use std::collections::BTreeMap;

use dbt_adapter::relation::RelationObject;
use dbt_adapter_core::AdapterType;
use dbt_jinja_ctx::DbtNamespace;
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
fn trino_drop_and_rename_preserve_relation_kind() {
    for kind in [RelationType::Table, RelationType::View] {
        let h = harness();
        let relation = RelationObject::new(h.relation("memory", "analytics", "orders", Some(kind)))
            .into_value();
        let renamed = RelationObject::new(h.relation("memory", "analytics", "renamed", Some(kind)))
            .into_value();
        let ctx = BTreeMap::from([
            ("relation".to_string(), relation),
            ("renamed".to_string(), renamed),
        ]);
        h.render(
            "{{ trino__rename_relation(relation, renamed) }}{{ trino__drop_relation(relation) }}",
            ctx,
        )
        .unwrap();
        let sql = executed_sql(h.mock()).join("\n");
        let noun = if kind == RelationType::View {
            "view"
        } else {
            "table"
        };
        assert!(sql.contains(&format!("alter {noun}")), "{sql}");
        assert!(sql.contains(&format!("drop {noun} if exists")), "{sql}");
        assert!(!sql.contains("cascade"), "{sql}");
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
fn trino_catalog_qualifies_catalog_and_escapes_schema() {
    let h = harness();
    let relation = RelationObject::new(h.relation(
        "iceberg",
        "sales'2026",
        "orders",
        Some(RelationType::Table),
    ))
    .into_value();
    let ctx = BTreeMap::from([
        ("information_schema".to_string(), relation.clone()),
        ("relations".to_string(), Value::from(vec![relation])),
    ]);
    h.render(
        "{{ trino__get_catalog_relations(information_schema, relations) }}",
        ctx,
    )
    .unwrap();
    let sql = executed_sql(h.mock()).join("\n");
    assert!(
        sql.contains("\"iceberg\".information_schema.tables"),
        "{sql}"
    );
    assert!(sql.contains("'sales''2026'"), "{sql}");
    assert!(sql.contains("decimal(38,0)"), "{sql}");
}

#[test]
fn trino_merge_qualifies_insert_values_without_changing_default_sql() {
    let mut h = harness();
    h.env_mut().env.add_global(
        "config",
        Value::from_dyn_object(crate::macro_test_harness::default_mock_config()),
    );
    let columns = Value::from_serialize(vec![
        BTreeMap::from([("name", "id"), ("quoted", "\"id\"")]),
        BTreeMap::from([("name", "a\"b"), ("quoted", "\"a\"\"b\"")]),
    ]);
    for (name, expected) in [
        (
            "trino__get_merge_sql",
            "values (DBT_INTERNAL_SOURCE.\"id\", DBT_INTERNAL_SOURCE.\"a\"\"b\")",
        ),
        ("default__get_merge_sql", "values (\"id\", \"a\"\"b\")"),
    ] {
        let sql = h
            .render(
                &format!("{{{{ {name}('target', 'source', ['id'], columns) }}}}"),
                BTreeMap::from([("columns".to_string(), columns.clone())]),
            )
            .unwrap();
        let sql = sql.split_whitespace().collect::<Vec<_>>().join(" ");
        assert!(sql.contains(expected), "{sql}");
    }
}

#[test]
fn trino_seeds_cast_bindings_to_inferred_and_overridden_types() {
    let h = harness();
    h.mock().on("quote_seed_column", |args| Ok(args[0].clone()));
    h.mock().on("convert_type", |_| Ok(Value::from("varchar")));
    h.mock().on("add_query", |_| Ok(Value::UNDEFINED));
    let ctx = h
        .materialization_context("seed_values", "")
        .database("memory")
        .schema("analytics")
        .relation_type(RelationType::Table)
        .build();
    let mut ctx = ctx;
    ctx.insert(
        "model".to_string(),
        Value::from_serialize(BTreeMap::from([(
            "config",
            BTreeMap::from([(
                "column_types",
                BTreeMap::from([("day", "date"), ("amount", "decimal(18,2)")]),
            )]),
        )])),
    );
    ctx.insert(
        "agate_table".to_string(),
        Value::from_serialize(BTreeMap::from([
            ("column_names", Value::from(vec!["day", "amount", "note"])),
            (
                "rows",
                Value::from_serialize(vec![vec!["2026-01-01", "0.10", "O'Brien"]]),
            ),
        ])),
    );
    for (name, expected) in [
        ("trino__load_csv_rows", "cast(%s as date)"),
        ("default__load_csv_rows", "values (%s"),
    ] {
        let sql = h
            .render(
                &format!("{{{{ {name}(model, agate_table) }}}}"),
                ctx.clone(),
            )
            .unwrap();
        let sql = sql.split_whitespace().collect::<Vec<_>>().join(" ");
        assert!(sql.contains(expected), "{sql}");
        if name == "trino__load_csv_rows" {
            assert!(sql.contains("cast(%s as decimal(18,2))"), "{sql}");
            assert!(sql.contains("cast(%s as varchar)"), "{sql}");
        }
        assert!(
            !sql.contains("O'Brien"),
            "Bindings must stay separate from SQL templates"
        );
    }
}
