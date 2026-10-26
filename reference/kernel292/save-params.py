"""Save independently reviewable common pad and VFE175 registration changes."""
from pathlib import Path
import hashlib,json,subprocess
import host
ROOT=Path(__file__).resolve().parent;TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
git=lambda *a:subprocess.check_output(['git','-C',str(TREE),*a],text=True).strip()
assert git('rev-parse','HEAD')=='15c8639d8badf5d4146bfd1b2c2fcb2460a137e5'
assert json.loads((ROOT/'pad-params-host-validation.json').read_text())['asan_ubsan']
assert json.loads((ROOT/'pad-parent-negative-validation.json').read_text())['expected_assertion_failure']
prefix='drivers/media/platform/qcom/camss/'
assert set(git('diff','--name-only').splitlines())=={prefix+'camss-vfe.c',prefix+'camss-vfe-17x.c'}
records=[]
for name,file,message in [
 ('pad-capabilities','camss-vfe.c','media: qcom: camss: reject formats on undeclared output pads\n\nKeep the shared pad indices for sparse PIX output sets, but gate TRY and ACTIVE formats and enumeration by the declared outputs. This prevents unsupported downscaler and metadata pads from advertising formats, and bounds format storage access. Sink and FULL remain available on existing lines.\n'),
 ('vfe175-params','camss-vfe-17x.c','media: qcom: camss: expose VFE175 white balance parameters\n\nRegister the existing typed parameters queue beside FULL on the SM8150 full IFE. Reuse common validation and frame-boundary parameter application, without assigning DMA write masters to the metadata output. Undeclared DS and statistics pads retain their shared indices but reject formats.\n')]:
 path=prefix+file;patch=ROOT/(name+'-candidate.patch');patch.write_bytes(subprocess.check_output(['git','-C',str(TREE),'diff','--',path]))
 q=subprocess.run(['perl',str(TREE/'scripts/checkpatch.pl'),'--no-tree',str(patch)],capture_output=True)
 (host.PRIVATE/(name+'-checkpatch-private.log')).write_bytes(q.stdout+q.stderr);assert q.returncode==0,(q.stdout+q.stderr).decode()
 text=host.PRIVATE/(name+'-commit-message-private.txt');text.write_text(message)
 subprocess.run(['git','-C',str(TREE),'add','--',path],check=True)
 subprocess.run(['git','-C',str(TREE),'commit','-F',str(text)],check=True,capture_output=True)
 records.append(dict(name=name,commit=git('rev-parse','HEAD'),patch_sha256=hashlib.sha256(patch.read_bytes()).hexdigest(),checkpatch_errors=0,checkpatch_warnings=0))
assert not git('status','--porcelain')
report=dict(stage=292,branch=git('branch','--show-current'),commit=git('rev-parse','HEAD'),commits=records,source_clean=True,not_deployed=True,pushed=False)
(ROOT/'params-commit-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
