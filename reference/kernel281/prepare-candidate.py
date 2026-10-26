"""Save and check the exact source patch, including newly added CAMIF files."""
from pathlib import Path
import json
import subprocess

ROOT = Path(__file__).resolve().parent
TREE = Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel281')
git = lambda *args: subprocess.check_output(['git', '-C', str(TREE), *args], text=True)
assert git('rev-parse', 'HEAD').strip() == '7f81d76ee7e05c1713ca87b59fc31df806ae0295'
assert git('branch', '--show-current').strip() == 'samurai-vfe175-281'
assert not git('diff', '--cached', '--name-only')
paths = git('diff', '--name-only').splitlines() + git('ls-files', '--others', '--exclude-standard').splitlines()
assert len(paths) == 8 and all(p.startswith('drivers/media/platform/qcom/camss/') for p in paths)
assert len([p for p in paths if '175-camif' in p]) == 2
git('diff', '--check')
git('add', '--', *paths)
patch = ROOT / 'vfe175-camif-candidate.patch'
patch.write_text(git('diff', '--cached', '--binary'))
run = subprocess.run(['perl', str(TREE / 'scripts/checkpatch.pl'), '--no-tree', str(patch)], capture_output=True, text=True)
(PRIVATE / 'camif-checkpatch-private.log').write_text(run.stdout + run.stderr)
report = dict(stage=281, exit=run.returncode, stdout=run.stdout, stderr=run.stderr)
(ROOT / 'camif-checkpatch-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(run.stdout + run.stderr)
