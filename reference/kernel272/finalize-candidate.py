"""Commit and lock only the tested offline candidate, without promoting deployment."""
from pathlib import Path
import hashlib,json,subprocess
R=Path(__file__).resolve().parent;W=Path('/home/cy122/x2pro-linux/camera270-kernel')
names=['Documentation/devicetree/bindings/media/i2c/samsung,s5kgw1.yaml',
 'arch/arm64/boot/dts/qcom/s5kgw1-samurai.dtsi','arch/arm64/boot/dts/qcom/sm8150-samurai.dts',
 'drivers/media/i2c/Kconfig','drivers/media/i2c/Makefile','drivers/media/i2c/s5kgw1.c','drivers/media/i2c/s5kgw1-tables.h']
status=subprocess.check_output(['git','status','--porcelain=v1','-z'],cwd=W).decode().split('\0')
assert {s[3:] for s in status if s}==set(names),status
hash=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name in ['s5kgw1.c','s5kgw1-tables.h']:
 assert (R/name).read_bytes()==(W/'drivers/media/i2c'/name).read_bytes()
driver_hash=hash(R/'s5kgw1.c')
for name in ['current-module-build-validation.json','table-writer-test-validation.json','power-sequence-test-validation.json','control-test-validation.json']:
 assert json.loads((R/name).read_text())['source_sha256']==driver_hash,name
board=json.loads((R/'board-validation.json').read_text())
assert board['dtb_sha256']==json.loads((R/'driver-build-validation.json').read_text())['dtb_sha256']
assert json.loads((R/'input-revalidation.json').read_text())['source_and_retained_xml_freshly_rechecked']
assert json.loads((R/'current-idle-validation.json').read_text())['passed']
helper=json.loads((R/'helper-candidate-validation.json').read_text())
assert helper['results']['candidate']['exit']==0 and helper['results']['negative-r20']['exit']==3
subprocess.run(['git','add','--',*names],cwd=W,check=True)
subprocess.run(['git','diff','--cached','--check'],cwd=W,check=True)
patch=subprocess.check_output(['git','diff','--cached','--binary'],cwd=W)
(R/'s5kgw1-candidate.patch').write_bytes(patch)
q=subprocess.run(['perl',str(W/'scripts/checkpatch.pl'),'--no-tree','--terse','--no-signoff',str(R/'s5kgw1-candidate.patch')],capture_output=True)
Path('/mnt/e/edk2-samurai-out/kernel272/checkpatch-private.log').write_bytes(q.stdout+q.stderr)
# Retain the style review separately; compilation/schema/fault tests are distinct gates.
review=dict(exit=q.returncode,errors=sum(b': ERROR:' in line for line in q.stdout.splitlines()),
 warnings=sum(b': WARNING:' in line for line in q.stdout.splitlines()))
if review['errors']:raise RuntimeError('Inspect checkpatch errors before committing')
message='''media: i2c: add S5KGW1 C-PHY candidate and samurai wiring

Use the handset OEM 19.2 MHz initialization and two complete RAW10 modes.
Preserve mixed-width writes and split indirect RAM transfers at whole-word
boundaries within the I2C adapter limit. Track power references through
failed resume/suspend and expose native gain codes and frame controls.

Add static board19781 supplies, PM8150 reset, MCLK0 and C-PHY endpoints.
The stock Android probe identifies address 0x10 and chip ID 0x0971.

Candidate only: W=1, focused DT schemas, table/control/power host fault
tests pass. Physical probe, link/VT timing, RAW/AE/colour, AF and other
modes are not verified. Existing boot270/Image183 deployment is unchanged.
'''
subprocess.run(['git','commit','-F','-'],cwd=W,input=message.encode(),check=True,capture_output=True)
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=W,text=True).strip()
assert not subprocess.check_output(['git','status','--porcelain'],cwd=W)
report=dict(stage=272,branch='samurai-main-camera272',commit=commit,parent='ac7ccc2da924b44aa6dff5d1be24356253890ee8',
 source_files_sha256={n:hash(W/n) for n in names},candidate_patch_sha256=hash(R/'s5kgw1-candidate.patch'),checkpatch=review,
 deployment_stage=271,boot_stage=270,image_build=183,phone_unchanged=True,not_pushed=True,
 native_probe_and_capture_pending=True,physical_timing_pending=True,af_and_more_modes_pending=True,
 spectra_image_processing_supported=False,goal_status='active_incomplete')
(R/'source-lock.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
