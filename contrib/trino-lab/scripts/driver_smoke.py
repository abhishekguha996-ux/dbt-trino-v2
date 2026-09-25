"""First Trino ADBC gate: exact results for joins, aggregates, types and ingestion.

This is a driver test, not evidence that the dbt adapter works. Run only in the
isolated Linux runner. All SQL writes use a fresh synthetic Memory schema.
"""

from decimal import Decimal
import json
from pathlib import Path
import socket
import uuid


FIXTURE = """WITH a(id, amount) AS (
    VALUES (1, 10), (2, 20), (2, 30), (CAST(NULL AS INTEGER), 40), (4, CAST(NULL AS INTEGER))
), b(id, units) AS (
    VALUES (2, 3), (2, 4), (3, 5), (CAST(NULL AS INTEGER), 6)
)
"""

CASES = [
    ("inner_duplicate_keys", "SELECT count(*), sum(amount), sum(units) FROM a INNER JOIN b ON a.id=b.id", [(4,100,14)]),
    ("left_unmatched_and_nulls", "SELECT count(*), sum(amount), sum(units) FROM a LEFT JOIN b ON a.id=b.id", [(7,150,14)]),
    ("right_unmatched_and_nulls", "SELECT count(*), sum(amount), sum(units) FROM a RIGHT JOIN b ON a.id=b.id", [(6,100,25)]),
    ("full_outer", "SELECT count(*), sum(amount), sum(units) FROM a FULL OUTER JOIN b ON a.id=b.id", [(9,150,25)]),
    ("bounded_cross", "SELECT count(*) FROM a CROSS JOIN b", [(20,)]),
    ("self_join", "SELECT count(*) FROM a x JOIN a y ON x.id=y.id", [(6,)]),
    ("non_equality_join", "SELECT count(*) FROM a JOIN b ON a.id < b.id", [(5,)]),
    ("exists", "SELECT count(*) FROM a WHERE EXISTS (SELECT 1 FROM b WHERE a.id=b.id)", [(2,)]),
    ("not_exists", "SELECT count(*) FROM a WHERE NOT EXISTS (SELECT 1 FROM b WHERE a.id=b.id)", [(3,)]),
    ("basic_aggregates", "SELECT count(*),count(amount),count(DISTINCT id),sum(amount),avg(amount),min(amount),max(amount) FROM a", [(5,4,3,100,25.0,10,40)]),
    ("having", "SELECT id,count(*),sum(amount) FROM a GROUP BY id HAVING count(*)>1", [(2,2,50)]),
    ("all_null", "SELECT sum(amount),avg(amount),count(amount) FROM a WHERE id=4", [(None,None,0)]),
    ("empty_input", "SELECT count(*),sum(amount),min(amount) FROM a WHERE false", [(0,None,None)]),
    ("conditional_and_filter", "SELECT sum(CASE WHEN id=2 THEN amount ELSE 0 END),sum(amount) FILTER (WHERE id=2),count(*) FILTER (WHERE amount IS NULL) FROM a", [(50,50,1)]),
    ("rollup", "SELECT id,grouping(id),sum(amount) FROM a GROUP BY ROLLUP(id) ORDER BY 2,1 NULLS LAST", [(1,0,10),(2,0,50),(4,0,None),(None,0,40),(None,1,100)]),
    ("grouping_sets", "SELECT id,grouping(id),sum(amount) FROM a GROUP BY GROUPING SETS ((id),()) ORDER BY 2,1 NULLS LAST", [(1,0,10),(2,0,50),(4,0,None),(None,0,40),(None,1,100)]),
    ("window_total", "SELECT amount,sum(amount) OVER (ORDER BY amount ROWS UNBOUNDED PRECEDING) FROM a WHERE amount IS NOT NULL ORDER BY amount", [(10,10),(20,30),(30,60),(40,100)]),
    ("decimal_exact", "SELECT sum(v),avg(v) FROM (VALUES DECIMAL '0.10', DECIMAL '0.20') t(v)", [(Decimal("0.30"),Decimal("0.15"))]),
]


def check_network():
    routes = Path("/proc/net/route").read_text().splitlines()[1:]
    if any(line.split()[1] == "00000000" for line in routes):
        raise RuntimeError("Runtime has an IPv4 default route")
    try:
        with socket.create_connection(("1.1.1.1",443),timeout=2):
            raise RuntimeError("Runtime can reach the public internet")
    except OSError:
        pass


def main():
    check_network()
    # Import native code only after the container network checks above.
    import pyarrow as pa
    from adbc_driver_manager import dbapi

    schema = "dbt_lab_" + uuid.uuid4().hex[:12]
    report = {"kind":"driver-only", "schema":schema, "cases":[],
              "not_yet_tested":["dbt integration", "TLS and auth", "cancellation", "timeout", "Iceberg", "Delta Lake"]}
    failures = []

    def check(name, operation):
        try:
            details = operation()
            report["cases"].append({"name":name,"status":"pass","details":details})
            print(f"PASS {name}", flush=True)
        except Exception as exc:
            failures.append(name)
            report["cases"].append({"name":name,"status":"fail","error":str(exc)})
            print(f"FAIL {name}: {exc}", flush=True)

    def assert_rows(cursor, sql, expected, parameters=None):
        cursor.execute(sql, parameters)
        rows = cursor.fetchall()
        if rows != expected:
            raise AssertionError(f"Expected {expected!r}, got {rows!r}")
        return {"rows":len(rows)}

    try:
        with dbapi.connect(driver="/workspace/driver/libadbc_driver_trino.so",
                           db_kwargs={"uri":"http://dbt_lab@trino:8080?catalog=memory"},
                           autocommit=True) as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"CREATE SCHEMA memory.{schema}")
                try:
                    for name, query, expected in CASES:
                        check(name, lambda q=query,e=expected: assert_rows(cursor,FIXTURE+q,e))
                    check("parameter_binding", lambda: assert_rows(cursor,
                        "SELECT CAST(? AS BIGINT)+CAST(? AS BIGINT)",[(42,)],(19,23)))
                    check("unicode", lambda: assert_rows(cursor,"SELECT 'café 東京'",[("café 東京",)]))

                    def ingest():
                        data = pa.table({"id":pa.array([1,2,3],type=pa.int64()),
                                         "amount":pa.array([10,None,30],type=pa.int64())})
                        cursor.adbc_ingest("synthetic", data, catalog_name="memory", db_schema_name=schema)
                        return assert_rows(cursor,f"SELECT id,amount FROM memory.{schema}.synthetic ORDER BY id",
                                           [(1,10),(2,None),(3,30)])
                    check("arrow_ingestion",ingest)

                    def metadata():
                        table_schema = conn.adbc_get_table_schema("synthetic", catalog_filter="memory",db_schema_filter=schema)
                        if table_schema.names != ["id","amount"]:
                            raise AssertionError(f"Unexpected columns: {table_schema}")
                        return str(table_schema)
                    check("table_schema",metadata)

                    def batches():
                        cursor.execute("SELECT n FROM UNNEST(sequence(1,10000)) t(n)")
                        with cursor.fetch_record_batch() as reader:
                            chunks = list(reader)
                        rows = sorted(row["n"] for batch in chunks for row in batch.to_pylist())
                        if rows != list(range(1,10001)):
                            raise AssertionError("Stream lost or duplicated rows")
                        return {"rows":len(rows),"batches_observed":len(chunks)}
                    check("record_batch_stream",batches)

                    def invalid_sql():
                        try:
                            cursor.execute("SELECT FROM intentionally_invalid_sql")
                        except dbapi.Error:
                            return assert_rows(cursor,"SELECT 1",[(1,)])
                        raise AssertionError("Invalid SQL unexpectedly succeeded")
                    check("error_and_reuse",invalid_sql)
                    check("tpch_tiny",lambda: assert_rows(cursor,"SELECT count(*) FROM tpch.tiny.customer",[(1500,)]))
                finally:
                    cursor.execute(f"DROP TABLE IF EXISTS memory.{schema}.synthetic")
                    cursor.execute(f"DROP SCHEMA memory.{schema}")
    finally:
        (Path("/workspace/reports")/"driver-capabilities.json").write_text(json.dumps(report,indent=2)+"\n")
    if failures:
        raise SystemExit(f"Driver gate failed: {', '.join(failures)}")


if __name__ == "__main__":
    main()
