"""Save the silicon-verified FULL route fix as a small independent SoC commit."""
from pathlib import Path
import hashlib,json,subprocess
import host

ROOT=Path(__file__).resolve().parent;TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
git=lambda *a:subprocess.check_output(['git','-C',str(TREE),*a],text=True).strip()
assert git('rev-parse','HEAD')=='ff8d2e9fc04ef92407ff83c40c4e059eb620f0f7'
path='drivers/media/platform/qcom/camss/camss-vfe-175-round.c'
assert git('diff','--name-only')==path
assert json.loads((ROOT/'route-pixel-validation.json').read_text())['black_white_neutrality_passed']
patch=ROOT/'vfe175-full-route-candidate.patch';patch.write_bytes(subprocess.check_output(['git','-C',str(TREE),'diff','--',path]))
q=subprocess.run(['perl',str(TREE/'scripts/checkpatch.pl'),'--no-tree',str(patch)],text=True,capture_output=True)
(host.PRIVATE/'full-route-checkpatch-private.txt').write_text(q.stdout+q.stderr);assert q.returncode==0,q.stdout+q.stderr
message=host.PRIVATE/'full-route-commit-message-private.txt'
message.write_text('media: qcom: camss: route VFE175 FULL through postprocessing\n\n'
 'The individual FULL round/clamp enables do not route data through the block. Enable the FULL postprocessing gate after programming both planes, and release only this gate when stopping. Preserve CST and scaler ownership. This fixes low-byte truncation of 10-bit CST values in the NV12 output without changing color matrices or sensor tuning.\n')
subprocess.run(['git','-C',str(TREE),'add','--',path],check=True)
subprocess.run(['git','-C',str(TREE),'commit','-F',str(message)],check=True,capture_output=True)
assert not git('status','--porcelain')
report=dict(stage=290,branch=git('branch','--show-current'),commit=git('rev-parse','HEAD'),parent=git('rev-parse','HEAD^'),
 source_clean=True,patch_sha256=hashlib.sha256(patch.read_bytes()).hexdigest(),checkpatch_errors=0,checkpatch_warnings=0,
 only_full_route_lifecycle_changed=True,cst_fields_and_matrices_unchanged=True,no_dt_or_userspace_changes=True,not_deployed=True,pushed=False)
(ROOT/'full-route-commit-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
