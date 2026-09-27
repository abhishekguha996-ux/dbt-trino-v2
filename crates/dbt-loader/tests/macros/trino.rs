//! Tests for the dbt-trino macro package (vendored from dbt-trino v1.10.5 with v2 changes).

use std::collections::BTreeMap;
use std::sync::Arc;

use dbt_adapter::relation::RelationObject;
use dbt_adapter_core::AdapterType;
use dbt_jinja_ctx::DbtNamespace;
use dbt_jinja_utils::mock_object::MockJinjaObject;
use dbt_schemas::dbt_types::RelationType;
use minijinja::Value;

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
fn trino_literals_escape_apostrophes() {
    let h = harness();
    let sql = h
        .render(
            "{{ trino__string_literal(value) }}",
            BTreeMap::from([(
                "value".to_string(),
                Value::from("schema'; drop table x; --"),
            )]),
        )
        .unwrap();
    assert_eq!(sql.trim(), "'schema''; drop table x; --'");
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
fn trino_catalog_derives_information_schema_and_escapes_literals() {
    let h = harness();
    let table = RelationObject::new(h.relation(
        "iceberg",
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
    assert!(sql.contains("iceberg.INFORMATION_SCHEMA.tables"), "{sql}");
    assert!(sql.contains("iceberg.INFORMATION_SCHEMA.columns"), "{sql}");
    assert!(sql.contains("'sales''2026'"), "{sql}");
    assert!(sql.contains("decimal(38, 0)"), "{sql}");
    assert!(sql.contains("left join table_comment"), "{sql}");
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
            "{{ trino__get_delete_insert_merge_sql('target', 'source', 'id', columns, none) }}",
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
fn trino_nested_column_paths_are_quoted_per_segment() {
    let h = harness();
    let sql = h
        .render(
            "{{ trino__nested_column_path('payload.inner field.x') }}",
            BTreeMap::<String, Value>::new(),
        )
        .unwrap();
    assert_eq!(sql.trim(), "\"payload\".\"inner field\".\"x\"");
}
