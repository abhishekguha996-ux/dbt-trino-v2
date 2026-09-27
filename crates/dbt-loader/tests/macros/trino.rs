//! Tests for the dbt-trino macro package (vendored from dbt-trino v1.10.5 with v2 changes).

use std::collections::BTreeMap;
use std::sync::Arc;

use dbt_adapter::Adapter;
use dbt_adapter::relation::RelationObject;
use dbt_adapter::sql_types::DefaultTypeOps;
use dbt_adapter_core::AdapterType;
use dbt_jinja_ctx::DbtNamespace;
use dbt_jinja_utils::mock_object::MockJinjaObject;
use dbt_schemas::dbt_types::RelationType;
use dbt_schemas::schemas::relations::default_dbt_quoting_for;
use minijinja::{State, Value};

use crate::macro_test_harness::{MacroTestHarness, executed_sql};

fn harness() -> MacroTestHarness {
    let mut harness = MacroTestHarness::for_adapter(AdapterType::Trino)
        .load_all_macros()
        .with_stub_functions()
        .with_global("dbt", Value::from_object(DbtNamespace::new("dbt")))
        .build()
        .expect("Trino macros should load");
    harness.mock().on("quote", |args| {
        let name = args.first().and_then(Value::as_str).unwrap_or_default();
        Ok(Value::from(format!("\"{}\"", name.replace('"', "\"\""))))
    });
    harness
        .env_mut()
        .env
        .add_global("execute", Value::from(true));
    harness
}

/// A `config` object returning the given values and each caller's default otherwise.
fn config(values: BTreeMap<&'static str, Value>) -> Value {
    let mock = Arc::new(MockJinjaObject::new());
    mock.on("get", move |args| {
        let key = args.first().and_then(Value::as_str).unwrap_or_default();
        Ok(match (key, values.get(key)) {
            (_, Some(value)) => value.clone(),
            ("contract", None) => Value::from_serialize(BTreeMap::from([("enforced", false)])),
            _ => args.get(1).cloned().unwrap_or(Value::UNDEFINED),
        })
    });
    mock.on("persist_column_docs", |_| Ok(Value::from(false)));
    mock.on("persist_relation_docs", |_| Ok(Value::from(false)));
    Value::from_dyn_object(mock)
}

fn squash(sql: &str) -> String {
    sql.split_whitespace().collect::<Vec<_>>().join(" ")
}

fn relation(h: &MacroTestHarness, name: &str, kind: RelationType) -> Value {
    RelationObject::new(h.relation("memory", "analytics", name, Some(kind))).into_value()
}

fn context(entries: impl IntoIterator<Item = (&'static str, Value)>) -> BTreeMap<String, Value> {
    entries
        .into_iter()
        .map(|(key, value)| (key.to_string(), value))
        .collect()
}

/// Columns as `adapter.get_columns_in_relation` returns them: `name` and `data_type`.
fn columns(columns: &[(&str, &str)]) -> Value {
    Value::from_serialize(
        columns
            .iter()
            .map(|(name, data_type)| BTreeMap::from([("name", *name), ("data_type", *data_type)]))
            .collect::<Vec<_>>(),
    )
}

#[test]
fn trino_ctas_keeps_catalog_and_schema_for_intermediate_tables() {
    let h = harness();
    let ctx = h
        .materialization_context("orders__dbt_tmp", "select 1 as id")
        .database("memory")
        .schema("analytics")
        .relation_type(RelationType::Table)
        .build();
    let sql = h
        .render(
            "{{ trino__create_table_as(true, this, compiled_code) }}",
            ctx,
        )
        .unwrap();
    assert!(
        sql.contains("\"memory\".\"analytics\".\"orders__dbt_tmp\""),
        "{sql}"
    );
    assert!(!sql.contains("temporary"), "{sql}");
    assert!(sql.contains("select 1 as id"), "{sql}");
}

#[test]
fn trino_ctas_on_table_exists_modes_and_properties() {
    let h = harness();
    let properties = Value::from_serialize(BTreeMap::from([("partitioned_by", "ARRAY['d']")]));
    let ctx = h
        .materialization_context("orders", "select 1 as id")
        .database("hive")
        .schema("analytics")
        .relation_type(RelationType::Table)
        .config(config(BTreeMap::from([
            ("properties", properties),
            ("file_format", Value::from("PARQUET")),
        ])))
        .build();
    for (mode, expected) in [
        ("none", "create table \"hive\""),
        ("'replace'", "create or replace table \"hive\""),
        ("'skip'", "create table if not exists \"hive\""),
    ] {
        let sql = squash(
            &h.render(
                &format!("{{{{ trino__create_table_as(false, this, compiled_code, {mode}) }}}}"),
                ctx.clone(),
            )
            .unwrap(),
        );
        assert!(sql.contains(expected), "{mode}: {sql}");
        assert!(
            sql.contains("WITH (partitioned_by = ARRAY['d'], format = 'PARQUET')"),
            "{sql}"
        );
    }
}

#[test]
fn trino_properties_reject_conflicting_format_configs() {
    let h = harness();
    let ctx = h
        .materialization_context("orders", "select 1 as id")
        .relation_type(RelationType::Table)
        .config(config(BTreeMap::from([
            (
                "properties",
                Value::from_serialize(BTreeMap::from([("format", "'ORC'")])),
            ),
            ("file_format", Value::from("PARQUET")),
        ])))
        .build();
    let err = h
        .render("{{ properties() }}", ctx)
        .expect_err("file_format and properties.format conflict");
    assert!(err.to_string().contains("file_format"), "{err}");
}

#[test]
fn trino_properties_fill_type_and_storage_uri_location() {
    let h = harness();
    let render = |values: BTreeMap<&'static str, Value>, template: &str| {
        let ctx = h
            .materialization_context("orders", "select 1 as id")
            .config(config(values))
            .build();
        squash(&h.render(template, ctx).unwrap())
    };
    let values = BTreeMap::from([
        ("table_format", Value::from("ICEBERG")),
        ("storage_uri", Value::from("s3://lake/orders")),
    ]);
    assert_eq!(
        render(values.clone(), "{{ properties() }}"),
        "WITH (type = 'ICEBERG', location = 's3://lake/orders')"
    );
    assert_eq!(
        render(values, "{{ properties(temporary=True) }}"),
        "WITH (type = 'ICEBERG', location = 's3://lake/orders__dbt_tmp')"
    );
    let properties = Value::from_serialize(BTreeMap::from([("location", "'s3://lake/own'")]));
    assert_eq!(
        render(
            BTreeMap::from([
                ("properties", properties),
                ("storage_uri", Value::from("s3://lake/orders")),
            ]),
            "{{ properties() }}"
        ),
        "WITH (location = 's3://lake/own')"
    );
}

#[test]
fn trino_properties_reject_catalog_integrations() {
    let h = harness();
    let ctx = h
        .materialization_context("orders", "select 1 as id")
        .config(config(BTreeMap::from([(
            "catalog_name",
            Value::from("lake"),
        )])))
        .build();
    let err = h
        .render("{{ properties() }}", ctx)
        .expect_err("catalog_name is not supported");
    assert!(
        err.to_string().contains(
            "catalogs.yml catalog integrations (catalog_name) are not supported by the Trino \
             adapter yet. Remove catalog_name and use properties, file_format or table_format."
        ),
        "{err}"
    );
}

#[test]
fn trino_sql_header_runs_before_create_statements() {
    let h = harness();
    let ctx = h
        .materialization_context("orders", "select 1 as id")
        .config(config(BTreeMap::from([(
            "sql_header",
            Value::from("set session query_max_run_time = '1h';"),
        )])))
        .build();
    for template in [
        "{{ trino__create_table_as(false, this, compiled_code) }}",
        "{{ trino__create_view_as(this, compiled_code) }}",
    ] {
        let sql = squash(&h.render(template, ctx.clone()).unwrap());
        assert!(
            sql.starts_with("set session query_max_run_time = '1h'; create"),
            "{template}: {sql}"
        );
    }
}

#[test]
fn trino_view_security_defaults_to_definer_and_rejects_unknown_values() {
    let h = harness();
    for (security, expected) in [
        (None, "security definer"),
        (Some("invoker"), "security invoker"),
        (Some("owner"), "security definer"),
    ] {
        let values = security
            .map(|s| BTreeMap::from([("view_security", Value::from(s))]))
            .unwrap_or_default();
        let ctx = h
            .materialization_context("v", "select 1 as id")
            .config(config(values))
            .build();
        let sql = squash(
            &h.render("{{ trino__create_view_as(this, compiled_code) }}", ctx)
                .unwrap(),
        );
        assert!(sql.contains("create or replace view"), "{sql}");
        assert!(sql.contains(expected), "{sql}");
    }
}

#[test]
fn trino_quoted_literal_escapes_and_string_literal_keeps_the_default() {
    let h = harness();
    let ctx = context([("value", Value::from("schema'; drop table x; --"))]);
    let sql = h
        .render("{{ trino_quoted_literal(value) }}", ctx.clone())
        .unwrap();
    assert_eq!(sql.trim(), "'schema''; drop table x; --'");
    // Not a dispatch override: dbt.string_literal keeps dbt's default, as in dbt-trino v1.
    let sql = h.render("{{ dbt.string_literal(value) }}", ctx).unwrap();
    assert_eq!(sql.trim(), "'schema'; drop table x; --'");
}

#[test]
fn trino_column_listing_matches_lowercase_names_in_position_order() {
    let h = harness();
    let table =
        RelationObject::new(h.relation("Iceberg", "Sales'26", "Orders", Some(RelationType::Table)))
            .into_value();
    h.render(
        "{{ trino__get_columns_in_relation(relation) }}",
        context([("relation", table)]),
    )
    .unwrap();
    let sql = squash(&executed_sql(h.mock()).join("\n"));
    assert!(
        sql.contains(
            "where table_catalog = 'iceberg' and table_schema = 'sales''26' \
             and table_name = 'orders' order by ordinal_position"
        ),
        "{sql}"
    );
    assert!(sql.contains(".INFORMATION_SCHEMA.columns"), "{sql}");
}

#[test]
fn trino_rename_and_drop_use_relation_kind_and_qualified_targets() {
    for (kind, noun) in [
        (RelationType::Table, "table"),
        (RelationType::View, "view"),
        (RelationType::MaterializedView, "materialized view"),
    ] {
        let h = harness();
        let ctx = BTreeMap::from([("relation".to_string(), relation(&h, "orders", kind))]);
        let sql = squash(
            &h.render(
                "{{ get_rename_sql(relation, 'orders__dbt_backup') }} | \
                 {{ trino__get_drop_sql(relation) }}",
                ctx,
            )
            .unwrap(),
        );
        assert!(
            sql.contains(&format!(
                "alter {noun} \"memory\".\"analytics\".\"orders\" rename to \
                 \"memory\".\"analytics\".\"orders__dbt_backup\""
            )),
            "{sql}"
        );
        assert!(
            sql.contains(&format!(
                "drop {noun} if exists \"memory\".\"analytics\".\"orders\""
            )),
            "{sql}"
        );
    }
}

#[test]
fn trino_rename_relation_executes_alter_for_relation_kind() {
    let h = harness();
    h.render(
        "{{ trino__rename_relation(relation, renamed) }}",
        BTreeMap::from([
            (
                "relation".to_string(),
                relation(&h, "orders", RelationType::View),
            ),
            (
                "renamed".to_string(),
                relation(&h, "renamed", RelationType::View),
            ),
        ]),
    )
    .unwrap();
    let sql = executed_sql(h.mock()).join("\n");
    assert!(
        sql.contains("alter view \"memory\".\"analytics\".\"orders\" rename to"),
        "{sql}"
    );
}

#[test]
fn trino_drop_schema_drops_each_listed_relation_by_its_type() {
    let mut h = harness();
    h.env_mut().env.add_function("load_result", |name: Value| {
        let rows = match name.as_str() {
            Some("list_relations_without_caching") => vec![vec![
                "memory",
                "orders_mv",
                "analytics",
                "materialized_view",
            ]],
            _ => vec![],
        };
        Ok(Value::from_serialize(BTreeMap::from([("table", rows)])))
    });
    h.render(
        "{{ trino__drop_schema(relation) }}",
        context([("relation", relation(&h, "orders", RelationType::Table))]),
    )
    .unwrap();
    let sql = squash(&executed_sql(h.mock()).join("\n"));
    assert!(
        sql.contains("drop materialized view if exists \"memory\".\"analytics\".\"orders_mv\""),
        "{sql}"
    );
    assert!(sql.contains("drop schema if exists"), "{sql}");
}

#[test]
fn trino_catalog_derives_information_schema_and_escapes_literals() {
    let h = harness();
    let table = RelationObject::new(h.relation(
        "Iceberg",
        "sales'2026",
        "orders",
        Some(RelationType::Table),
    ))
    .into_value();
    h.render(
        "{{ trino__get_catalog_relations(information_schema, relations) }}",
        BTreeMap::from([
            ("information_schema".to_string(), table.clone()),
            ("relations".to_string(), Value::from(vec![table])),
        ]),
    )
    .unwrap();
    let sql = executed_sql(h.mock()).join("\n");
    assert!(sql.contains("Iceberg.INFORMATION_SCHEMA.tables"), "{sql}");
    assert!(sql.contains("Iceberg.INFORMATION_SCHEMA.columns"), "{sql}");
    assert!(sql.contains("catalog_name = 'iceberg'"), "{sql}");
    assert!(sql.contains("'sales''2026'"), "{sql}");
    assert!(sql.contains("decimal(38, 0)"), "{sql}");
    assert!(sql.contains("left join table_comment"), "{sql}");
    assert!(
        sql.contains("cast(null as varchar) as \"table_owner\""),
        "{sql}"
    );
}

#[test]
fn trino_get_catalog_reads_the_views_of_the_documented_catalog() {
    let h = harness();
    let information_schema =
        RelationObject::new(h.relation("Iceberg", "sales", "orders", Some(RelationType::Table)))
            .into_value();
    h.render(
        "{{ trino__get_catalog(information_schema, ['Sales', 'ops']) }}",
        context([("information_schema", information_schema)]),
    )
    .unwrap();
    let sql = squash(&executed_sql(h.mock()).join("\n"));
    assert!(
        sql.contains("from Iceberg.INFORMATION_SCHEMA.tables"),
        "{sql}"
    );
    assert!(
        sql.contains("from Iceberg.INFORMATION_SCHEMA.columns"),
        "{sql}"
    );
    assert!(sql.contains("table_schema in ('sales', 'ops')"), "{sql}");
    assert!(
        sql.contains("where catalog_name = 'iceberg' and schema_name != 'information_schema'"),
        "{sql}"
    );
}

#[test]
fn trino_check_schema_exists_matches_the_lowercase_catalog_and_schema() {
    let h = harness();
    let information_schema =
        RelationObject::new(h.relation("Iceberg", "sales", "orders", Some(RelationType::Table)))
            .into_value();
    h.render(
        "{{ trino__check_schema_exists(information_schema, 'Staging') }}",
        context([("information_schema", information_schema)]),
    )
    .unwrap();
    let sql = squash(&executed_sql(h.mock()).join("\n"));
    assert!(
        sql.ends_with("where catalog_name = 'iceberg' and schema_name = 'staging'"),
        "{sql}"
    );
}

#[test]
fn trino_show_grants_matches_lowercase_names_and_reads_other_users_only() {
    let h = harness();
    let table =
        RelationObject::new(h.relation("Hive", "Staging", "MyTable", Some(RelationType::Table)))
            .into_value();
    let sql = squash(
        &h.render(
            "{{ trino__get_show_grant_sql(relation) }}",
            context([("relation", table)]),
        )
        .unwrap(),
    );
    assert!(
        sql.contains(".INFORMATION_SCHEMA.table_privileges"),
        "{sql}"
    );
    assert!(
        sql.ends_with(
            "where table_catalog = 'hive' and table_schema = 'staging' \
             and table_name = 'mytable' and grantee_type = 'USER' and grantee != current_user"
        ),
        "{sql}"
    );
}

#[test]
fn trino_merge_prefixes_insert_values_with_source_alias() {
    let mut h = harness();
    h.env_mut().env.add_global(
        "config",
        Value::from_dyn_object(crate::macro_test_harness::default_mock_config()),
    );
    let columns = Value::from_serialize(vec![
        BTreeMap::from([("name", "id"), ("quoted", "\"id\"")]),
        BTreeMap::from([("name", "amount"), ("quoted", "\"amount\"")]),
    ]);
    let sql = squash(
        &h.render(
            "{{ trino__get_merge_sql('target', 'source', ['id'], columns) }}",
            BTreeMap::from([("columns".to_string(), columns)]),
        )
        .unwrap(),
    );
    assert!(
        sql.contains("merge into target as DBT_INTERNAL_DEST using source as DBT_INTERNAL_SOURCE"),
        "{sql}"
    );
    assert!(
        sql.contains("values (DBT_INTERNAL_SOURCE.\"id\", DBT_INTERNAL_SOURCE.\"amount\")"),
        "{sql}"
    );
}

#[test]
fn trino_delete_insert_sql() {
    let h = harness();
    let columns = Value::from_serialize(vec![BTreeMap::from([("name", "id")])]);
    let sql = squash(
        &h.render(
            "{{ trino__get_delete_insert_merge_sql('target', 'source', 'id', columns) }}",
            BTreeMap::from([("columns".to_string(), columns)]),
        )
        .unwrap(),
    );
    assert!(sql.contains("delete from target"), "{sql}");
    assert!(sql.contains("select id from source"), "{sql}");
    assert!(sql.contains("insert into target (\"id\")"), "{sql}");
}

#[test]
fn trino_seed_bindings_use_typed_literals_and_keep_values_out_of_sql() {
    let h = harness();
    h.mock().on("quote_seed_column", |args| Ok(args[0].clone()));
    h.mock().on("convert_type", |_| Ok(Value::from("varchar")));
    h.mock().on("add_query", |_| Ok(Value::UNDEFINED));
    let mut ctx = h
        .materialization_context("seed_values", "")
        .database("memory")
        .schema("analytics")
        .relation_type(RelationType::Table)
        .build();
    ctx.insert(
        "model".to_string(),
        Value::from_serialize(BTreeMap::from([(
            "config",
            BTreeMap::from([(
                "column_types",
                BTreeMap::from([("day", "date"), ("payload", "json")]),
            )]),
        )])),
    );
    ctx.insert(
        "agate_table".to_string(),
        Value::from_serialize(BTreeMap::from([
            (
                "column_names",
                Value::from(vec!["day", "payload", "note", "missing"]),
            ),
            (
                "rows",
                Value::from(vec![Value::from(vec![
                    Value::from("2026-01-01"),
                    Value::from("{\"a\": \"%s\"}"),
                    Value::from("O'Brien"),
                    Value::from(()),
                ])]),
            ),
        ])),
    );
    let sql = squash(
        &h.render("{{ trino__load_csv_rows(model, agate_table) }}", ctx)
            .unwrap(),
    );
    assert!(sql.contains("(DATE %s,JSON %s,%s,NULL)"), "{sql}");
    assert!(
        !sql.contains("O'Brien") && !sql.contains("\"a\""),
        "values must stay in bindings: {sql}"
    );
    assert_eq!(h.mock().observed_calls().to("add_query").count(), 1);
}

#[test]
fn trino_seed_batches_shrink_for_wide_seeds() {
    let h = harness();
    h.mock().on("quote_seed_column", |args| Ok(args[0].clone()));
    h.mock().on("convert_type", |_| Ok(Value::from("varchar")));
    h.mock().on("add_query", |_| Ok(Value::UNDEFINED));
    let column_names = (0..200).map(|i| format!("c{i}")).collect::<Vec<_>>();
    // Only the column count sets the batch size; empty rows keep the render fast.
    let rows = vec![Vec::<String>::new(); 101];
    let mut ctx = h
        .materialization_context("wide_seed", "")
        .relation_type(RelationType::Table)
        .build();
    ctx.insert(
        "model".to_string(),
        Value::from_serialize(BTreeMap::from([(
            "config",
            BTreeMap::<String, String>::new(),
        )])),
    );
    ctx.insert(
        "agate_table".to_string(),
        Value::from_serialize(BTreeMap::from([
            ("column_names", Value::from_serialize(&column_names)),
            ("rows", Value::from_serialize(&rows)),
        ])),
    );
    h.render("{{ trino__load_csv_rows(model, agate_table) }}", ctx)
        .unwrap();
    // At most 20,000 values per statement: 100 rows of 200 columns, so 101 rows take two.
    assert_eq!(h.mock().observed_calls().to("add_query").count(), 2);
}

#[test]
fn trino_binding_char_is_a_placeholder_for_inlined_bindings() {
    let h = harness();
    let rendered = h
        .render(
            "{{ trino__get_binding_char() }}",
            context([(
                "target",
                Value::from_serialize(BTreeMap::from([("prepared_statements_enabled", true)])),
            )]),
        )
        .unwrap();
    assert_eq!(rendered.trim(), "%s");
}

#[test]
fn trino_schema_sync_drops_columns_before_adding() {
    let h = harness();
    h.render(
        "{{ trino__alter_relation_add_remove_columns(relation, added, removed) }}",
        context([
            ("relation", relation(&h, "orders", RelationType::Table)),
            ("added", columns(&[("new_int", "integer")])),
            ("removed", columns(&[("old_col", "varchar")])),
        ]),
    )
    .unwrap();
    let sql = executed_sql(h.mock())
        .iter()
        .map(|sql| squash(sql))
        .collect::<Vec<_>>();
    assert_eq!(
        sql,
        vec![
            "alter table \"memory\".\"analytics\".\"orders\" drop column \"old_col\"",
            "alter table \"memory\".\"analytics\".\"orders\" add column \"new_int\" integer",
        ]
    );
}

#[test]
fn trino_nested_column_paths_are_quoted_per_segment() {
    let h = harness();
    let sql = h
        .render(
            "{{ trino__nested_column_path(['payload', 'inner.field', 'x']) }}",
            BTreeMap::<String, Value>::new(),
        )
        .unwrap();
    assert_eq!(sql.trim(), "\"payload\".\"inner.field\".\"x\"");
}

/// A harness whose `adapter.diff_nested_column_types` is the real Trino implementation and whose
/// `adapter.get_columns_in_relation` returns `target_after_alter`.
fn nested_sync_harness(target_after_alter: &[(&str, &str)]) -> MacroTestHarness {
    let h = harness();
    let adapter = Arc::new(Adapter::new_parse_phase_adapter(
        AdapterType::Trino,
        dbt_yaml::Mapping::default(),
        default_dbt_quoting_for(AdapterType::Trino),
        Arc::new(DefaultTypeOps::new(AdapterType::Trino)),
        None,
    ));
    h.mock().on("diff_nested_column_types", move |args| {
        let env = minijinja::Environment::new();
        adapter.call_method_impl(
            &State::new_for_env(&env),
            "diff_nested_column_types",
            args,
            &[],
        )
    });
    let target_after_alter = columns(target_after_alter);
    h.mock().on("get_columns_in_relation", move |_| {
        Ok(target_after_alter.clone())
    });
    h
}

/// Renders `trino__sync_row_columns` for a `payload` ROW column and returns the result's
/// `schema_changed`.
fn sync_payload(
    h: &MacroTestHarness,
    on_schema_change: &str,
    source_type: &str,
    target_type: &str,
) -> dbt_common::FsResult<String> {
    let schema_changes = Value::from_serialize(BTreeMap::from([
        ("schema_changed", Value::from(true)),
        (
            "source_columns",
            columns(&[("id", "integer"), ("payload", source_type)]),
        ),
        (
            "target_columns",
            columns(&[("id", "integer"), ("payload", target_type)]),
        ),
        ("source_not_in_target", Value::from(Vec::<Value>::new())),
        ("target_not_in_source", Value::from(Vec::<Value>::new())),
        (
            "new_target_types",
            Value::from_serialize(vec![BTreeMap::from([
                ("column_name", "payload"),
                ("new_type", source_type),
            ])]),
        ),
    ]));
    h.render(
        "{{ trino__sync_row_columns(on_schema_change, relation, changes)['schema_changed'] }}",
        context([
            ("on_schema_change", Value::from(on_schema_change)),
            ("relation", relation(h, "events", RelationType::Table)),
            ("changes", schema_changes),
        ]),
    )
}

#[test]
fn trino_nested_row_sync_adds_fields_in_model_order() {
    let source = "row(a varchar, zeta varchar, alpha varchar, s row(x integer, y varchar))";
    let h = nested_sync_harness(&[("id", "integer"), ("payload", source)]);
    let schema_changed = sync_payload(&h, "append_new_columns", source, "row(a varchar)").unwrap();
    assert_eq!(schema_changed.trim(), "False");
    let sql = executed_sql(h.mock())
        .iter()
        .map(|sql| squash(sql))
        .collect::<Vec<_>>();
    let add = "alter table \"memory\".\"analytics\".\"events\" add column \"payload\"";
    assert_eq!(
        sql,
        vec![
            format!("{add}.\"zeta\" VARCHAR"),
            format!("{add}.\"alpha\" VARCHAR"),
            format!("{add}.\"s\" ROW(x INT, y VARCHAR)"),
        ]
    );
}

#[test]
fn trino_nested_row_sync_stops_when_fields_are_out_of_model_order() {
    let source = "row(a varchar, m varchar, b varchar)";
    let after_alter = "row(a varchar, b varchar, m varchar)";
    let h = nested_sync_harness(&[("id", "integer"), ("payload", after_alter)]);
    let err = sync_payload(&h, "sync_all_columns", source, "row(a varchar, b varchar)")
        .expect_err("a field added mid-row lands at the end");
    assert!(
        err.to_string().contains(
            "The ROW fields of column 'payload' in \"memory\".\"analytics\".\"events\" are \
             not in the model's order"
        ),
        "{err}"
    );
    assert!(err.to_string().contains("--full-refresh"), "{err}");
    assert_eq!(executed_sql(h.mock()).len(), 1);

    // The next run finds nothing to add and still refuses to write.
    let h = nested_sync_harness(&[]);
    let err = sync_payload(&h, "append_new_columns", source, after_alter)
        .expect_err("fields are still out of order");
    assert!(err.to_string().contains("--full-refresh"), "{err}");
    assert!(executed_sql(h.mock()).is_empty());
}

#[test]
fn trino_sync_column_schemas_keeps_synced_row_columns_out_of_the_flat_changes() {
    let mut h = nested_sync_harness(&[
        ("id", "integer"),
        ("payload", "row(a varchar, b varchar)"),
        ("old", "varchar"),
    ]);
    h.env_mut().env.add_global(
        "dbt_trino",
        Value::from_object(DbtNamespace::new("dbt_trino")),
    );
    let source = "row(a varchar, b varchar)";
    let changes = Value::from_serialize(BTreeMap::from([
        ("schema_changed", Value::from(true)),
        (
            "source_columns",
            columns(&[("id", "integer"), ("payload", source), ("note", "varchar")]),
        ),
        (
            "target_columns",
            columns(&[
                ("id", "integer"),
                ("payload", "row(a varchar)"),
                ("old", "varchar"),
            ]),
        ),
        ("source_not_in_target", columns(&[("note", "varchar")])),
        ("target_not_in_source", columns(&[("old", "varchar")])),
        (
            "new_target_types",
            Value::from_serialize(vec![BTreeMap::from([
                ("column_name", "payload"),
                ("new_type", source),
            ])]),
        ),
    ]));
    // The plain-named override in the dbt_trino package, not dbt-core's sync_column_schemas.
    h.render(
        "{{ dbt_trino.sync_column_schemas('sync_all_columns', relation, changes) }}",
        context([
            (
                "config",
                config(BTreeMap::from([("sync_nested_columns", Value::from(true))])),
            ),
            ("relation", relation(&h, "events", RelationType::Table)),
            ("changes", changes),
        ]),
    )
    .unwrap();
    let sql = executed_sql(h.mock())
        .iter()
        .map(|sql| squash(sql))
        .collect::<Vec<_>>();
    let alter = "alter table \"memory\".\"analytics\".\"events\"";
    // The ROW column gets its field and no flat type change; the other columns change as usual.
    assert_eq!(
        sql,
        vec![
            format!("{alter} add column \"payload\".\"b\" VARCHAR"),
            format!("{alter} drop column \"old\""),
            format!("{alter} add column \"note\" varchar"),
        ]
    );
}

fn materialization_calls(h: &MacroTestHarness) -> Vec<String> {
    h.mock()
        .observed_calls()
        .iter()
        .filter_map(|call| match call.method.as_str() {
            "execute" => call.args[0].as_str().map(squash),
            "drop_relation" => Some(format!("drop {}", call.args[0])),
            "rename_relation" => Some(format!("rename {} to {}", call.args[0], call.args[1])),
            _ => None,
        })
        .collect()
}

/// Runs the table materialization over an existing view `orders` and returns the statements
/// and relation calls in order.
fn replace_view_with_table(on_table_exists: &str) -> Vec<String> {
    let h = harness();
    let view = relation(&h, "orders", RelationType::View);
    h.mock().on("get_relation", move |args| {
        let identifier = args
            .last()
            .and_then(|kwargs| kwargs.get_attr("identifier").ok());
        Ok(match identifier.as_ref().and_then(Value::as_str) {
            Some("orders") => view.clone(),
            _ => Value::from(()),
        })
    });
    h.mock().on("drop_relation", |_| Ok(Value::UNDEFINED));
    h.mock().on("rename_relation", |_| Ok(Value::UNDEFINED));
    let ctx = h
        .materialization_context("orders", "select 1 as id")
        .database("memory")
        .schema("analytics")
        .relation_type(RelationType::Table)
        .config(config(BTreeMap::from([(
            "on_table_exists",
            Value::from(on_table_exists),
        )])))
        .build();
    h.render("{{ materialization_table_trino() }}", ctx)
        .unwrap_or_else(|e| panic!("{on_table_exists}: {e:?}"));
    materialization_calls(&h)
}

#[test]
fn trino_table_over_a_view_builds_first_in_rename_mode() {
    let calls = replace_view_with_table("rename");
    assert_eq!(calls.len(), 3, "{calls:?}");
    assert!(
        calls[0].starts_with(
            "create table \"memory\".\"analytics\".\"orders__dbt_tmp\" as ( select 1 as id )"
        ),
        "{calls:?}"
    );
    assert_eq!(
        calls[1..],
        [
            "drop \"memory\".\"analytics\".\"orders\"",
            "rename \"memory\".\"analytics\".\"orders__dbt_tmp\" to \"memory\".\"analytics\".\"orders\"",
        ]
    );
}

#[test]
fn trino_table_over_a_view_drops_first_in_drop_replace_and_skip_modes() {
    for (mode, create) in [
        ("drop", "create table \"memory\".\"analytics\".\"orders\""),
        (
            "replace",
            "create or replace table \"memory\".\"analytics\".\"orders\"",
        ),
        (
            "skip",
            "create table if not exists \"memory\".\"analytics\".\"orders\"",
        ),
    ] {
        let calls = replace_view_with_table(mode);
        assert_eq!(calls.len(), 2, "{mode}: {calls:?}");
        assert_eq!(
            calls[0], "drop \"memory\".\"analytics\".\"orders\"",
            "{mode}"
        );
        assert!(calls[1].starts_with(create), "{mode}: {calls:?}");
    }
}

/// A model with a description and `persist_docs: {relation: true}`.
fn documented_model() -> Value {
    Value::from_serialize(BTreeMap::from([
        ("description", Value::from("Orders, refreshed hourly")),
        ("columns", Value::from(BTreeMap::<String, Value>::new())),
        (
            "config",
            Value::from_serialize(BTreeMap::from([(
                "persist_docs",
                BTreeMap::from([("relation", true)]),
            )])),
        ),
    ]))
}

#[test]
fn trino_materialized_view_full_refresh_replaces_in_place_with_its_comment() {
    let h = harness();
    let mv = relation(&h, "orders_mv", RelationType::MaterializedView);
    let mut ctx = h
        .materialization_context("orders_mv", "select 1 as id")
        .config(config(BTreeMap::from([(
            "grace_period",
            Value::from("interval '1' hour"),
        )])))
        .build();
    ctx.insert("model".to_string(), documented_model());
    ctx.insert("mv".to_string(), mv);
    let sql = squash(
        &h.render("{{ get_replace_sql(mv, mv, compiled_code) }}", ctx)
            .unwrap(),
    );
    assert_eq!(
        sql,
        "create or replace materialized view \"memory\".\"analytics\".\"orders_mv\" \
         grace period interval '1' hour comment 'Orders, refreshed hourly' as select 1 as id ;"
    );
}

#[test]
fn trino_persist_docs_leaves_materialized_view_comments_to_create() {
    let h = harness();
    let docs_config = Arc::new(MockJinjaObject::new());
    docs_config.on("persist_relation_docs", |_| Ok(Value::from(true)));
    docs_config.on("persist_column_docs", |_| Ok(Value::from(false)));
    h.render(
        "{{ trino__persist_docs(mv, model, true, true) }}\
         {{ trino__persist_docs(table, model, true, true) }}",
        context([
            ("config", Value::from_dyn_object(docs_config)),
            ("model", documented_model()),
            (
                "mv",
                relation(&h, "orders_mv", RelationType::MaterializedView),
            ),
            ("table", relation(&h, "orders", RelationType::Table)),
            // dbt-trino v1 also synced docs to Starburst Data Discovery; v2 never calls it.
            (
                "target",
                Value::from_serialize(BTreeMap::from([("starburst_url", "https://sep.example")])),
            ),
        ]),
    )
    .unwrap();
    let sql = executed_sql(h.mock())
        .iter()
        .map(|sql| squash(sql))
        .collect::<Vec<_>>();
    assert_eq!(
        sql,
        vec!["comment on table \"memory\".\"analytics\".\"orders\" is 'Orders, refreshed hourly';"]
    );
}
