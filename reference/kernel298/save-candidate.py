"""Save the tested public black-offset mapping as an independent candidate."""
from pathlib import Path
import json, subprocess
import host
HERE=Path(__file__).resolve().parent
TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
git=lambda *a:subprocess.check_output(['git','-C',str(TREE),*a],text=True).strip()
for tag in ['parent','fixed']:
 assert json.loads((HERE/f'blc-{tag}-host-validation.json').read_text())['expected_outcome_observed']
assert git('branch','--show-current')=='samurai-blc298'
assert git('rev-parse','HEAD')=='ab709d9670f6dcaa71858fd4f3e189522f669913'
patch=subprocess.check_output(['git','-C',str(TREE),'diff'])
q=subprocess.run([str(TREE/'scripts/checkpatch.pl'),'--no-tree','--strict','-'],input=patch,capture_output=True)
(host.PRIVATE/'candidate-checkpatch-private.log').write_bytes(q.stdout+q.stderr)
assert q.returncode==0,q.stdout.decode()
names=['drivers/media/platform/qcom/camss/'+n for n in ['camss-vfe-175-pixel.c','camss-vfe-175-pixel.h']]
assert set(git('diff','--name-only').splitlines())==set(names)
subprocess.run(['git','-C',str(TREE),'add',*names],check=True)
subprocess.run(['git','-C',str(TREE),'commit','-m','media: qcom: camss: map common black subtraction to VFE175 BLS'],check=True)
assert not git('status','--porcelain')
report=dict(stage=298,branch=git('branch','--show-current'),commit=git('rev-parse','HEAD'),parent='ab709d9670f6dcaa71858fd4f3e189522f669913',
 source_clean=True,checkpatch_errors=0,checkpatch_warnings=0,pushed=False,not_deployed=True,
 scope='Common equal WB subtraction maps U16 to U14 BLS at Q11 unity; reject unequal subtraction and additive offsets; bypass/cache/stop/reopen lifecycle; no board, firmware or UAPI change',
 physical_validation_pending=True)
(HERE/'source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
(HERE/'blc-candidate.patch').write_bytes(patch)
for name in names:(HERE/Path(name).name).write_bytes((TREE/name).read_bytes())
print(json.dumps(report,indent=2))
