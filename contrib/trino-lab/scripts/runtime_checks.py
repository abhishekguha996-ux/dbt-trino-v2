"""Bounded candidate CLI and result checks inside the isolated Linux runner."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
sys.path.insert(0,'/opt/lab')
from container import ROOT, REPORTS, run
from driver_smoke import check_network

SOURCE=ROOT/'source/dbt-841c74e863df51b89d208b1ad0eca388aa0f32a4'
BINARY=SOURCE/'target/debug/dbt'
check_network()
os.environ.update(DBT_ALLOW_EXPERIMENTAL_ADAPTERS='yes',
                  LD_LIBRARY_PATH='/workspace/driver',DBT_SEND_ANONYMOUS_USAGE_STATS='false')
command=sys.argv[1]
if command == 'help':
    for subcommand in ['debug','build','docs','show']:
        run([str(BINARY),subcommand,'--help'],'candidate-'+subcommand+'-help',timeout=60)
elif command in ['retail','tpch']:
    catalog=sys.argv[2] if len(sys.argv)>2 else 'memory'
    assert catalog in ['memory','iceberg','delta']
    original=ROOT/'projects'/command
    project=ROOT/'runs'/catalog/command
    if not project.exists():
        shutil.copytree(original,project)
    profile=json.loads((ROOT/'profile-template.json').read_text()) if (ROOT/'profile-template.json').exists() else {
        'trino_lab':{'target':'lab','outputs':{'lab':{'type':'trino','host':'trino','port':8080,
        'user':'dbt_lab','threads':1,'http_scheme':'http'}}}}
    profile['trino_lab']['outputs']['lab'].update(database=catalog,schema='dbt_lab_'+command)
    (project/'profiles.yml').write_text(json.dumps(profile))
    for action in ['debug','build']:
        run([str(BINARY),action,'--project-dir',str(project),'--profiles-dir',str(project)],
            f'dbt-{catalog}-{command}-{action}',timeout=300)
    results=json.loads((project/'target/run_results.json').read_text())
    assert results['results'], 'dbt produced no results'
    manifest=json.loads((project/'target/manifest.json').read_text())
    def ephemeral_noop(result):
        return (result['status']=='skipped' and
                manifest['nodes'].get(result['unique_id'],{}).get('config',{}).get('materialized')=='ephemeral')
    failures=[r for r in results['results'] if r['status'] not in ['success','pass'] and not ephemeral_noop(r)]
    assert not failures, [(r['unique_id'],r['status']) for r in failures]
    (REPORTS/f'dbt-{catalog}-{command}-summary.json').write_text(json.dumps({
        'status':'pass','count':sum(r['status'] in ['success','pass'] for r in results['results']),
        'ephemeral_noops':sum(ephemeral_noop(r) for r in results['results']),
        'results':[{'node':r['unique_id'],'status':r['status']} for r in results['results']],
    },indent=2)+'\n')
elif command == 'repeat':
    project=ROOT/'runs'/sys.argv[2]/sys.argv[3]
    run([str(BINARY),'build','--project-dir',str(project),'--profiles-dir',str(project)],
        f'dbt-{sys.argv[2]}-{sys.argv[3]}-repeat',timeout=300)
elif command in ['docs','catalog']:
    project=ROOT/'runs'/sys.argv[2]/sys.argv[3]
    args=['docs','generate'] if command == 'docs' else ['compile','--write-catalog']
    run([str(BINARY),*args,'--project-dir',str(project),'--profiles-dir',str(project)],
        f'dbt-{sys.argv[2]}-{sys.argv[3]}-{command}',timeout=300)
else:
    raise ValueError('Unknown runtime check')
