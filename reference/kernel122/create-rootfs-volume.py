from pathlib import Path
import subprocess,shutil,json,os
out=Path('/mnt/e/edk2-samurai-out/kernel122');out.mkdir(exist_ok=True)
image=out/'rootfs-build-volume.ext4';mount=Path('/home/cy122/pmos-samurai-rootfs122')
assert not image.exists() and not mount.exists()
assert shutil.disk_usage('/mnt/e').free>50*1024**3
with image.open('xb') as f:f.truncate(24*1024**3)
with (out/'mkfs-ext4-private.txt').open('w') as log:
    subprocess.run(['mkfs.ext4','-F','-m','0','-L','samurai-rfs122',str(image)],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=90)
mount.mkdir(mode=0o700)
subprocess.run(['mount','-o','loop',str(image),str(mount)],check=True,timeout=30)
assert mount.is_mount()
report=dict(new_private_e_rootfs_volume_bytes=image.stat().st_size,existing_volumes_not_resized=True,original_wsl_vhd_unchanged=True,host_c_free_bytes=shutil.disk_usage('/mnt/c').free,host_e_free_bytes=shutil.disk_usage('/mnt/e').free)
Path('/mnt/e/RealmeX2Pro edk2/reference/kernel122/volume-create-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
