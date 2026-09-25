"""Check that Iceberg and Delta table data survives a Trino restart."""
import json
from pathlib import Path
import sys
from adbc_driver_manager import dbapi

QUERIES={
    'iceberg_orders':'select count(*),sum(net_cents) from iceberg.dbt_lab_retail.fct_orders',
    'delta_revenue':'select count(*),sum(revenue) from delta.dbt_lab_tpch.shipping_revenue',
}
with dbapi.connect(driver='/workspace/driver/libadbc_driver_trino.so',
                  db_kwargs={'uri':'http://dbt_lab@trino:8080'},autocommit=True) as conn:
    with conn.cursor() as cursor:
        result={}
        for name,sql in QUERIES.items():
            cursor.execute(sql)
            result[name]=[str(value) for value in cursor.fetchone()]
path=Path('/workspace/reports/persistence-before.json')
if sys.argv[1]=='capture':
    assert result['iceberg_orders'][0]=='200' and result['delta_revenue'][0]=='138',result
    path.write_text(json.dumps(result,indent=2)+'\n')
elif sys.argv[1]=='verify':
    assert result==json.loads(path.read_text()),result
    Path('/workspace/reports/persistence-tests.json').write_text(json.dumps({'status':'pass','tables':result},indent=2)+'\n')
    print('Iceberg and Delta counts and totals survived the Trino restart.')
else:
    raise ValueError('Use capture or verify')
