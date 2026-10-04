"""Snapshots, materialized views, grants, docs, contracts, seeds, unit tests and commands.

Modeled on dbt-trino v1 tests/functional/adapter/{test_simple_snapshot.py,
materialized_view_tests, test_grants.py, persist_docs, constraints, simple_seed,
unit_testing, hooks, test_session_property.py, utils, dbt_show, dbt_clone, empty}.
"""

import json
import unittest

from harness import TrinoTestCase, run_sql

ROW_LEVEL = ("iceberg", "delta")


def delta_replace(catalog: str) -> str:
    return "models:\n  +on_table_exists: replace\n" if catalog == "delta" else ""


class TestSnapshots(TrinoTestCase):
    SRC_V1 = "id,status,updated_at\n1,new,2024-01-01 00:00:00\n2,new,2024-01-01 00:00:00\n"
    SRC_V2 = "id,status,updated_at\n1,shipped,2024-01-02 00:00:00\n3,new,2024-01-02 00:00:00\n"

    def snapshot(self, strategy: str, extra: str = "") -> str:
        if strategy == "timestamp":
            cfg = "strategy='timestamp', updated_at='updated_at'"
        else:
            cfg = "strategy='check', check_cols=['status']"
        return f"""
            {{% snapshot orders_snapshot %}}
            {{{{ config(target_schema=target.schema ~ '_snapshots', unique_key='id', {cfg} {extra}) }}}}
            select * from {{{{ ref('orders') }}}}
            {{% endsnapshot %}}
        """

    def run_snapshot(self, catalog: str, strategy: str, extra: str = ""):
        p = self.project(catalog, {"seeds/orders.csv": self.SRC_V1,
                                   "snapshots/orders_snapshot.sql": self.snapshot(strategy, extra)})
        run_sql(f"create schema if not exists {catalog}.{p.schema}_snapshots "
                f"with (location = 's3://datalake/{catalog}/{p.schema}_snapshots')")
        p.dbt("seed")
        p.dbt("snapshot")
        p.write("seeds/orders.csv", self.SRC_V2)
        p.dbt("seed", "--full-refresh")
        p.dbt("snapshot")
        rows = run_sql(f'select id, status, dbt_valid_to is null from {catalog}."{p.schema}_snapshots".orders_snapshot '
                       "order by id, dbt_valid_from")
        return p, rows

    def test_timestamp_strategy(self):
        for catalog in self.catalogs(*ROW_LEVEL):
            with self.subTest(catalog=catalog):
                _, rows = self.run_snapshot(catalog, "timestamp")
                self.assertEqual(rows, [[1, "new", False], [1, "shipped", True], [2, "new", True], [3, "new", True]])

    def test_check_strategy_with_hard_deletes(self):
        for catalog in self.catalogs(*ROW_LEVEL):
            with self.subTest(catalog=catalog):
                _, rows = self.run_snapshot(catalog, "check", ", hard_deletes='invalidate'")
                # id 2 disappeared from the source and is invalidated
                self.assertEqual(rows, [[1, "new", False], [1, "shipped", True], [2, "new", False], [3, "new", True]])


class TestMaterializedViews(TrinoTestCase):
    def test_create_refresh_and_full_refresh(self):
        # OSS Trino supports materialized views on the Iceberg connector.
        for catalog in self.catalogs("iceberg"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, {
                    "seeds/base.csv": "id,v\n1,10\n2,20\n",
                    "models/mv.sql": "{{ config(materialized='materialized_view', grace_period='INTERVAL \\'1\\' HOUR') }} "
                                     "select id, v * 2 as v2 from {{ ref('base') }}",
                })
                p.dbt("seed")
                p.dbt("run")
                self.assertEqual(p.type_of("mv"), "materialized_view")
                self.assertEqual(p.rows("mv"), [[1, 20], [2, 40]])
                ddl = p.query(f"show create materialized view {p.relation('mv')}")[0][0]
                self.assertIn("GRACE PERIOD", ddl.upper())
                p.write("seeds/base.csv", "id,v\n1,10\n2,20\n3,30\n")
                p.dbt("seed", "--full-refresh")
                p.dbt("run")  # refresh
                self.assertEqual(len(p.rows("mv")), 3)
                p.dbt("run", "--full-refresh")
                self.assertEqual(p.type_of("mv"), "materialized_view")
                self.assertEqual(len(p.rows("mv")), 3)

    def test_mv_replaces_table(self):
        for catalog in self.catalogs("iceberg"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, {"models/m.sql": "{{ config(materialized='table') }} select 1 as id"})
                p.dbt("run")
                p.write("models/m.sql", "{{ config(materialized='materialized_view') }} select 1 as id")
                p.dbt("run")
                self.assertEqual(p.type_of("m"), "materialized_view")


class TestGrants(TrinoTestCase):
    def test_grant_and_revoke(self):
        # Hive with sql-standard security supports GRANT/REVOKE in OSS Trino.
        for catalog in self.catalogs("hive"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, {
                    "models/m.sql": "{{ config(materialized='table', grants={'select': ['user1']}) }} select 1 as id",
                })
                p.dbt("run")
                grants = p.query(
                    f"select grantee, privilege_type from {catalog}.information_schema.table_privileges "
                    f"where table_schema = '{p.schema}' and table_name = 'm' and grantee = 'user1'")
                self.assertEqual(grants, [["user1", "SELECT"]])
                p.write("models/m.sql", "{{ config(materialized='table', grants={'insert': ['user1']}) }} select 1 as id")
                p.dbt("run")
                grants = p.query(
                    f"select privilege_type from {catalog}.information_schema.table_privileges "
                    f"where table_schema = '{p.schema}' and table_name = 'm' and grantee = 'user1'")
                self.assertEqual(grants, [["INSERT"]])


class TestPersistDocs(TrinoTestCase):
    FILES = {
        "models/t.sql": "{{ config(materialized='table') }} select 1 as id, 'x' as name",
        "models/v.sql": "{{ config(materialized='view') }} select 1 as id",
        "models/schema.yml": """
            version: 2
            models:
              - name: t
                description: "Table's description"
                columns:
                  - name: id
                    description: "Id's column"
                  - name: name
                    description: "Name column"
              - name: v
                description: "View description"
        """,
    }

    def test_relation_and_column_comments(self):
        for catalog in self.catalogs("hive", "iceberg", "delta"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, self.FILES,
                                 "models:\n  +persist_docs:\n    relation: true\n    columns: true\n" +
                                 ("  +on_table_exists: replace\n" if catalog == "delta" else ""))
                p.dbt("run")
                comment = p.query(
                    "select comment from system.metadata.table_comments "
                    f"where catalog_name = '{catalog}' and schema_name = '{p.schema}' and table_name = 't'")
                self.assertEqual(comment, [["Table's description"]])
                cols = dict(p.query(
                    f"select column_name, comment from {catalog}.information_schema.columns "
                    f"where table_schema = '{p.schema}' and table_name = 't'"))
                self.assertEqual(cols, {"id": "Id's column", "name": "Name column"})
                p.dbt("run")  # rerun keeps comments
                self.assertEqual(p.query(
                    "select comment from system.metadata.table_comments "
                    f"where catalog_name = '{catalog}' and schema_name = '{p.schema}' and table_name = 't'"),
                    [["Table's description"]])


class TestContracts(TrinoTestCase):
    def test_enforced_contract_with_not_null(self):
        for catalog in self.catalogs("memory", "iceberg", "delta"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, {
                    "models/c.sql": "{{ config(materialized='table') }} select 1 as id, 'a' as name",
                    "models/schema.yml": """
                        version: 2
                        models:
                          - name: c
                            config:
                              contract: {enforced: true}
                            columns:
                              - name: id
                                data_type: integer
                                constraints: [{type: not_null}]
                              - name: name
                                data_type: varchar
                    """,
                }, delta_replace(catalog))
                p.dbt("run")
                self.assertEqual(p.rows("c"), [[1, "a"]])
                if catalog != "memory":
                    ddl = p.query(f"show create table {p.relation('c')}")[0][0]
                    self.assertIn("NOT NULL", ddl.upper())

    def test_contract_mismatch_fails(self):
        for catalog in self.catalogs("memory"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, {
                    "models/c.sql": "{{ config(materialized='table') }} select 'x' as id",
                    "models/schema.yml": """
                        version: 2
                        models:
                          - name: c
                            config:
                              contract: {enforced: true}
                            columns:
                              - name: id
                                data_type: integer
                    """,
                })
                result = p.dbt("run", expect=False)
                self.assertRegex(result.output.lower(), r"contract|data type|mismatch")


class TestSeeds(TrinoTestCase):
    SEED = (
        "id,name,price,is_active,created_on,created_at,notes\n"
        "1,O'Brien,9.99,true,2024-01-31,2024-01-31 10:00:00,\"comma, inside\"\n"
        "2,Zoë ☃,10.5,false,2024-02-29,2024-02-29 23:59:59,%s literal\n"
        "3,,,,,,\n"
    )

    def test_types_escaping_and_nulls(self):
        for catalog in self.catalogs():
            with self.subTest(catalog=catalog):
                p = self.project(catalog, {"seeds/s.csv": self.SEED})
                p.dbt("seed")
                rows = p.query(f"select id, name, cast(price as varchar), is_active, cast(created_on as varchar), "
                               f"cast(created_at as varchar), notes from {p.relation('s')} order by id")
                self.assertEqual(rows[0][:2], [1, "O'Brien"])
                self.assertEqual(rows[1][1], "Zoë ☃")
                self.assertEqual(rows[0][3:5], [True, "2024-01-31"])
                self.assertTrue(rows[1][5].startswith("2024-02-29 23:59:59"))
                self.assertEqual(rows[0][6], "comma, inside")
                self.assertEqual(rows[1][6], "%s literal")
                self.assertEqual(rows[2][1:], [None] * 6)

    def test_column_types_override_and_json(self):
        # Iceberg stores varchar(n) as unbounded varchar, so bounded lengths are checked on memory.
        for catalog in self.catalogs("memory"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, {
                    "seeds/s.csv": "id,amount,code,payload,day\n1,12.30,00123,\"{\"\"k\"\": 1}\",2024-01-01\n",
                }, """
seeds:
  functional:
    s:
      +column_types:
        amount: decimal(10,2)
        code: varchar(10)
        day: timestamp(3)
""")
                p.dbt("seed")
                types = dict(p.query(
                    f"select column_name, data_type from {catalog}.information_schema.columns "
                    f"where table_schema = '{p.schema}' and table_name = 's'"))
                self.assertEqual(types["amount"], "decimal(10,2)")
                self.assertEqual(types["code"], "varchar(10)")
                self.assertEqual(types["day"], "timestamp(3)")
                self.assertEqual(p.query(f"select cast(amount as varchar), code from {p.relation('s')}"),
                                 [["12.30", "00123"]])

    def test_integer_inference_matches_dbt_trino_v1(self):
        for catalog in self.catalogs("memory"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, {"seeds/n.csv": "small,big,ratio\n1,3000000000,1.5\n2,4,2.0\n"})
                p.dbt("seed")
                types = dict(p.query(
                    f"select column_name, data_type from {catalog}.information_schema.columns "
                    f"where table_schema = '{p.schema}' and table_name = 'n'"))
                self.assertEqual(types, {"small": "integer", "big": "bigint", "ratio": "double"})

    def test_large_seed_batches(self):
        for catalog in self.catalogs("memory", "iceberg"):
            with self.subTest(catalog=catalog):
                lines = ["id,label"] + [f"{i},row {i}" for i in range(2500)]
                p = self.project(catalog, {"seeds/big.csv": "\n".join(lines) + "\n"})
                p.dbt("seed")
                self.assertEqual(p.query(f"select count(*), sum(id) from {p.relation('big')}"),
                                 [[2500, sum(range(2500))]])


class TestUnitTests(TrinoTestCase):
    def test_unit_test_passes_and_fails(self):
        for catalog in self.catalogs("memory", "iceberg"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, {
                    "seeds/orders.csv": "id,amount,ordered_at\n1,10,2024-01-01\n",
                    "models/order_totals.sql": """
                        select id, amount * 2 as doubled, cast(ordered_at as date) as d
                        from {{ ref('orders') }}
                    """,
                    "models/unit.yml": """
                        unit_tests:
                          - name: doubles_amount
                            model: order_totals
                            given:
                              - input: ref('orders')
                                rows:
                                  - {id: 1, amount: 5, ordered_at: 2024-03-01}
                                  - {id: 2, amount: 7, ordered_at: 2024-03-02}
                            expect:
                              rows:
                                - {id: 1, doubled: 10, d: 2024-03-01}
                                - {id: 2, doubled: 14, d: 2024-03-02}
                          - name: wrong_expectation
                            model: order_totals
                            given:
                              - input: ref('orders')
                                rows:
                                  - {id: 1, amount: 5, ordered_at: 2024-03-01}
                            expect:
                              rows:
                                - {id: 1, doubled: 11, d: 2024-03-01}
                    """,
                })
                p.dbt("seed")
                p.dbt("run")
                result = p.dbt("test", "--select", "test_type:unit", expect=False)
                self.assertEqual(result.status("doubles_amount"), "pass", result)
                # dbt v2 records a failing unit test as "error" in run_results.json
                self.assertIn(result.status("wrong_expectation"), ("fail", "error"), result)
                self.assertIn("11 -> 10", result.output)


class TestHooksAndSession(TrinoTestCase):
    def test_hooks_and_set_session(self):
        for catalog in self.catalogs("memory"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, {
                    "models/m.sql": """
                        {{ config(materialized='table',
                                  pre_hook="set session query_max_run_time = '5s'",
                                  post_hook="insert into {{ this }} values (99)") }}
                        select 1 as id
                    """,
                }, """
on-run-start:
  - "create table if not exists {{ target.database }}.{{ target.schema }}.run_log (event varchar)"
  - "insert into {{ target.database }}.{{ target.schema }}.run_log values ('start')"
on-run-end:
  - "insert into {{ target.database }}.{{ target.schema }}.run_log values ('end')"
""")
                p.dbt("run")
                self.assertEqual(p.rows("m"), [[1], [99]])
                self.assertEqual(p.rows("run_log"), [["end"], ["start"]])

    def test_profile_session_properties(self):
        for catalog in self.catalogs("memory"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, {
                    "models/m.sql": "{{ config(materialized='table') }} select 1 as id",
                    "macros/show_prop.sql": """
                        {% macro show_prop() %}
                          {% set r = run_query("show session like 'query_max_run_time'") %}
                          {{ log('PROP=' ~ r.rows[0][1], info=true) }}
                        {% endmacro %}
                    """,
                }, profile_overrides={"session_properties": {"query_max_run_time": "7m"}})
                result = p.dbt("run-operation", "show_prop")
                self.assertIn("PROP=7m", result.output)


class TestCrossDatabaseMacros(TrinoTestCase):
    def test_utils(self):
        for catalog in self.catalogs("memory"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, {
                    "models/u.sql": """
                        select
                          {{ dbt.datediff("date '2024-01-01'", "date '2024-03-01'", 'day') }} as dd,
                          {{ dbt.dateadd('day', 3, "date '2024-01-01'") }} as da,
                          {{ dbt.date_trunc('month', "date '2024-03-15'") }} as dt,
                          {{ dbt.hash("'abc'") }} as h,
                          {{ dbt.listagg("x", "','", "order by x") }} as la,
                          {{ dbt.split_part("'a-b-c'", "'-'", 2) }} as sp,
                          {{ dbt.right("'hello'", 2) }} as r,
                          {{ dbt.safe_cast("'12'", dbt.type_int()) }} as sc,
                          {{ dbt.bool_or("x > 'a'") }} as bo,
                          {{ dbt.any_value("x") }} as av,
                          {{ dbt.concat(["'a'", "'b'"]) }} as c,
                          {{ dbt.cast_bool_to_text("true") }} as bt
                        from (values 'a', 'b') as t(x)
                    """,
                    "models/spine.sql": "{{ dbt.date_spine('day', \"date '2024-01-01'\", \"date '2024-01-05'\") }}",
                })
                p.dbt("run")
                row = p.rows("u")[0]
                self.assertEqual(row[0], 60)
                self.assertEqual(str(row[1]), "2024-01-04")
                self.assertEqual(row[3], "900150983cd24fb0d6963f7d28e17f72")
                self.assertEqual(row[4:7], ["a,b", "b", "lo"])
                self.assertEqual(row[7], 12)
                self.assertEqual(len(p.rows("spine")), 4)


class TestCommands(TrinoTestCase):
    FILES = {
        "seeds/base.csv": "id,name,loaded_at\n1,a,2024-01-01 00:00:00\n2,b,2024-01-02 00:00:00\n",
        "models/t.sql": "{{ config(materialized='table') }} select * from {{ ref('base') }}",
        "models/v.sql": "select * from {{ ref('t') }}",
        "models/sources.yml": """
            version: 2
            sources:
              - name: raw
                schema: "{{ target.schema }}"
                tables:
                  - name: base
                    config:
                      loaded_at_field: loaded_at
                      freshness:
                        warn_after: {count: 1, period: day}
        """,
    }

    def test_debug_parse_compile_list_show(self):
        for catalog in self.catalogs("memory"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, self.FILES)
                self.assertIn("All checks passed", p.dbt("debug").output)
                p.dbt("parse")
                p.dbt("seed")
                p.dbt("compile")
                listed = p.dbt("list", "--resource-type", "model").output
                self.assertIn("functional.t", listed)
                shown = p.dbt("show", "--select", "t", "--limit", "1").output
                self.assertIn("name", shown)
                inline = p.dbt("show", "--inline", "select 42 as answer").output
                self.assertIn("42", inline)

    def test_docs_generate_catalog(self):
        for catalog in self.catalogs("memory", "iceberg"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, self.FILES)
                p.dbt("build")
                p.dbt("docs", "generate")
                self.assertTrue((p.dir / "target" / "index.html").exists())
                # dbt v2 writes catalog.json with `compile --write-catalog`
                p.dbt("compile", "--write-catalog")
                catalog_json = json.loads((p.dir / "target" / "catalog.json").read_text())
                self.assertEqual(catalog_json["errors"] or [], [])
                node = catalog_json["nodes"]["model.functional.t"]
                self.assertEqual(sorted(node["columns"]), ["id", "loaded_at", "name"])
                self.assertEqual(node["metadata"]["type"].upper(), "BASE TABLE")

    def test_empty_flag_and_retry(self):
        for catalog in self.catalogs("memory"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, self.FILES)
                p.dbt("seed")
                p.dbt("run", "--empty")
                self.assertEqual(p.rows("t"), [])
                p.write("models/v.sql", "select * from {{ ref('t') }} where missing_column = 1")
                p.dbt("run", expect=False)
                p.write("models/v.sql", "select * from {{ ref('t') }}")
                p.dbt("retry")

    def test_source_freshness(self):
        for catalog in self.catalogs("memory"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, self.FILES)
                p.dbt("seed")
                result = p.dbt("source", "freshness", expect=None)
                self.assertIn("raw.base", result.output)
                self.assertNotIn("panicked", result.output)

    def test_clone(self):
        for catalog in self.catalogs("iceberg"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, self.FILES)
                p.dbt("build")
                state = p.dir / "state"
                (p.dir / "target").rename(state)
                p.write_profile(schema=p.schema + "_custom")
                run_sql(f"create schema if not exists {catalog}.{p.schema}_custom "
                        f"with (location = 's3://datalake/{catalog}/{p.schema}_custom')")
                p.dbt("clone", "--state", str(state))
                cloned = run_sql(f"select count(*) from {catalog}.\"{p.schema}_custom\".t")
                self.assertEqual(cloned, [[2]])


if __name__ == "__main__":
    unittest.main()
