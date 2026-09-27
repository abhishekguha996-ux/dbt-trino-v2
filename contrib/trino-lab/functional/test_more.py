"""Remaining dbt behaviors: query comments, custom schemas, store_failures, snapshot
hard deletes, session limits, packages, unsupported configs and cancellation.

Modeled on dbt-trino v1 test_query_comments.py, test_custom_schema.py, store_failures,
test_simple_snapshot.py and test_session_property.py.
"""

import os
import signal
import subprocess
import time
import unittest

from harness import DBT_BIN, TrinoTestCase, run_sql


class TestQueryComments(TrinoTestCase):
    def test_default_and_custom_query_comment(self):
        for catalog in self.catalogs("memory"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, {"models/qc_marker_5501.sql": "select 1 as id"},
                                 "query-comment:\n  comment: 'dbt-trino-qc {{ node.name if node else \"\" }}'\n  append: true\n")
                p.dbt("run")
                rows = run_sql("select query from system.runtime.queries "
                               "where query like '%qc_marker_5501%' and query like '%dbt-trino-qc%' "
                               "and query not like '%system.runtime%'")
                self.assertTrue(rows, "query comment not found")
                self.assertTrue(rows[0][0].rstrip().endswith("*/"), rows[0][0])


class TestCustomSchema(TrinoTestCase):
    def test_schema_config_creates_schema(self):
        for catalog in self.catalogs("memory", "iceberg", "hive", "delta"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, {"models/m.sql": "{{ config(schema='custom') }} select 1 as id"})
                p.dbt("run")
                self.assertEqual(run_sql(f'select * from {catalog}."{p.schema}_custom".m'), [[1]])


class TestStoreFailures(TrinoTestCase):
    def test_failures_stored_in_audit_schema(self):
        for catalog in self.catalogs("memory", "iceberg"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, {
                    "models/m.sql": "select * from (values 1, 1, 2) as t(id)",
                    "models/schema.yml": """
                        version: 2
                        models:
                          - name: m
                            columns:
                              - name: id
                                data_tests: [unique]
                    """,
                })
                p.dbt("run")
                result = p.dbt("test", "--store-failures", expect=False)
                self.assertIn(result.status("unique_m_id"), ("fail", "error"))
                self.addCleanup(lambda c=catalog, s=p.schema: __import__("harness").drop_schema(c, s + "_dbt_test__audit"))
                stored = run_sql(f'select * from {catalog}."{p.schema}_dbt_test__audit".unique_m_id')
                self.assertEqual(len(stored), 1)


class TestSnapshotNewRecord(TrinoTestCase):
    def test_hard_deletes_new_record(self):
        for catalog in self.catalogs("iceberg"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, {
                    "seeds/src.csv": "id,v,updated_at\n1,a,2024-01-01 00:00:00\n2,b,2024-01-01 00:00:00\n",
                    "snapshots/snap.yml": """
                        snapshots:
                          - name: snap
                            relation: ref('src')
                            config:
                              unique_key: id
                              strategy: timestamp
                              updated_at: updated_at
                              hard_deletes: new_record
                    """,
                })
                p.dbt("seed")
                p.dbt("snapshot")
                p.write("seeds/src.csv", "id,v,updated_at\n1,a,2024-01-01 00:00:00\n")
                p.dbt("seed", "--full-refresh")
                p.dbt("snapshot")
                rows = p.query(f"select id, dbt_is_deleted from {p.relation('snap')} order by id, dbt_valid_from")
                self.assertEqual(rows, [[1, "False"], [2, "False"], [2, "True"]])


class TestSessionLimits(TrinoTestCase):
    SLOW = "select count(*) as n from tpch.sf1.lineitem a cross join tpch.sf1.lineitem b"

    def test_profile_session_property_is_enforced(self):
        for catalog in self.catalogs("memory"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, {"models/slow.sql": "{{ config(materialized='table') }} " + self.SLOW},
                                 profile_overrides={"session_properties": {"query_max_run_time": "2s"}})
                start = time.time()
                result = p.dbt("run", expect=False)
                self.assertLess(time.time() - start, 60)
                self.assertRegex(result.output, r"(?i)exceeded|maximum run time|query_max_run_time")

    # Known driver limitation (adbc-drivers/trino go/v0.5.3): AdbcStatementCancel only cancels a
    # call that is still executing, and the query is polled while dbt reads the result stream,
    # after ExecuteQuery returned. Trino then abandons the query after query.client.timeout
    # (5m by default). Remove expectedFailure once the driver propagates cancellation.
    @unittest.expectedFailure
    def test_ctrl_c_stops_server_query(self):
        for catalog in self.catalogs("memory"):
            with self.subTest(catalog=catalog):
                marker = "cancel_marker_9313"
                p = self.project(catalog, {"models/slow.sql": "{{ config(materialized='table') }} "
                                           f"select '{marker}' as m, n from ({self.SLOW})"},
                                 profile_overrides={"session_properties": {"query_max_run_time": "3m"}})
                env = {**os.environ, "DBT_ALLOW_EXPERIMENTAL_ADAPTERS": "yes"}
                proc = subprocess.Popen([str(DBT_BIN), "run", "--project-dir", str(p.dir), "--profiles-dir", str(p.dir)],
                                        cwd=p.dir, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                running = []
                for _ in range(60):
                    running = run_sql(f"select query_id from system.runtime.queries where state = 'RUNNING' "
                                      f"and query like '%{marker}%' and query not like '%system.runtime%'")
                    if running:
                        break
                    time.sleep(1)
                self.assertTrue(running, "slow query never started")
                proc.send_signal(signal.SIGINT)
                proc.wait(timeout=60)
                state = None
                for _ in range(30):
                    state = run_sql(f"select state from system.runtime.queries where query_id = '{running[0][0]}'")[0][0]
                    if state != "RUNNING":
                        break
                    time.sleep(1)
                if state == "RUNNING":
                    run_sql(f"call system.runtime.kill_query(query_id => '{running[0][0]}', message => 'test cleanup')")
                self.assertNotEqual(state, "RUNNING", "query kept running on the server after Ctrl-C")


class TestPackagesAndUnsupported(TrinoTestCase):
    def test_dbt_utils(self):
        for catalog in self.catalogs("memory"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, {
                    "packages.yml": "packages:\n  - package: dbt-labs/dbt_utils\n    version: [\">=1.3.0\", \"<2.0.0\"]\n",
                    "models/base.sql": "select * from (values (1, 'a', 10), (2, 'b', 20)) as t(id, name, amount)",
                    "models/u.sql": """
                        select {{ dbt_utils.generate_surrogate_key(['id', 'name']) }} as sk,
                               {{ dbt_utils.star(ref('base'), except=['amount']) }}
                        from {{ ref('base') }}
                    """,
                    "models/schema.yml": """
                        version: 2
                        models:
                          - name: u
                            data_tests:
                              - dbt_utils.unique_combination_of_columns:
                                  arguments:
                                    combination_of_columns: [id, name]
                    """,
                })
                p.dbt("deps")
                p.dbt("build")
                self.assertEqual(len(p.rows("u")), 2)

    def test_catalog_integration_not_supported_yet(self):
        for catalog in self.catalogs("iceberg"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, {"models/m.sql": "{{ config(materialized='table', catalog_name='lake') }} select 1 as id"})
                result = p.dbt("run", expect=False)
                self.assertRegex(result.output.lower(), r"catalog")
                self.assertNotIn("panicked", result.output)

    def test_python_models_rejected(self):
        for catalog in self.catalogs("memory"):
            with self.subTest(catalog=catalog):
                p = self.project(catalog, {"models/py.py": "def model(dbt, session):\n    return None\n"})
                result = p.dbt("run", expect=False)
                self.assertNotIn("panicked", result.output)


if __name__ == "__main__":
    unittest.main()
