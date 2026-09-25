"""Apply reviewed candidate source and run bounded offline Rust checks in Linux."""
import json
from pathlib import Path
import shutil
import sys
import tarfile
import uuid
sys.path.insert(0,'/opt/lab')
from archive_utils import safe_extract
from container import ROOT, REPORTS, run, digest

SOURCE=ROOT/'source/dbt-841c74e863df51b89d208b1ad0eca388aa0f32a4'
assert Path('/opt/lab/container.py').is_file()
if sys.argv[1] == 'apply':
    incoming=ROOT/('candidate-'+uuid.uuid4().hex)
    safe_extract(ROOT/'candidate.tar',incoming)
    with tarfile.open(ROOT/'candidate.tar') as archive:
        names=[m.name for m in archive.getmembers()]
    for name in names:
        assert name.startswith('crates/') and '..' not in Path(name).parts
        dest=SOURCE/name
        dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists() or dest.read_bytes() != (incoming/name).read_bytes():
            shutil.copyfile(incoming/name,dest)
    for name in json.loads((ROOT/'candidate-deleted.json').read_text()):
        assert name.startswith('crates/') and '..' not in Path(name).parts
        (SOURCE/name).unlink(missing_ok=True)
    run(['rustfmt','--edition','2024','--config','skip_children=true',*[str(SOURCE/n) for n in names if n.endswith('.rs')]],'candidate-format',timeout=120)
    with tarfile.open(ROOT/'candidate-formatted.tar','w:gz') as archive:
        for name in names:
            archive.add(SOURCE/name,arcname=name,recursive=False)
    shutil.rmtree(incoming)
elif sys.argv[1] == 'unit':
    run(['cargo','test','-p','dbt-auth','-p','dbt-adapter-sql','--lib','--frozen','-j','1'], 'candidate-auth-sql-tests',cwd=SOURCE)
elif sys.argv[1] == 'adapter':
    for test_filter in ['column::column_builder::tests','sql_types::tests','metadata::duckdb::tests']:
        run(['cargo','test','-p','dbt-adapter','--lib','--frozen','-j','1',test_filter], 'candidate-'+test_filter.replace('::','-'),cwd=SOURCE)
elif sys.argv[1] == 'macros':
    run(['cargo','test','-p','dbt-loader','--test','main','--frozen','-j','1'], 'candidate-macro-tests',cwd=SOURCE)
elif sys.argv[1] == 'build':
    run(['cargo','build','-p','dbt-sa-cli','--bin','dbt','--frozen','-j','1'],'candidate-build',cwd=SOURCE)
else:
    raise ValueError('Unknown check')
