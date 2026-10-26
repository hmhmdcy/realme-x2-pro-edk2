"""Save the tested shared-SOF change as an independent, undeployed candidate."""
from pathlib import Path
import json, subprocess
import host
HERE=Path(__file__).resolve().parent
TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
git=lambda *a:subprocess.check_output(['git','-C',str(TREE),*a],text=True).strip()
for tag in ['parent','fixed']:
 assert json.loads((HERE/f'sof-{tag}-host-validation.json').read_text())['expected_outcome_observed']
assert git('branch','--show-current')=='samurai-sof297'
assert git('rev-parse','HEAD')=='f86906688666c0ebaabaeeec96c28d5741257f50'
patch=subprocess.check_output(['git','-C',str(TREE),'diff'])
q=subprocess.run([str(TREE/'scripts/checkpatch.pl'),'--no-tree','--strict','-'],input=patch,capture_output=True)
(host.PRIVATE/'candidate-checkpatch-private.log').write_bytes(q.stdout+q.stderr)
assert q.returncode==0,q.stdout.decode()
names=['drivers/media/platform/qcom/camss/'+n for n in ['camss-vfe.c','camss-vfe-17x.c']]
assert set(git('diff','--name-only').splitlines())==set(names)
subprocess.run(['git','-C',str(TREE),'add',*names],check=True)
subprocess.run(['git','-C',str(TREE),'commit','-m','media: qcom: camss: retain shared SOF identities for VFE175 PIX outputs'],check=True)
assert not git('status','--porcelain')
report=dict(stage=297,branch=git('branch','--show-current'),commit=git('rev-parse','HEAD'),parent='f86906688666c0ebaabaeeec96c28d5741257f50',
 source_clean=True,checkpatch_errors=0,checkpatch_warnings=0,pushed=False,not_deployed=True,
 scope='Existing CAMIF SOF tags shared by image/statistics; missing tags ERROR; future parameter sequence uses SOF; no board, firmware or UAPI change',
 physical_validation_pending=True,multi_unobserved_sof_coalescence_not_proven=True)
(HERE/'source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
(HERE/'sof-candidate.patch').write_bytes(patch)
for name in names:(HERE/Path(name).name).write_bytes((TREE/name).read_bytes())
print(json.dumps(report,indent=2))
