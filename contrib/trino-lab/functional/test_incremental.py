"""Incremental materializations: strategies, schema changes and options.

Modeled on dbt-trino v1 tests/functional/adapter/materialization/test_incremental_*.py.
Row-level DELETE/MERGE are supported by the Iceberg and Delta Lake connectors; Hive (non-ACID)
and Memory support appends only, matching Trino's connector capabilities.
"""

import unittest

from harness import TrinoTestCase

ROW_LEVEL = ("iceberg", "delta")

SOURCE_V1 = """
id,name,amount,updated_at
1,alpha,10,2024-01-01
2,beta,20,2024-01-01
3,gamma,30,2024-01-01
"""
SOURCE_V2 = """
id,name,amount,updated_at
1,alpha,10,2024-01-01
2,beta-updated,25,2024-01-02
3,gamma,30,2024-01-01
4,delta,40,2024-01-02
"""


def incremental(strategy: str, extra: str = "", select: str = "select * from {{ ref('src') }}") -> str:
    return f"""
        {{{{ config(materialized='incremental', incremental_strategy='{strategy}' {extra}) }}}}
        {select}
        {{% if is_incremental() %}}
        where updated_at > (select max(updated_at) from {{{{ this }}}})
        {{% endif %}}
    """


class IncrementalBase(TrinoTestCase):
    def run_two_phases(self, catalog: str, model: str, config: str = ""):
        p = self.project(catalog, {"seeds/src.csv": SOURCE_V1, "models/inc.sql": model},
                         ("models:\n  +on_table_exists: replace\n" if catalog == "delta" else "") + config)
        p.dbt("seed")
        p.dbt("run")
        p.write("seeds/src.csv", SOURCE_V2)
        p.dbt("seed", "--full-refresh")
        p.dbt("run")
        return p


class TestAppend(IncrementalBase):
    def test_append_all_catalogs(self):
        for catalog in self.catalogs():
            with self.subTest(catalog=catalog):
                p = self.run_two_phases(catalog, incremental("append"))
                ids = [r[0] for r in p.rows("inc", "id, updated_at")]
                # rows 2 (new version) and 4 were appended; the old row 2 stays
                self.assertEqual(ids, [1, 2, 2, 3, 4])

    def test_default_strategy_is_append(self):
        for catalog in self.catalogs("memory", "iceberg"):
            with self.subTest(catalog=catalog):
                p = self.run_two_phases(catalog, incremental("append").replace(
                    "incremental_strategy='append'", "on_schema_change='ignore'"))
                self.assertEqual(len(p.rows("inc")), 5)

    def test_full_refresh(self):
        for catalog in self.catalogs():
            with self.subTest(catalog=catalog):
                p = self.run_two_phases(catalog, incremental("append"))
                p.dbt("run", "--full-refresh")
                self.assertEqual([r[0] for r in p.rows("inc")], [1, 2, 3, 4])

    def test_views_enabled_false_uses_temp_table(self):
        for catalog in self.catalogs("memory", "iceberg"):
            with self.subTest(catalog=catalog):
                p = self.run_two_phases(catalog, incremental("append", ", views_enabled=false"))
                self.assertEqual(len(p.rows("inc")), 5)
                leftovers = p.query(
                    f"select table_name from {catalog}.information_schema.tables "
                    f"where table_schema = '{p.schema}' and table_name like '%dbt_tmp%'")
                self.assertEqual(leftovers, [])


class TestMerge(IncrementalBase):
    def test_merge_single_key(self):
        for catalog in self.catalogs(*ROW_LEVEL):
            with self.subTest(catalog=catalog):
                p = self.run_two_phases(catalog, incremental("merge", ", unique_key='id'"))
                self.assertEqual(p.rows("inc", "id"), [
                    [1, "alpha", 10, p.rows("inc", "id")[0][3]],
                    [2, "beta-updated", 25, p.rows("inc", "id")[1][3]],
                    [3, "gamma", 30, p.rows("inc", "id")[2][3]],
                    [4, "delta", 40, p.rows("inc", "id")[3][3]],
                ])

    def test_merge_composite_key_and_update_columns(self):
        for catalog in self.catalogs(*ROW_LEVEL):
            with self.subTest(catalog=catalog):
                p = self.run_two_phases(catalog, incremental(
                    "merge", ", unique_key=['id', 'name'], merge_update_columns=['amount']"))
                names = [r[1] for r in p.rows("inc", "id, name")]
                # composite key: beta-updated is a new key, so both versions exist
                self.assertEqual(names, ["alpha", "beta", "beta-updated", "gamma", "delta"])

    def test_merge_exclude_columns(self):
        for catalog in self.catalogs(*ROW_LEVEL):
            with self.subTest(catalog=catalog):
                p = self.run_two_phases(catalog, incremental(
                    "merge", ", unique_key='id', merge_exclude_columns=['name']"))
                row2 = p.rows("inc", "id")[1]
                self.assertEqual(row2[1:3], ["beta", 25])

    def test_merge_incremental_predicates(self):
        for catalog in self.catalogs(*ROW_LEVEL):
            with self.subTest(catalog=catalog):
                p = self.run_two_phases(catalog, incremental(
                    "merge", ", unique_key='id', incremental_predicates=['DBT_INTERNAL_DEST.id > 2']"))
                rows = p.rows("inc", "id, name")
                # id=2 is outside the predicate, so its update is inserted as a new row
                self.assertEqual([r[1] for r in rows], ["alpha", "beta", "beta-updated", "gamma", "delta"])


class TestDeleteInsert(IncrementalBase):
    def test_delete_insert(self):
        for catalog in self.catalogs(*ROW_LEVEL):
            with self.subTest(catalog=catalog):
                p = self.run_two_phases(catalog, incremental("delete+insert", ", unique_key='id'"))
                self.assertEqual([r[1] for r in p.rows("inc", "id")], ["alpha", "beta-updated", "gamma", "delta"])

    def test_delete_insert_composite_key(self):
        for catalog in self.catalogs(*ROW_LEVEL):
            with self.subTest(catalog=catalog):
                p = self.run_two_phases(catalog, incremental("delete+insert", ", unique_key=['id']"))
                self.assertEqual([r[0] for r in p.rows("inc", "id")], [1, 2, 3, 4])


class TestMicrobatch(TrinoTestCase):
    EVENTS = """
    id,event_ts,value
    1,2024-01-01 01:00:00,1
    2,2024-01-01 23:00:00,2
    3,2024-01-02 05:00:00,3
    4,2024-01-03 12:00:00,4
    """

    def test_microbatch_daily(self):
        for catalog in self.catalogs(*ROW_LEVEL):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, {
                    "seeds/events.csv": self.EVENTS,
                    "models/events_src.sql": """
                        {{ config(materialized='table', event_time='event_ts') }}
                        select id, cast(event_ts as timestamp(6)) as event_ts, value from {{ ref('events') }}
                    """,
                    "models/mb.sql": """
                        {{ config(materialized='incremental', incremental_strategy='microbatch',
                                  event_time='event_ts', batch_size='day', begin='2024-01-01',
                                  lookback=1) }}
                        select * from {{ ref('events_src') }}
                    """,
                }, "models:\n  +on_table_exists: replace\n" if catalog == "delta" else "")
                p.dbt("seed")
                p.dbt("run", "--event-time-start", "2024-01-01", "--event-time-end", "2024-01-04")
                self.assertEqual([r[0] for r in p.rows("mb", "id")], [1, 2, 3, 4])
                # rerun a single day: rows for that day are replaced, not duplicated
                p.dbt("run", "--select", "mb", "--event-time-start", "2024-01-02", "--event-time-end", "2024-01-03")
                self.assertEqual([r[0] for r in p.rows("mb", "id")], [1, 2, 3, 4])


class TestMicrobatchWeek(TrinoTestCase):
    def test_seven_daily_batches_rerun_idempotently(self):
        for catalog in self.catalogs("iceberg"):
            with self.subTest(catalog=catalog):
                days = [f"2024-01-{d:02d}" for d in range(1, 8)]
                rows = "\n".join(f"{i},{day} 12:00:00,{i}" for i, day in enumerate(days, 1))
                p = self.project(catalog, {
                    "seeds/events.csv": "id,event_ts,value\n" + rows + "\n",
                    "models/events_src.sql": """
                        {{ config(materialized='table', event_time='event_ts') }}
                        select id, cast(event_ts as timestamp(6)) as event_ts, value from {{ ref('events') }}
                    """,
                    "models/mb.sql": """
                        {{ config(materialized='incremental', incremental_strategy='microbatch',
                                  event_time='event_ts', batch_size='day', begin='2024-01-01',
                                  ) }}
                        select * from {{ ref('events_src') }}
                    """,
                })
                p.dbt("seed")
                p.dbt("run", "--select", "events_src")
                p.dbt("run", "--select", "mb", "--event-time-start", "2024-01-01", "--event-time-end", "2024-01-08")
                p.dbt("run", "--select", "mb", "--event-time-start", "2024-01-01", "--event-time-end", "2024-01-08")
                self.assertEqual([r[0] for r in p.rows("mb", "id")], list(range(1, 8)))


class TestOnSchemaChange(TrinoTestCase):
    V1 = "select 1 as id, 'a' as name"
    V2 = "select 2 as id, 'b' as name, 10 as extra"
    V3 = "select 3 as id, 20 as extra"

    def model(self, osc: str, select: str) -> str:
        return f"{{{{ config(materialized='incremental', on_schema_change='{osc}') }}}} {select}"

    @staticmethod
    def config_for(catalog: str) -> str:
        # Delta Lake drops and renames columns only with column mapping enabled.
        if catalog == "delta":
            return "models:\n  +properties:\n    column_mapping_mode: \"'name'\"\n"
        return ""

    def test_append_new_columns(self):
        for catalog in self.catalogs("memory", "hive", "iceberg", "delta"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, {"models/m.sql": self.model("append_new_columns", self.V1)})
                p.dbt("run")
                p.write("models/m.sql", self.model("append_new_columns", self.V2))
                p.dbt("run")
                self.assertEqual(p.rows("m", "id"), [[1, "a", None], [2, "b", 10]])

    def test_sync_all_columns(self):
        for catalog in self.catalogs("hive", "iceberg", "delta"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, {"models/m.sql": self.model("sync_all_columns", self.V1)},
                                 self.config_for(catalog))
                p.dbt("run")
                p.write("models/m.sql", self.model("sync_all_columns", self.V3))
                p.dbt("run")
                cols = [r[0] for r in p.query(
                    f"select column_name from {catalog}.information_schema.columns "
                    f"where table_schema = '{p.schema}' and table_name = 'm' order by ordinal_position")]
                self.assertEqual(cols, ["id", "extra"])

    def test_sync_all_columns_type_change(self):
        for catalog in self.catalogs("iceberg", "delta"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, {"models/m.sql": self.model("sync_all_columns", "select 1 as id, cast(1 as integer) as v")},
                                 self.config_for(catalog))
                p.dbt("run")
                p.write("models/m.sql", self.model("sync_all_columns", "select 2 as id, cast(2 as varchar) as v"))
                p.dbt("run")
                types = dict(p.query(
                    f"select column_name, data_type from {catalog}.information_schema.columns "
                    f"where table_schema = '{p.schema}' and table_name = 'm'"))
                self.assertEqual(types["v"], "varchar")
                self.assertEqual(p.rows("m", "id"), [[1, "1"], [2, "2"]])

    def test_fail(self):
        for catalog in self.catalogs("memory", "iceberg"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, {"models/m.sql": self.model("fail", self.V1)})
                p.dbt("run")
                p.write("models/m.sql", self.model("fail", self.V2))
                result = p.dbt("run", expect=False)
                self.assertIn("schema", result.output.lower())

    def test_ignore(self):
        for catalog in self.catalogs("memory", "iceberg"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, {"models/m.sql": self.model("ignore", self.V1)})
                p.dbt("run")
                p.write("models/m.sql", self.model("ignore", self.V2))
                p.dbt("run")
                self.assertEqual(p.rows("m", "id"), [[1, "a"], [2, "b"]])


class TestInsertOverwrite(TrinoTestCase):
    """v2 addition: Hive partition overwrite (dbt-trino v1 has no insert_overwrite)."""

    def model(self, select: str) -> str:
        return ("{{ config(materialized='incremental', incremental_strategy='insert_overwrite', "
                "properties={'partitioned_by': \"ARRAY['d']\"}) }} " + select)

    def test_overwrites_only_written_partitions_on_hive(self):
        for catalog in self.catalogs("hive"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, {"models/m.sql": self.model(
                    "select * from (values (1, 'a', '2024-01-01'), (2, 'b', '2024-01-02')) as t(id, v, d)")})
                p.dbt("run")
                p.write("models/m.sql", self.model(
                    "select * from (values (3, 'c', '2024-01-02'), (4, 'd', '2024-01-03')) as t(id, v, d)"))
                p.dbt("run")
                self.assertEqual(p.rows("m", "id"), [[1, "a", "2024-01-01"], [3, "c", "2024-01-02"],
                                                     [4, "d", "2024-01-03"]])
                # the session property does not leak into later statements
                p.dbt("run")
                self.assertEqual(len(p.rows("m")), 3)

    def test_non_hive_catalog_fails_clearly(self):
        for catalog in self.catalogs("iceberg"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, {"models/m.sql": self.model("select 1 as id, '2024-01-01' as d")
                                           .replace("properties={'partitioned_by': \"ARRAY['d']\"}", "")})
                p.dbt("run")
                result = p.dbt("run", expect=False)
                self.assertIn("requires a Hive connector catalog", result.output)


class TestSyncNestedColumns(TrinoTestCase):
    V1 = "select 1 as id, cast(row(1, 'a') as row(x integer, y varchar)) as payload"
    V2 = ("select 2 as id, cast(row(2, 'b', date '2024-01-01') "
          "as row(x bigint, y varchar, z date)) as payload")
    V3 = "select 3 as id, cast(row(3) as row(x bigint)) as payload"

    def model(self, osc: str, select: str) -> str:
        return (f"{{{{ config(materialized='incremental', on_schema_change='{osc}', "
                f"sync_nested_columns=true) }}}} {select}")

    def payload_type(self, p) -> str:
        return dict(p.query(
            f"select column_name, data_type from {p.catalog}.information_schema.columns "
            f"where table_schema = '{p.schema}' and table_name = 'm'"))["payload"]

    def test_append_new_nested_fields(self):
        for catalog in self.catalogs("iceberg"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, {"models/m.sql": self.model("append_new_columns", self.V1)})
                p.dbt("run")
                p.write("models/m.sql", self.model("append_new_columns", self.V2))
                p.dbt("run")
                self.assertIn("z date", self.payload_type(p).replace('"', ""))
                self.assertEqual(p.query(f"select id, payload.z from {p.relation('m')} order by id"),
                                 [[1, None], [2, "2024-01-01"]])

    def test_sync_all_nested_fields(self):
        for catalog in self.catalogs("iceberg"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, {"models/m.sql": self.model("sync_all_columns", self.V1)})
                p.dbt("run")
                p.write("models/m.sql", self.model("sync_all_columns", self.V3))
                p.dbt("run")
                self.assertEqual(self.payload_type(p).replace('"', ''), "row(x bigint)")
                self.assertEqual(p.query(f"select id, payload.x from {p.relation('m')} order by id"),
                                 [[1, 1], [3, 3]])


if __name__ == "__main__":
    unittest.main()
