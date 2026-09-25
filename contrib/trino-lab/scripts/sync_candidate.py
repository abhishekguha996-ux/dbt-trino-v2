"""Package only candidate files from the source checkout; never copy credentials."""
from pathlib import Path
import json
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parents[1]
BASE = json.loads((ROOT/'sources.lock.json').read_text())['dbt_commit']


def paths(*args):
    return subprocess.check_output(['git',*args],cwd=SOURCE).decode().splitlines()

changed = paths('diff',BASE,'--no-renames','--name-only','--diff-filter=ACMRT')
changed += paths('ls-files','--others','--exclude-standard')
deleted = paths('diff',BASE,'--no-renames','--name-only','--diff-filter=D')
changed=[name for name in changed if name.startswith('crates/')]
deleted=[name for name in deleted if name.startswith('crates/')]
for name in changed+deleted:
    assert name.startswith('crates/') and '..' not in Path(name).parts
with tarfile.open(ROOT/'reports/candidate.tar','w:gz') as archive:
    for name in sorted(set(changed)):
        assert (SOURCE/name).is_file() and not (SOURCE/name).is_symlink()
        archive.add(SOURCE/name,arcname=name,recursive=False)
(ROOT/'reports/candidate-deleted.json').write_text(json.dumps(deleted))
(ROOT/'reports/candidate.patch').write_bytes(subprocess.check_output(['git','diff',BASE,'--binary','--','crates'],cwd=SOURCE))
print(f'Packaged {len(set(changed))} files; {len(deleted)} removals')
