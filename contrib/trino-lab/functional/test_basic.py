"""Core materializations, seeds and Trino table/view configs.

Modeled on dbt-trino v1 tests/functional/adapter/test_basic.py,
materialization/test_on_table_exists.py, test_table_properties.py and view_security tests.

Delta Lake on a Hive metastore cannot rename managed tables or views (Trino limitation shared
with dbt-trino v1), so Delta projects use `on_table_exists: replace`.
"""

import unittest

from harness import TrinoError, TrinoTestCase

SEED = """
id,name,some_date
1,Easton,1981-05-20 06:46:51
2,Lillian,1978-09-03 18:10:33
3,Jeremiah,1982-03-11 03:59:51
4,Nicholas,1976-05-25 07:34:22
5,Jack,1980-02-19 17:01:04
"""

MODELS = {
    "seeds/base.csv": SEED,
    "models/view_model.sql": "{{ config(materialized='view') }} select * from {{ ref('base') }}",
    "models/table_model.sql": "{{ config(materialized='table') }} select * from {{ ref('base') }}",
    "models/ephemeral_model.sql": "{{ config(materialized='ephemeral') }} select id, name from {{ ref('base') }} where id > 2",
    "models/from_ephemeral.sql": "{{ config(materialized='table') }} select * from {{ ref('ephemeral_model') }}",
    "models/schema.yml": """
        version: 2
        models:
          - name: table_model
            columns:
              - name: id
                data_tests: [unique, not_null]
          - name: view_model
            columns:
              - name: id
                data_tests: [unique, not_null]
    """,
}


def table_mode(catalog: str) -> str:
    return "models:\n  +on_table_exists: replace\n" if catalog == "delta" else ""


class TestBasicMaterializations(TrinoTestCase):
    def test_seed_table_view_ephemeral_and_rerun(self):
        for catalog in self.catalogs():
            with self.subTest(catalog=catalog):
                p = self.project(catalog, MODELS, table_mode(catalog))
                result = p.dbt("build")
                self.assertEqual(result.status("table_model"), "success")
                self.assertEqual(p.type_of("view_model"), "view")
                self.assertEqual(p.type_of("table_model"), "table")
                self.assertIsNone(p.type_of("ephemeral_model"))
                self.assertEqual(len(p.rows("table_model")), 5)
                self.assertEqual([r[0] for r in p.rows("from_ephemeral")], [3, 4, 5])
                seed_types = p.query(
                    f"select column_name, data_type from {catalog}.information_schema.columns "
                    f"where table_schema = '{p.schema}' and table_name = 'base' order by ordinal_position"
                )
                self.assertEqual([t[0] for t in seed_types], ["id", "name", "some_date"])
                self.assertEqual(seed_types[1][1], "varchar")
                self.assertTrue(seed_types[2][1].startswith("timestamp"), seed_types)
                # second run replaces relations in place (on_table_exists=rename default)
                p.dbt("build")
                self.assertEqual(len(p.rows("table_model")), 5)
                leftovers = p.query(
                    f"select table_name from {catalog}.information_schema.tables "
                    f"where table_schema = '{p.schema}' and table_name like '%__dbt_%'"
                )
                self.assertEqual(leftovers, [])

    def test_switch_view_to_table_and_back(self):
        for catalog in self.catalogs():
            with self.subTest(catalog=catalog):
                p = self.project(catalog, {"models/m.sql": "{{ config(materialized='view') }} select 1 as id"},
                                 table_mode(catalog))
                p.dbt("run")
                self.assertEqual(p.type_of("m"), "view")
                p.write("models/m.sql", "{{ config(materialized='table') }} select 1 as id")
                p.dbt("run")
                self.assertEqual(p.type_of("m"), "table")
                p.write("models/m.sql", "{{ config(materialized='view') }} select 2 as id")
                p.dbt("run")
                self.assertEqual(p.type_of("m"), "view")
                self.assertEqual(p.rows("m"), [[2]])


class TestOnTableExists(TrinoTestCase):
    def check(self, catalog: str, mode: str):
        p = self.project(catalog, {
            "models/m.sql": f"{{{{ config(materialized='table', on_table_exists='{mode}') }}}} select 1 as id",
        })
        p.dbt("run")
        p.write("models/m.sql", f"{{{{ config(materialized='table', on_table_exists='{mode}') }}}} select 2 as id")
        result = p.dbt("run", "--log-level", "debug")
        return p, result

    def test_rename(self):
        for catalog in self.catalogs("memory", "hive", "iceberg"):
            with self.subTest(catalog=catalog):
                p, result = self.check(catalog, "rename")
                self.assertEqual(p.rows("m"), [[2]])
                self.assertIn("__dbt_tmp", result.output)
                self.assertIn("__dbt_backup", result.output)

    def test_rename_unsupported_on_delta(self):
        for catalog in self.catalogs("delta"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, {"models/m.sql": "{{ config(materialized='table') }} select 1 as id"})
                p.dbt("run")
                result = p.dbt("run", expect=False)
                self.assertIn("Renaming managed tables is not allowed", result.output)

    def test_drop(self):
        for catalog in self.catalogs():
            with self.subTest(catalog=catalog):
                p, result = self.check(catalog, "drop")
                self.assertEqual(p.rows("m"), [[2]])
                self.assertNotIn("__dbt_backup", result.output)

    def test_replace(self):
        # CREATE OR REPLACE TABLE is supported by Iceberg and Delta Lake only.
        for catalog in self.catalogs("iceberg", "delta"):
            with self.subTest(catalog=catalog):
                p, result = self.check(catalog, "replace")
                self.assertEqual(p.rows("m"), [[2]])
                self.assertRegex(result.output.lower(), r"create or replace table")

    def test_skip(self):
        for catalog in self.catalogs():
            with self.subTest(catalog=catalog):
                p, result = self.check(catalog, "skip")
                self.assertEqual(p.rows("m"), [[1]])
                self.assertRegex(result.output.lower(), r"create table if not exists")


class TestViewSecurity(TrinoTestCase):
    def test_definer_and_invoker(self):
        for catalog in self.catalogs("hive", "iceberg", "delta", "memory"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, {
                    "models/v_default.sql": "{{ config(materialized='view') }} select 1 as id",
                    "models/v_invoker.sql": "{{ config(materialized='view', view_security='invoker') }} select 1 as id",
                })
                p.dbt("run")
                ddl_default = p.query(f"show create view {p.relation('v_default')}")[0][0]
                ddl_invoker = p.query(f"show create view {p.relation('v_invoker')}")[0][0]
                self.assertIn("SECURITY DEFINER", ddl_default)
                self.assertIn("SECURITY INVOKER", ddl_invoker)


class TestTableProperties(TrinoTestCase):
    def test_hive_properties(self):
        for catalog in self.catalogs("hive"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, {
                    "models/m.sql": """
                        {{ config(materialized='table',
                                  properties={'format': "'PARQUET'", 'partitioned_by': "ARRAY['d']"}) }}
                        select 1 as id, date '2024-01-01' as d
                    """,
                })
                p.dbt("run")
                ddl = p.query(f"show create table {p.relation('m')}")[0][0]
                self.assertIn("format = 'PARQUET'", ddl)
                self.assertIn("partitioned_by = ARRAY['d']", ddl)

    def test_iceberg_properties_and_file_format(self):
        for catalog in self.catalogs("iceberg"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, {
                    "models/m.sql": """
                        {{ config(materialized='table', file_format='ORC',
                                  properties={'partitioning': "ARRAY['day(ts)']"}) }}
                        select 1 as id, timestamp '2024-01-01 10:00:00' as ts
                    """,
                })
                p.dbt("run")
                ddl = p.query(f"show create table {p.relation('m')}")[0][0]
                self.assertIn("format = 'ORC'", ddl)
                self.assertIn("partitioning = ARRAY['day(ts)']", ddl)

    def test_conflicting_format_configs_fail(self):
        for catalog in self.catalogs("iceberg"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, {
                    "models/m.sql": """
                        {{ config(materialized='table', file_format='ORC', properties={'format': "'PARQUET'"}) }}
                        select 1 as id
                    """,
                })
                result = p.dbt("run", expect=False)
                self.assertIn("either 'file_format' or 'properties.format'", result.output)


class TestSqlHeader(TrinoTestCase):
    def test_sql_header_session_property(self):
        for catalog in self.catalogs("memory"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, {
                    "models/m.sql": """
                        {{ config(materialized='table') }}
                        {% call set_sql_header(config) %}
                        set session query_max_run_time = '1h';
                        {%- endcall %}
                        select 1 as id
                    """,
                })
                p.dbt("run")
                self.assertEqual(p.rows("m"), [[1]])


if __name__ == "__main__":
    unittest.main()
