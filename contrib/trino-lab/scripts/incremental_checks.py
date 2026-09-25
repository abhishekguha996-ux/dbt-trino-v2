"""Check append/merge updates, repeated runs, staging cleanup and full refresh."""
import json
import os
from pathlib import Path
import shutil
import sys
sys.path.insert(0,'/opt/lab')
from container import ROOT, REPORTS, run
from driver_smoke import check_network
check_network()
from adbc_driver_manager import dbapi
BINARY=ROOT/'source/dbt-841c74e863df51b89d208b1ad0eca388aa0f32a4/target/debug/dbt'
catalog=sys.argv[1]
assert catalog in ['memory','iceberg','delta']
project=ROOT/'runs'/catalog/'incremental'
if not project.exists():
    shutil.copytree(ROOT/'projects/incremental',project)
profile={'trino_lab':{'target':'lab','outputs':{'lab':{'type':'trino','host':'trino','port':8080,
         'user':'dbt_lab','threads':1,'http_scheme':'http','database':catalog,'schema':'dbt_lab_incremental'}}}}
(project/'profiles.yml').write_text(json.dumps(profile))
os.environ.update(DBT_ALLOW_EXPERIMENTAL_ADAPTERS='yes',LD_LIBRARY_PATH='/workspace/driver',DBT_SEND_ANONYMOUS_USAGE_STATS='false')
reports=[]
with dbapi.connect(driver='/workspace/driver/libadbc_driver_trino.so',db_kwargs={'uri':'http://dbt_lab@trino:8080'},autocommit=True) as conn:
    with conn.cursor() as cursor:
        for model in (['append_events'] if catalog == 'memory' else ['append_events','merge_events']):
            for stage,batch,full,expected in [
                ('initial',1,True,[(1,10),(2,20)]),
                ('update',2,False,[(1,10),(2,20 if model=='append_events' else 200),(3,30)]),
                ('repeat',2,False,[(1,10),(2,20 if model=='append_events' else 200),(3,30)]),
                ('refresh',2,True,[(2,200),(3,30)]),
            ]:
                cmd=[str(BINARY),'run','--project-dir',str(project),'--profiles-dir',str(project),
                     '--select',model,'--vars',json.dumps({'batch':batch})]
                if full:
                    cmd.append('--full-refresh')
                run(cmd,f'dbt-{catalog}-{model}-{stage}',timeout=300)
                cursor.execute(f'SELECT event_id,amount FROM {catalog}.dbt_lab_incremental.{model} ORDER BY event_id')
                rows=cursor.fetchall()
                assert rows==expected, (catalog,model,stage,rows,expected)
                cursor.execute(f"SELECT table_name FROM {catalog}.information_schema.tables WHERE table_schema='dbt_lab_incremental' AND table_name IN ('{model}__dbt_tmp', '{model}__dbt_backup')")
                assert cursor.fetchall()==[], 'Leftover dbt staging table'
                reports.append({'catalog':catalog,'model':model,'stage':stage,'status':'pass','rows':len(rows)})
(REPORTS/f'incremental-{catalog}.json').write_text(json.dumps(reports,indent=2)+'\n')
print(json.dumps(reports,indent=2))
