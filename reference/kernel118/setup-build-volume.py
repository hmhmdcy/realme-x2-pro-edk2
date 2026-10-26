from pathlib import Path
import os,shutil,subprocess,json
out=Path('/mnt/e/edk2-samurai-out/kernel118')
image=out/'build-volume.ext4'
mount=Path('/home/cy122/pmos-samurai-kernel118')
assert not image.exists() and not mount.exists()
assert shutil.disk_usage('/mnt/e').free>35*1024**3
assert shutil.disk_usage('/mnt/c').free>1024**3
with image.open('xb') as f: f.truncate(20*1024**3)
os.chmod(image,0o600)
mkfs=subprocess.run(['mkfs.ext4','-F','-m','0','-L','samurai-k118',str(image)],check=True,capture_output=True)
(out/'build-volume-mkfs-private.txt').write_bytes(mkfs.stdout+mkfs.stderr)
mount.mkdir()
subprocess.run(['mount','-o','loop',str(image),str(mount)],check=True)
assert mount.is_mount()
(out/'build-volume-mount-private.txt').write_bytes(subprocess.check_output(['findmnt','-n','-o','SOURCE,TARGET,OPTIONS',str(mount)]))
report=dict(private_e_drive_ext4_build_volume_gib=20,created_new_file_only=True,phone_partitions_not_touched=True,c_drive_avoided_for_new_kernel_clone=True,goal_complete=False)
(out/'build-volume-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
