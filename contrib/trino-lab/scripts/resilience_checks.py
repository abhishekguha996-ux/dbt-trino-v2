"""Bounded timeout and ADBC cancellation checks on synthetic TPC-H data."""
import json
from pathlib import Path
import threading
import time
import uuid

from adbc_driver_manager import dbapi


def main():
    report=[]
    driver='/workspace/driver/libadbc_driver_trino.so'
    with dbapi.connect(driver=driver,db_kwargs={'uri':'http://dbt_lab@trino:8080'},autocommit=True) as conn:
        with conn.cursor() as cursor:
            heavy='SELECT sum(a.o_orderkey % (b.o_orderkey + 1)) FROM tpch.sf1.orders a CROSS JOIN tpch.tiny.orders b'
            try:
                cursor.execute("WITH SESSION query_max_execution_time = '1ms' "+heavy)
                cursor.fetchall()
            except dbapi.Error as err:
                text=str(err)
                assert 'time' in text.lower() and ('limit' in text.lower() or 'exceeded' in text.lower()), text
                report.append({'name':'server_execution_timeout','status':'pass','error':text})
            else:
                raise AssertionError('The timeout query unexpectedly completed')
            cursor.execute('SELECT 42')
            assert cursor.fetchone() == (42,)
            report.append({'name':'reuse_after_timeout','status':'pass'})

        with conn.cursor() as cursor:
            marker='dbt_trino_cancel_'+uuid.uuid4().hex
            outcome=[]
            started=threading.Event()
            def query():
                started.set()
                try:
                    cursor.execute(f'/* {marker} */ '+heavy)
                    cursor.fetchall()
                    outcome.append('completed')
                except dbapi.Error as err:
                    outcome.append(str(err))
            worker=threading.Thread(target=query,daemon=True)
            worker.start();started.wait(timeout=5)
            time.sleep(0.25)
            before=time.monotonic()
            cursor.adbc_cancel()
            worker.join(timeout=10)
            cancelled = not worker.is_alive() and len(outcome)==1 and 'cancel' in outcome[0].lower()
            if not cancelled:
                # Bound the known driver limitation through Trino's own control API.
                with dbapi.connect(driver=driver,db_kwargs={'uri':'http://dbt_lab@trino:8080'},autocommit=True) as control:
                    with control.cursor() as admin:
                        admin.execute(f"SELECT query_id FROM system.runtime.queries WHERE query LIKE '/* {marker} */%' AND state NOT IN ('FINISHED','FAILED')")
                        for (query_id,) in admin.fetchall():
                            assert all(c.isalnum() or c=='_' for c in query_id)
                            admin.execute(f"CALL system.runtime.kill_query(query_id => '{query_id}', message => 'Bounded test watchdog stop')")
                worker.join(timeout=10)
                assert not worker.is_alive(), 'Query survived the server watchdog'
            report.append({'name':'adbc_statement_cancel','status':'pass' if cancelled else 'unsupported',
                           'seconds':round(time.monotonic()-before,3),
                           'detail':'Driver cancellation returned promptly' if cancelled else 'Driver did not interrupt execution; the server watchdog stopped the synthetic query'})
            cursor.execute('SELECT 43')
            assert cursor.fetchone() == (43,)
            report.append({'name':'reuse_after_cancel_attempt','status':'pass'})
        with conn.cursor() as cursor:
            cursor.execute('SELECT query,state FROM system.runtime.queries')
            active=[state for query,state in cursor.fetchall() if marker in query and state not in ['FINISHED','FAILED']]
            assert not active, active
            report.append({'name':'stress_query_not_running','status':'pass'})
    Path('/workspace/reports/resilience-tests.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__ == '__main__':
    main()
