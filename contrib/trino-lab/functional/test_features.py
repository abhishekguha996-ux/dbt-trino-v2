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

    def test_mixed_case_names_refresh(self):
        # Trino stores catalog, schema and table names in lowercase; the second run must find the
        # materialized view and refresh it (dbt-trino v1 lowercases them in its metadata queries).
        for catalog in self.catalogs("iceberg"):
            for mv, mixed_case in (("MyMV", "schema"), ("mv", "catalog")):
                with self.subTest(catalog=catalog, model=mv, mixed_case=mixed_case):
                    p = self.project(catalog, {
                        "models/base.sql": "{{ config(materialized='table') }} select 1 as id",
                        f"models/{mv}.sql": "{{ config(materialized='materialized_view') }} "
                                            "select id from {{ ref('base') }}",
                    })
                    if mixed_case == "schema":
                        p.write_profile(schema=p.schema.title())
                    else:
                        p.write_profile(database=catalog.title())
                    p.dbt("run")
                    p.write("models/base.sql", "{{ config(materialized='table') }} select 2 as id")
                    p.dbt("run")
                    self.assertEqual(p.type_of(mv), "materialized_view")
                    self.assertEqual(p.rows(mv), [[2]])

    def test_failed_full_refresh_keeps_the_view(self):
        # Full refresh uses CREATE OR REPLACE MATERIALIZED VIEW, which keeps the old view when the
        # new definition fails (dbt-trino v1 drops it first).
        for catalog in self.catalogs("iceberg"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, {
                    "models/base.sql": "{{ config(materialized='table') }} select 1 as id",
                    "models/mv.sql": "{{ config(materialized='materialized_view') }} select id from {{ ref('base') }}",
                })
                p.dbt("run")
                p.write("models/mv.sql",
                        "{{ config(materialized='materialized_view') }} select missing_column from {{ ref('base') }}")
                result = p.dbt("run", "--full-refresh", "--select", "mv", expect=False)
                self.assertIn("Column 'missing_column' cannot be resolved", result.output)
                self.assertEqual(p.type_of("mv"), "materialized_view")
                self.assertEqual(p.rows("mv"), [[1]])


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

    @staticmethod
    def grants(p, grantee: str) -> list[list]:
        return p.query(
            f"select table_name, privilege_type from {p.catalog}.information_schema.table_privileges "
            f"where table_schema = '{p.schema}' and grantee = '{grantee}' order by 1, 2")

    def test_revoke_in_mixed_case_schema(self):
        def models(grantees: list[str]) -> dict[str, str]:
            grants = {"select": grantees}
            return {
                "models/gv.sql": f"{{{{ config(materialized='view', grants={grants}) }}}} select 1 as id",
                "models/gi.sql": f"{{{{ config(materialized='incremental', grants={grants}) }}}} select 1 as id",
            }

        for catalog in self.catalogs("hive"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, models(["user1", "dbt_ldap"]))
                p.write_profile(schema=p.schema.title())  # the same schema, spelled in mixed case
                p.dbt("run")
                for path, content in models(["user1"]).items():
                    p.write(path, content)
                result = p.dbt("run", expect=None)
                self.assertEqual(self.grants(p, "dbt_ldap"), [])
                self.assertEqual(self.grants(p, "user1"), [["gi", "SELECT"], ["gv", "SELECT"]])
                self.assertEqual(result.returncode, 0, result)

    def test_owner_keeps_its_own_privileges(self):
        # dbt connects as the schema owner without the admin role. Revoking grantees that are not
        # in the config must not revoke the owner's own privileges (dbt-trino v1 does, and the
        # third run then fails with Access Denied).
        for catalog in self.catalogs("hive"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, {
                    "models/oi.sql": "{{ config(materialized='incremental', grants={'select': ['dbt_ldap']}) }} "
                                     "select 1 as id",
                }, profile_overrides={"user": "user1", "roles": None})
                run_sql(f"alter schema {catalog}.{p.schema} set authorization user user1")
                for _ in range(3):
                    p.dbt("run")
                self.assertEqual(p.rows("oi"), [[1], [1], [1]])
                self.assertEqual(self.grants(p, "user1"),
                                 [["oi", "DELETE"], ["oi", "INSERT"], ["oi", "SELECT"], ["oi", "UPDATE"]])
                self.assertEqual(self.grants(p, "dbt_ldap"), [["oi", "SELECT"]])


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

    def test_materialized_view_comments(self):
        # Trino has no COMMENT ON MATERIALIZED VIEW: the relation comment is part of CREATE
        # MATERIALIZED VIEW, and column comments use COMMENT ON COLUMN (dbt-trino v1 fails).
        for catalog in self.catalogs("iceberg"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, {
                    "models/mv.sql": "{{ config(materialized='materialized_view') }} select 1 as id",
                    "models/schema.yml": """
                        version: 2
                        models:
                          - name: mv
                            description: "MV's description"
                            columns:
                              - name: id
                                description: "Id's column"
                    """,
                }, "models:\n  +persist_docs:\n    relation: true\n    columns: true\n")
                for args in ((), (), ("--full-refresh",)):  # create, refresh, replace
                    p.dbt("run", *args)
                    self.assertEqual(p.query(
                        "select comment from system.metadata.materialized_views "
                        f"where catalog_name = '{catalog}' and schema_name = '{p.schema}' and name = 'mv'"),
                        [["MV's description"]])
                    self.assertEqual(p.query(
                        f"select comment from {catalog}.information_schema.columns "
                        f"where table_schema = '{p.schema}' and table_name = 'mv'"), [["Id's column"]])


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


class TestUnitTestingTypes(TrinoTestCase):
    """dbt-trino v1 TestTrinoUnitTestingTypesTrinoStarburst (dbt-tests-adapter
    BaseUnitTestingTypes) plus a decimal with a scale: each value passes through a unit-test
    fixture unchanged."""

    DATA_TYPES = [  # sql_value, yaml_value
        ("1", "1"),
        ("'1'", "1"),
        ("true", "true"),
        ("DATE '2020-01-02'", "2020-01-02"),
        ("TIMESTAMP '2013-11-03 00:00:00'", "2013-11-03 00:00:00"),
        ("TIMESTAMP '2013-11-03 00:00:00-0'", "2013-11-03 00:00:00-0"),
        ("DECIMAL '1'", "1"),
        ("CAST(12.34 AS DECIMAL(10, 2))", "12.34"),
    ]

    def test_fixture_types(self):
        for catalog in self.catalogs("memory", "iceberg"):
            p = self.project(catalog, {
                "models/my_model.sql": "select tested_column from {{ ref('my_upstream_model') }}",
            })
            for sql_value, yaml_value in self.DATA_TYPES:
                with self.subTest(catalog=catalog, sql_value=sql_value):
                    p.write("models/my_upstream_model.sql", f"select {sql_value} as tested_column")
                    p.write("models/unit.yml", f"""
                        unit_tests:
                          - name: test_my_model
                            model: my_model
                            given:
                              - input: ref('my_upstream_model')
                                rows:
                                  - {{tested_column: {yaml_value}}}
                            expect:
                              rows:
                                - {{tested_column: {yaml_value}}}
                    """)
                    p.dbt("run", "--select", "my_upstream_model")
                    result = p.dbt("test", "--select", "test_type:unit", expect=None)
                    self.assertEqual(result.status("test_my_model"), "pass", result)


class TestUuid(TrinoTestCase):
    """The ADBC driver returns Trino uuid values as 16-byte binaries; dbt shows them as text."""

    UUID = "12151fd2-7586-11e9-8f9e-2a86e4085a59"

    def test_run_query(self):
        for catalog in self.catalogs("memory"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, {"macros/show_uuid.sql": f"""
                    {{% macro show_uuid() %}}
                      {{% set r = run_query("select uuid '{self.UUID}' as u, cast(null as uuid) as n") %}}
                      {{{{ log('UUID=' ~ r.rows[0][0] ~ ' NULL=' ~ r.rows[0][1], info=true) }}}}
                    {{% endmacro %}}
                """})
                self.assertIn(f"UUID={self.UUID} NULL=None", p.dbt("run-operation", "show_uuid").output)

    def test_enforced_contract(self):
        for catalog in self.catalogs("memory", "iceberg"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, {
                    "models/c.sql": f"{{{{ config(materialized='table') }}}} select uuid '{self.UUID}' as id, 'a' as name",
                    "models/schema.yml": """
                        version: 2
                        models:
                          - name: c
                            config:
                              contract: {enforced: true}
                            columns:
                              - name: id
                                data_type: uuid
                              - name: name
                                data_type: varchar
                    """,
                })
                p.dbt("run")
                self.assertEqual(p.rows("c"), [[self.UUID, "a"]])
                types = dict(p.query(
                    f"select column_name, data_type from {catalog}.information_schema.columns "
                    f"where table_schema = '{p.schema}' and table_name = 'c'"))
                self.assertEqual(types["id"], "uuid")

    def test_unit_test_fixture(self):
        for catalog in self.catalogs("memory", "iceberg"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, {
                    "models/src.sql": f"select uuid '{self.UUID}' as u, 1 as n",
                    "models/m.sql": "select u, n * 2 as doubled from {{ ref('src') }}",
                    "models/unit.yml": f"""
                        unit_tests:
                          - name: keeps_uuid
                            model: m
                            given:
                              - input: ref('src')
                                rows:
                                  - {{u: '{self.UUID}', n: 1}}
                            expect:
                              rows:
                                - {{u: '{self.UUID}', doubled: 2}}
                    """,
                })
                p.dbt("run")
                result = p.dbt("test", "--select", "test_type:unit", expect=None)
                self.assertEqual(result.status("keeps_uuid"), "pass", result)


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

    def test_string_literal_matches_dbt_default(self):
        # dbt.string_literal quotes without escaping, as on every other adapter; callers escape.
        for catalog in self.catalogs("memory"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, {
                    "models/s.sql": """select {{ dbt.string_literal(dbt.escape_single_quotes("O'Brien")) }} as name""",
                })
                p.dbt("run")
                self.assertEqual(p.rows("s"), [["O'Brien"]])


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

    def test_defer_without_favor_state(self):
        # The relation cache is hydrated at startup, so dbt knows that `a` is missing from the
        # development schema and defers to the state relation (as dbt-trino v1 does).
        for catalog in self.catalogs("memory", "iceberg"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, {
                    "models/a.sql": "{{ config(materialized='table') }} select 1 as id",
                    "models/b.sql": "{{ config(materialized='table') }} select id from {{ ref('a') }}",
                })
                p.dbt("run")
                state = p.dir / "state"
                (p.dir / "target").rename(state)
                p.write_profile(schema=p.schema + "_custom")
                if catalog != "memory":
                    run_sql(f"create schema if not exists {catalog}.{p.schema}_custom "
                            f"with (location = 's3://datalake/{catalog}/{p.schema}_custom')")
                p.dbt("run", "--select", "b", "--defer", "--state", str(state))
                self.assertEqual(run_sql(f'select id from {catalog}."{p.schema}_custom".b'), [[1]])


if __name__ == "__main__":
    unittest.main()
