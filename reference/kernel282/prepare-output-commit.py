"""Save the exact tested output patch, including both new source files."""
from pathlib import Path
import json
import subprocess
import host

ROOT=Path(__file__).resolve().parent
TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
git=lambda *args:subprocess.check_output(['git','-C',str(TREE),*args],text=True)
assert git('rev-parse','HEAD').strip()=='2985ef200e4ae28d567f5919a4d8657ac0559b65'
assert not git('diff','--cached','--name-only')
paths=git('diff','--name-only').splitlines()+git('ls-files','--others','--exclude-standard').splitlines()
assert len(paths)==7 and all(p.startswith('drivers/media/platform/qcom/camss/') for p in paths)
git('diff','--check');git('add','--',*paths)
patch=ROOT/'vfe175-output-candidate.patch';patch.write_text(git('diff','--cached','--binary'))
run=subprocess.run(['perl',str(TREE/'scripts/checkpatch.pl'),'--no-tree',str(patch)],capture_output=True,text=True)
(host.PRIVATE/'output-checkpatch-private.log').write_text(run.stdout+run.stderr)
report=dict(stage=282,exit=run.returncode,stdout=run.stdout,stderr=run.stderr,
    new_files_covered_by_existing_camss_maintainers_pattern=True)
(ROOT/'output-checkpatch-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(run.stdout+run.stderr)
