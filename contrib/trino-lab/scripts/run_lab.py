#!/usr/bin/env python3
"""Run the reviewed lab in separate acquisition, build, and test phases."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import uuid
from lab_control import ROOT, DOCKER, COMPOSE, review, stop
from verify_isolation import verify


def run(args, timeout=7500):
    subprocess.run(args,cwd=ROOT,check=True,timeout=timeout)


def guest(name,script,*args):
    python='/workspace/venv/bin/python'
    run(DOCKER+['exec',name,python,'/opt/lab/'+script,*args])


def copy_reports(name):
    run(DOCKER+['cp',name+':/workspace/reports/.',str(ROOT/'reports')])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=['prepare','build','test','stop'])
    phase=parser.parse_args().phase
    (ROOT/'reports').mkdir(exist_ok=True)
    if phase=='stop':
        stop();return
    review()
    active=subprocess.check_output(DOCKER+['ps','-q','--filter','label=org.dbt-trino-lab.owner=dbt-trino-lab'],text=True).strip()
    if active:
        raise SystemExit('Stop the current lab phase before starting another: python3 scripts/run_lab.py stop')
    name='dbt-trino-lab-'+phase+'-'+uuid.uuid4().hex[:8]
    if phase=='prepare':
        run([sys.executable,str(ROOT/'scripts/fetch_inputs.py')])
        run(COMPOSE+['build','prepare','trino'])
        run(COMPOSE+['run','--rm','--no-deps','--name',name,'prepare'],timeout=4000)
        return
    if phase=='build':
        run([sys.executable,str(ROOT/'scripts/sync_candidate.py')])
    else:
        run(COMPOSE+['up','-d','--wait','trino'],timeout=240)
    service='builder' if phase=='build' else 'runner'
    try:
        run(COMPOSE+['run','--rm','-d','--no-deps','--name',name,'--entrypoint','sleep',service,'7200'])
        checked=verify([name]+(['dbt-trino-lab-trino-1'] if phase=='test' else []))
        (ROOT/'reports'/('isolation-'+phase+'.json')).write_text(json.dumps(checked,indent=2)+'\n')
        if phase=='build':
            # The source is pristine until candidate_checks apply runs for the first time.
            baseline=subprocess.run(DOCKER+['exec',name,'test','-f','/workspace/reports/baseline-binary.json']).returncode
            if baseline:
                guest(name,'container.py','baseline')
            for filename in ['candidate.tar','candidate-deleted.json']:
                run(DOCKER+['cp',str(ROOT/'reports'/filename),name+':/workspace/'+filename])
            for action in ['apply','unit','adapter','macros','build']:
                guest(name,'candidate_checks.py',action)
        else:
            guest(name,'driver_smoke.py')
            for catalog in ['memory','iceberg']:
                guest(name,'runtime_checks.py','retail',catalog)
                guest(name,'runtime_checks.py','repeat',catalog,'retail')
                guest(name,'runtime_checks.py','catalog',catalog,'retail')
                guest(name,'incremental_checks.py',catalog)
            for catalog in ['memory','delta']:
                guest(name,'runtime_checks.py','tpch',catalog)
                guest(name,'runtime_checks.py','repeat',catalog,'tpch')
                guest(name,'runtime_checks.py','catalog',catalog,'tpch')
                guest(name,'tpch_oracle.py',catalog)
            guest(name,'tls_smoke.py')
            guest(name,'resilience_checks.py')
            guest(name,'persistence_checks.py','capture')
            run(COMPOSE+['stop','trino'],timeout=60)
            run(COMPOSE+['up','-d','--wait','trino'],timeout=240)
            guest(name,'persistence_checks.py','verify')
    finally:
        # Preserve failure reports too. Never remove data volumes or unrelated services.
        try:
            copy_reports(name)
        finally:
            stop()


if __name__=='__main__':
    main()
