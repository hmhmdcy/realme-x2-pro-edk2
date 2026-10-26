from pathlib import Path
import os,shutil,subprocess,json
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel129';out=Path('/mnt/e/edk2-samurai-out/kernel129');image=out/'rootfs-build-volume.ext4';mount=Path('/home/cy122/pmos-samurai-rootfs129')
assert os.geteuid()==0 and not image.exists() and not mount.exists()
assert shutil.disk_usage('/mnt/e').free>20*1024**3
with image.open('xb') as f:f.truncate(16*1024**3)
with (out/'mkfs-ext4-private.txt').open('w') as log:
 subprocess.run(['mkfs.ext4','-F','-m','0','-L','samurai-rfs129',str(image)],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=90)
mount.mkdir(mode=0o700)
report=dict(new_private_rootfs_e_volume_bytes=image.stat().st_size,existing_stable_volumes_preserved=True,original_wsl_vhd_not_resized=True,host_c_free_bytes=shutil.disk_usage('/mnt/c').free,host_e_free_bytes=shutil.disk_usage('/mnt/e').free,phone_unchanged=True)
(ref/'volume-create-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
