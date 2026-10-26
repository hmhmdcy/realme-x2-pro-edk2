from pathlib import Path
import subprocess,json
image=Path('/mnt/e/edk2-samurai-out/kernel126/build-volume.ext4');out=Path('/mnt/e/edk2-samurai-out/kernel127');out.mkdir(mode=0o700,exist_ok=True)
assert not subprocess.check_output(['losetup','-j',str(image)],text=True).strip()
with (out/'volume-readonly-check-private.log').open('w') as log:
 p=subprocess.run(['e2fsck','-fn',str(image)],stdout=log,stderr=subprocess.STDOUT,timeout=120)
report=dict(volume_readonly_fsck_exit=p.returncode,no_existing_loop_mount=True,no_phone_changes=True)
(out/'volume-readonly-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
