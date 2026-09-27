//! Metadata adapter shared by Exasol and Trino.
//!
//! Provides the schema-creation preflight (`create_schemas_if_not_exists` ->
//! `<adapter>__create_schema`), per-relation schema fetch for unit tests and
//! contracts (`list_relations_schemas_inner`, via a zero-row probe — both drivers
//! return the result schema even for empty results; for Exasol this needs
//! exarrow-rs >= 0.12.7), and catalog parsing for `compile --write-catalog`
//! (`build_schemas_from_stats_sql` / `build_columns_from_get_columns` over the
//! RecordBatch produced by `<adapter>__get_catalog`). Exasol's relation-cache hydration is
//! intentionally empty, so dbt falls back to the per-relation
//! `list_relations_without_caching` / `get_relation` macros; Trino hydrates the cache from
//! `information_schema` ([`list_relations`]). Metadata-based source freshness is implemented
//! for Exasol as `exasol__get_relation_last_modified`; the `freshness_inner` entry point stays
//! unimplemented until the shared task graph handles the Source command. Trino exposes no
//! last-modified metadata (dbt-trino `TableLastModifiedMetadata: Unsupported`).

use crate::AdapterEngine;
use crate::adapter::adapter_impl::AdapterImpl;
use crate::connection::{AdapterConnectionFactory, ConnectionGuard};
use crate::errors::{AdapterError, AdapterErrorKind, AsyncAdapterResult, Cancellable};
use crate::relation::do_create_relation;
use crate::{AdapterResult, metadata::*, record_batch::RecordBatchExt};
use arrow_schema::Schema;
use dbt_adapter_engine::MapReduce;
use dbt_adbc::QueryCtx;
use dbt_common::cancellation::CancellationToken;
use dbt_schemas::dbt_types::RelationType;

use arrow_array::{Array, Decimal128Array, RecordBatch, StringArray};

use dbt_adapter_core::ExecutionPhase;
use dbt_schemas::schemas::{
    legacy_catalog::{CatalogNodeStats, CatalogTable, ColumnMetadata, TableMetadata},
    relations::base::{BaseRelation, RelationPattern},
};
use indexmap::IndexMap;
use minijinja::State;

use std::collections::btree_map::Entry;
use std::collections::{BTreeMap, HashMap};
use std::future;
use std::sync::Arc;

pub struct GenericMetadataAdapter {
    adapter: AdapterImpl,
}

impl GenericMetadataAdapter {
    pub fn new(engine: Arc<dyn AdapterEngine>) -> Self {
        let adapter = AdapterImpl::new(engine, None);
        Self { adapter }
    }
}

impl MetadataAdapter for GenericMetadataAdapter {
    fn adapter_type(&self) -> AdapterType {
        self.adapter.adapter_type()
    }

    fn build_schemas_from_stats_sql(
        &self,
        stats_sql_result: Arc<RecordBatch>,
    ) -> AdapterResult<BTreeMap<String, CatalogTable>> {
        if stats_sql_result.num_rows() == 0 {
            return Ok(BTreeMap::new());
        }

        let table_catalogs = stats_sql_result.column_values::<StringArray>("table_database")?;
        let table_schemas = stats_sql_result.column_values::<StringArray>("table_schema")?;
        let table_names = stats_sql_result.column_values::<StringArray>("table_name")?;
        let data_types = stats_sql_result.column_values::<StringArray>("table_type")?;
        let comments = stats_sql_result.column_values::<StringArray>("table_comment")?;
        let table_owners = stats_sql_result.column_values::<StringArray>("table_owner")?;

        let mut result = BTreeMap::<String, CatalogTable>::new();

        for i in 0..table_catalogs.len() {
            let catalog = table_catalogs.value(i);
            let schema = table_schemas.value(i);
            let table = table_names.value(i);
            let data_type = data_types.value(i);
            let comment = comments.value(i);
            let owner = table_owners.value(i);

            let fully_qualified_name = format!("{catalog}.{schema}.{table}").to_lowercase();

            let entry = result.entry(fully_qualified_name.clone());

            if matches!(entry, Entry::Vacant(_)) {
                let node_metadata = TableMetadata {
                    materialization_type: data_type.to_string(),
                    schema: schema.to_string(),
                    name: table.to_string(),
                    database: Some(catalog.to_string()),
                    comment: match comment {
                        "" => None,
                        _ => Some(comment.to_string()),
                    },
                    // Trino catalogs report no owner (NULL); Exasol always reports one.
                    owner: match (self.adapter_type(), table_owners.is_null(i)) {
                        (AdapterType::Trino, true) => None,
                        _ => Some(owner.to_string()),
                    },
                };

                let no_stats = CatalogNodeStats {
                    id: "has_stats".to_string(),
                    label: "Has Stats?".to_string(),
                    value: serde_json::Value::Bool(false),
                    description: Some(
                        "Indicates whether there are statistics for this table".to_string(),
                    ),
                    include: false,
                };

                let node = CatalogTable {
                    metadata: node_metadata,
                    columns: IndexMap::new(),
                    stats: BTreeMap::from([("has_stats".to_string(), no_stats)]),
                    unique_id: None,
                };
                result.insert(fully_qualified_name.clone(), node);
            }
        }
        Ok(result)
    }

    fn build_columns_from_get_columns(
        &self,
        stats_sql_result: Arc<RecordBatch>,
    ) -> AdapterResult<BTreeMap<String, BTreeMap<String, ColumnMetadata>>> {
        if stats_sql_result.num_rows() == 0 {
            return Ok(BTreeMap::new());
        }

        let table_catalogs = stats_sql_result.column_values::<StringArray>("table_database")?;
        let table_schemas = stats_sql_result.column_values::<StringArray>("table_schema")?;
        let table_names = stats_sql_result.column_values::<StringArray>("table_name")?;

        let column_names = stats_sql_result.column_values::<StringArray>("column_name")?;
        let column_indices = stats_sql_result.column_values::<Decimal128Array>("column_index")?;
        let column_types = stats_sql_result.column_values::<StringArray>("column_type")?;
        let column_comments = stats_sql_result.column_values::<StringArray>("column_comment")?;

        let mut columns_by_relation = BTreeMap::new();

        for i in 0..table_catalogs.len() {
            let catalog = table_catalogs.value(i);
            let schema = table_schemas.value(i);
            let table = table_names.value(i);

            let fully_qualified_name = format!("{catalog}.{schema}.{table}").to_lowercase();

            let column_name = column_names.value(i);
            let column_index = column_indices.value(i);
            let column_type = column_types.value(i);
            let column_comment = column_comments.value(i);

            let column = ColumnMetadata {
                name: column_name.to_string(),
                index: column_index,
                data_type: column_type.to_string(),
                comment: match column_comment {
                    "" => None,
                    _ => Some(column_comment.to_string()),
                },
            };

            columns_by_relation
                .entry(fully_qualified_name.clone())
                .or_insert(BTreeMap::new())
                .insert(column_name.to_string(), column);
        }
        Ok(columns_by_relation)
    }

    fn list_relations_schemas_inner(
        &self,
        unique_id: Option<String>,
        phase: Option<ExecutionPhase>,
        relations: &[Arc<dyn BaseRelation>],
        item_span_operation_id: Option<&str>,
        token: CancellationToken,
    ) -> AsyncAdapterResult<'_, HashMap<String, AdapterResult<Arc<Schema>>>> {
        type Acc = HashMap<String, AdapterResult<Arc<Schema>>>;

        // The Arrow schema comes straight from a zero-row probe (see the module docs). The probe
        // must render the name exactly as materializations do (quote policy included): under
        // Exasol's default policy objects are created quoted, so an unquoted probe would
        // uppercase-resolve to a different name. The HashMap key must match
        // `relation.semantic_fqn()`, so both forms are carried as a tuple.
        let keys: Vec<(String, String)> = relations
            .iter()
            .map(|relation| (relation.semantic_fqn(), relation.render_self_as_str()))
            .collect();

        let factory = Box::new(AdapterConnectionFactory::new(self.adapter.engine().clone()));

        let adapter = self.adapter.clone();
        let token_clone = token.clone();
        let map_f = move |conn: &mut ConnectionGuard<'_>,
                          key: &(String, String)|
              -> AdapterResult<Arc<Schema>> {
            let (_semantic_fqn, sql_name) = key;
            let sql = format!("select * from {sql_name} where false limit 0");
            let mut ctx = QueryCtx::default().with_desc("Get table schema");
            if let Some(node_id) = unique_id.clone() {
                ctx = ctx.with_node_id(&node_id);
            }
            if let Some(phase) = phase {
                ctx = ctx.with_phase(phase.as_str());
            }
            let (_, table) = adapter.query(&ctx, conn, &sql, None, token_clone.clone())?;
            Ok(table.original_record_batch().schema())
        };

        let reduce_f = |acc: &mut Acc,
                        key: (String, String),
                        schema: AdapterResult<Arc<Schema>>|
         -> Result<(), Cancellable<AdapterError>> {
            let (semantic_fqn, _sql_name) = key;
            acc.insert(semantic_fqn, schema);
            Ok(())
        };

        run_schema_cache_map_reduce(
            factory,
            keys,
            item_span_operation_id,
            map_f,
            reduce_f,
            None,
            token,
        )
    }

    fn list_relations_schemas_by_patterns_inner(
        &self,
        _patterns: &[RelationPattern],
        _token: CancellationToken,
    ) -> AsyncAdapterResult<'_, Vec<(String, AdapterResult<RelationSchemaPair>)>> {
        let err = AdapterError::new(
            AdapterErrorKind::NotSupported,
            format!(
                "list_relations_schemas_by_patterns is not yet implemented for the {:?} metadata adapter",
                self.adapter_type()
            ),
        );
        Box::pin(future::ready(Err(Cancellable::Error(err))))
    }

    fn freshness_inner(
        &self,
        _relations: &[Arc<dyn BaseRelation>],
        _token: CancellationToken,
    ) -> AsyncAdapterResult<'_, BTreeMap<String, MetadataFreshness>> {
        let err = AdapterError::new(
            AdapterErrorKind::NotSupported,
            format!(
                "metadata-based source freshness is not yet implemented for the {:?} adapter",
                self.adapter_type()
            ),
        );
        Box::pin(future::ready(Err(Cancellable::Error(err))))
    }

    fn create_schemas_if_not_exists(
        &self,
        state: &State<'_, '_>,
        catalog_schemas: Vec<(String, String, String)>,
    ) -> AdapterResult<Vec<(String, String, String, AdapterResult<()>)>> {
        create_schemas_if_not_exists(&self.adapter, self, state, catalog_schemas)
    }

    fn supports_relation_progress(&self) -> bool {
        matches!(self.adapter_type(), AdapterType::Trino)
    }

    fn list_relations_in_parallel_inner(
        &self,
        db_schemas: &[CatalogAndSchema],
        token: CancellationToken,
        report_progress: bool,
    ) -> AsyncAdapterResult<'_, BTreeMap<CatalogAndSchema, AdapterResult<RelationVec>>> {
        type Acc = BTreeMap<CatalogAndSchema, AdapterResult<RelationVec>>;
        match self.adapter_type() {
            AdapterType::Trino => {
                let factory =
                    Box::new(AdapterConnectionFactory::new(self.adapter.engine().clone()));
                let engine = self.adapter.engine().clone();
                let token_clone = token.clone();
                let map_f = move |conn: &mut ConnectionGuard<'_>,
                                  db_schema: &CatalogAndSchema|
                      -> AdapterResult<RelationVec> {
                    let ctx = QueryCtx::default().with_desc("list_relations_in_parallel");
                    with_relation_list_item_span(
                        report_progress.then_some(RELATION_CACHE_OP_ID),
                        &db_schema.to_string(),
                        || {
                            list_relations(
                                engine.as_ref(),
                                &ctx,
                                conn,
                                db_schema,
                                token_clone.clone(),
                            )
                        },
                    )
                };
                // A schema that fails to list stays uncached; `get_relation` lists it on demand.
                let reduce_f = |acc: &mut Acc,
                                db_schema: CatalogAndSchema,
                                relations: AdapterResult<RelationVec>|
                 -> Result<(), Cancellable<AdapterError>> {
                    acc.insert(db_schema, relations);
                    Ok(())
                };
                MapReduce::new(factory, Box::new(map_f), Box::new(reduce_f), None)
                    .run(Arc::new(db_schemas.to_vec()), token)
            }
            // Exasol's cache hydration is intentionally empty: dbt falls back to the
            // per-relation `list_relations_without_caching` / `get_relation` macros.
            _ => Box::pin(future::ready(Ok(BTreeMap::new()))),
        }
    }
}

/// Convert information_schema table rows using the engine's relation and quoting policy.
pub(crate) fn relations_from_information_schema(
    engine: &dyn AdapterEngine,
    batch: &RecordBatch,
) -> AdapterResult<Vec<Arc<dyn BaseRelation>>> {
    if batch.num_rows() == 0 {
        return Ok(Vec::new());
    }

    let table_catalogs = batch.column_values::<StringArray>("table_catalog")?;
    let table_schemas = batch.column_values::<StringArray>("table_schema")?;
    let table_names = batch.column_values::<StringArray>("table_name")?;
    let table_types = batch.column_values::<StringArray>("table_type")?;

    let mut relations = Vec::with_capacity(batch.num_rows());
    for i in 0..batch.num_rows() {
        let database = table_catalogs.value(i);
        let schema = table_schemas.value(i);
        let name = table_names.value(i);
        // DuckDB reports BASE TABLE, VIEW and LOCAL TEMPORARY (a temporary table). Trino reports
        // BASE TABLE and VIEW, and `information_schema_tables_sql` adds MATERIALIZED VIEW.
        let relation_type = match table_types.value(i) {
            "BASE TABLE" => RelationType::Table,
            "VIEW" => RelationType::View,
            "MATERIALIZED VIEW" => RelationType::MaterializedView,
            "LOCAL TEMPORARY" => RelationType::Table,
            other => RelationType::from_adapter_type(engine.adapter_type(), other),
        };

        let relation = do_create_relation(
            engine.adapter_type(),
            database.to_string(),
            schema.to_string(),
            Some(name.to_string()),
            Some(relation_type),
            engine.quoting(),
        )
        .map_err(|e| AdapterError::new(AdapterErrorKind::Internal, e.to_string()))?;

        relations.push(Arc::from(relation));
    }

    Ok(relations)
}

/// `information_schema.tables` rows (`table_catalog`, `table_schema`, `table_name`,
/// `table_type`) for one schema, optionally one table. Used by Trino; DuckDB keeps its own query.
///
/// Trino reports materialized views as `BASE TABLE`; they are identified through
/// `system.metadata.materialized_views`, as dbt-trino v1 does in `list_relations_without_caching`.
/// Trino stores catalog, schema and table names in lowercase even when they are quoted, so the
/// name literals are lowercased whatever the quote policy, like v1's `| lower` filters:
/// https://github.com/starburstdata/dbt-trino/blob/v1.10.5/dbt/include/trino/macros/adapters.sql#L34-L54
/// An empty catalog reads the session catalog, as v1's unqualified `information_schema` does:
/// https://github.com/starburstdata/dbt-trino/blob/v1.10.5/dbt/include/trino/macros/adapters.sql#L236-L242
pub(crate) fn information_schema_tables_sql(
    adapter_type: AdapterType,
    catalog: &str,
    schema: &str,
    table: Option<&str>,
) -> String {
    use dbt_adapter_sql::ident::{escape_string_literal, quote_identifier};
    match adapter_type {
        AdapterType::Trino => {
            let literal = |name: &str| escape_string_literal(&name.to_lowercase(), adapter_type);
            let (catalog_prefix, catalog_name) = match catalog {
                "" => (String::new(), "current_catalog".to_string()),
                _ => (
                    format!("{}.", quote_identifier(catalog, adapter_type)),
                    format!("'{}'", literal(catalog)),
                ),
            };
            let schema = literal(schema);
            let table_filter = table
                .map(|table| format!(" AND t.table_name = '{}'", literal(table)))
                .unwrap_or_default();
            format!(
                "SELECT t.table_catalog, t.table_schema, t.table_name, \
                 CASE WHEN mv.name IS NOT NULL THEN 'MATERIALIZED VIEW' ELSE t.table_type END \
                 AS table_type \
                 FROM {catalog_prefix}information_schema.tables t \
                 LEFT JOIN (SELECT name FROM system.metadata.materialized_views \
                 WHERE catalog_name = {catalog_name} AND schema_name = '{schema}') mv \
                 ON mv.name = t.table_name \
                 WHERE t.table_schema = '{schema}'{table_filter}"
            )
        }
        other => unimplemented!("information_schema_tables_sql is not implemented for {other}"),
    }
}

pub(crate) fn list_relations(
    engine: &dyn AdapterEngine,
    ctx: &QueryCtx,
    conn: &mut ConnectionGuard<'_>,
    db_schema: &CatalogAndSchema,
    token: CancellationToken,
) -> AdapterResult<Vec<Arc<dyn BaseRelation>>> {
    let sql = information_schema_tables_sql(
        engine.adapter_type(),
        &db_schema.resolved_catalog,
        &db_schema.resolved_schema,
        None,
    );
    let batch = engine.execute(None, conn.as_mut(), ctx, &sql, token)?;
    relations_from_information_schema(engine, &batch)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::adapter::adapter_factory::backend_of;
    use crate::cache::RelationCache;
    use crate::config::AdapterConfig;
    use crate::engine::query_comment::QueryCommentConfig;
    use crate::engine::{ColumnInfo, NoopConnection, SidecarClient, SidecarEngine};
    use crate::sql_types::DefaultTypeOps;
    use crate::stmt_splitter::DefaultStmtSplitter;
    use arrow_array::ArrayRef;
    use arrow_schema::{DataType, Field};
    use dbt_adbc::Connection;
    use dbt_schemas::schemas::common::ResolvedQuoting;
    use dbt_schemas::schemas::relations::DEFAULT_RESOLVED_QUOTING;

    fn mock_engine(adapter_type: AdapterType) -> Arc<dyn AdapterEngine> {
        AdapterImpl::new_mock(
            adapter_type,
            BTreeMap::new(),
            DEFAULT_RESOLVED_QUOTING,
            Arc::new(DefaultTypeOps::new(adapter_type)),
            Arc::new(DefaultStmtSplitter),
        )
        .engine()
        .clone()
    }

    fn iceberg_schema(name: &str) -> CatalogAndSchema {
        CatalogAndSchema {
            rendered_catalog: "\"iceberg\"".to_string(),
            rendered_schema: format!("\"{name}\""),
            resolved_catalog: "iceberg".to_string(),
            resolved_schema: name.to_string(),
        }
    }

    /// `information_schema_tables_sql` rows for `(table_name, table_type)` in iceberg.analytics.
    fn analytics_tables(tables: &[(&str, &str)]) -> RecordBatch {
        let column = |values: Vec<&str>| Arc::new(StringArray::from(values)) as ArrayRef;
        let fields = ["table_catalog", "table_schema", "table_name", "table_type"]
            .map(|name| Field::new(name, DataType::Utf8, false));
        RecordBatch::try_new(
            Arc::new(Schema::new(fields.to_vec())),
            vec![
                column(vec!["iceberg"; tables.len()]),
                column(vec!["analytics"; tables.len()]),
                column(tables.iter().map(|(name, _)| *name).collect()),
                column(tables.iter().map(|(_, table_type)| *table_type).collect()),
            ],
        )
        .unwrap()
    }

    #[test]
    fn trino_tables_sql_identifies_materialized_views_and_escapes() {
        let sql = information_schema_tables_sql(AdapterType::Trino, "ice\"berg", "it's", Some("t"));
        assert!(
            sql.contains("FROM \"ice\"\"berg\".information_schema.tables t"),
            "{sql}"
        );
        assert!(sql.contains("system.metadata.materialized_views"), "{sql}");
        assert!(sql.contains("catalog_name = 'ice\"berg'"), "{sql}");
        assert!(sql.contains("schema_name = 'it''s'"), "{sql}");
        assert!(sql.ends_with("AND t.table_name = 't'"), "{sql}");
    }

    #[test]
    fn trino_tables_sql_lowercases_mixed_case_names() {
        let sql = information_schema_tables_sql(
            AdapterType::Trino,
            "Iceberg",
            "Staging",
            Some("MyTable"),
        );
        assert!(
            sql.contains("FROM \"Iceberg\".information_schema.tables t"),
            "{sql}"
        );
        assert!(
            sql.contains("WHERE catalog_name = 'iceberg' AND schema_name = 'staging'"),
            "{sql}"
        );
        assert!(
            sql.ends_with("WHERE t.table_schema = 'staging' AND t.table_name = 'mytable'"),
            "{sql}"
        );
    }

    #[test]
    fn trino_tables_sql_reads_the_session_catalog_without_a_catalog() {
        let sql = information_schema_tables_sql(AdapterType::Trino, "", "Staging", Some("m1"));
        assert!(sql.contains("FROM information_schema.tables t"), "{sql}");
        assert!(
            sql.contains("WHERE catalog_name = current_catalog AND schema_name = 'staging'"),
            "{sql}"
        );
    }

    #[test]
    fn trino_listing_rows_become_typed_relations() {
        let batch = analytics_tables(&[
            ("t", "BASE TABLE"),
            ("v", "VIEW"),
            ("mv", "MATERIALIZED VIEW"),
        ]);

        let relations =
            relations_from_information_schema(mock_engine(AdapterType::Trino).as_ref(), &batch)
                .unwrap();
        let relation_types = relations
            .iter()
            .map(|relation| relation.relation_type())
            .collect::<Vec<_>>();
        assert_eq!(
            relation_types,
            [
                Some(RelationType::Table),
                Some(RelationType::View),
                Some(RelationType::MaterializedView),
            ]
        );
    }

    #[test]
    fn trino_catalog_tables_without_an_owner_have_no_owner() {
        let column =
            |values: [Option<&str>; 2]| Arc::new(StringArray::from(values.to_vec())) as ArrayRef;
        let fields = [
            "table_database",
            "table_schema",
            "table_name",
            "table_type",
            "table_comment",
            "table_owner",
        ]
        .map(|name| Field::new(name, DataType::Utf8, true));
        let batch = Arc::new(
            RecordBatch::try_new(
                Arc::new(Schema::new(fields.to_vec())),
                vec![
                    column([Some("iceberg"); 2]),
                    column([Some("analytics"); 2]),
                    column([Some("t"), Some("u")]),
                    column([Some("BASE TABLE"); 2]),
                    column([None; 2]),
                    column([None, Some("admin")]),
                ],
            )
            .unwrap(),
        );
        let owners = |adapter_type| {
            GenericMetadataAdapter::new(mock_engine(adapter_type))
                .build_schemas_from_stats_sql(batch.clone())
                .unwrap()
                .into_values()
                .map(|table| table.metadata.owner)
                .collect::<Vec<_>>()
        };

        assert_eq!(
            owners(AdapterType::Trino),
            [None, Some("admin".to_string())]
        );
        // Exasol always reports an owner, and its rows keep one.
        assert!(owners(AdapterType::Exasol).iter().all(Option::is_some));
    }

    #[dbt_runtime::test]
    async fn trino_hydrates_every_schema_and_exasol_none() {
        let db_schemas = [iceberg_schema("analytics"), iceberg_schema("staging")];

        let trino = GenericMetadataAdapter::new(mock_engine(AdapterType::Trino));
        assert!(trino.supports_relation_progress());
        let hydrated = trino
            .list_relations_in_parallel_inner(
                &db_schemas,
                CancellationToken::never_cancels(),
                false,
            )
            .await
            .unwrap();
        assert_eq!(hydrated.keys().cloned().collect::<Vec<_>>(), db_schemas);
        assert!(
            hydrated
                .values()
                .all(|relations| relations.as_ref().is_ok_and(Vec::is_empty))
        );

        let exasol = GenericMetadataAdapter::new(mock_engine(AdapterType::Exasol));
        assert!(!exasol.supports_relation_progress());
        let hydrated = exasol
            .list_relations_in_parallel_inner(
                &db_schemas,
                CancellationToken::never_cancels(),
                false,
            )
            .await
            .unwrap();
        assert!(hydrated.is_empty());
    }

    /// Lists one table in `analytics` and fails every other query, as Trino does for a schema
    /// that the user cannot read. The sidecar engine sends each query to this client.
    #[derive(Debug)]
    struct AnalyticsOnlyClient;

    impl SidecarClient for AnalyticsOnlyClient {
        fn execute(
            &self,
            _ctx: &QueryCtx,
            sql: &str,
            _fetch: bool,
        ) -> AdapterResult<Option<RecordBatch>> {
            if sql.contains("WHERE t.table_schema = 'analytics'") {
                Ok(Some(analytics_tables(&[("t", "BASE TABLE")])))
            } else {
                Err(AdapterError::new(
                    AdapterErrorKind::SqlExecution,
                    "Access Denied: Cannot select from columns",
                ))
            }
        }

        fn new_connection(
            &self,
            _state: Option<&State>,
            _node_id: Option<String>,
        ) -> AdapterResult<Box<dyn Connection>> {
            Ok(Box::new(NoopConnection))
        }

        fn shutdown(&self) -> AdapterResult<()> {
            Ok(())
        }

        fn get_relation_type(
            &self,
            _quoting: &ResolvedQuoting,
            _database: &str,
            _schema: &str,
            _table: &str,
        ) -> AdapterResult<Option<RelationType>> {
            unimplemented!()
        }

        fn get_columns(&self, _relation_name: &str) -> AdapterResult<Vec<ColumnInfo>> {
            unimplemented!()
        }

        fn list_relations(
            &self,
            _quoting: &ResolvedQuoting,
            _database: &str,
            _schema: &str,
        ) -> AdapterResult<Vec<(String, String, String, RelationType)>> {
            unimplemented!()
        }
    }

    #[dbt_runtime::test]
    async fn trino_hydration_keeps_the_error_of_a_schema_that_fails_to_list() {
        let engine = SidecarEngine::new(
            AdapterType::Trino,
            backend_of(AdapterType::Trino),
            Arc::new(AnalyticsOnlyClient),
            DEFAULT_RESOLVED_QUOTING,
            AdapterConfig::default(),
            Arc::new(DefaultTypeOps::new(AdapterType::Trino)),
            Arc::new(DefaultStmtSplitter),
            QueryCommentConfig::from_query_comment(None, AdapterType::Trino, false, None),
            Arc::new(RelationCache::default()),
        );
        let hydrated = GenericMetadataAdapter::new(Arc::new(engine))
            .list_relations_in_parallel_inner(
                &[iceberg_schema("analytics"), iceberg_schema("staging")],
                CancellationToken::never_cancels(),
                false,
            )
            .await
            .unwrap();

        assert_eq!(hydrated.len(), 2);
        assert!(
            hydrated[&iceberg_schema("analytics")]
                .as_ref()
                .is_ok_and(|relations| relations.len() == 1)
        );
        assert!(hydrated[&iceberg_schema("staging")].is_err());
    }
}
