from pathlib import Path
import subprocess,json
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel118')
out=Path('/mnt/e/edk2-samurai-out/kernel118')
subprocess.run(['python3',str(ref/'ensure-build-volume.py')],check=True)
subprocess.run(['umount','/home/cy122/pmos-samurai-kernel118'],check=True)
check=subprocess.run(['e2fsck','-f','-n',str(out/'build-volume.ext4')],capture_output=True)
(out/'build-volume-fsck-private.txt').write_bytes(check.stdout+check.stderr)
assert check.returncode==0
report=dict(candidate=118,e_drive_volume_cleanly_unmounted=True,offline_readonly_fsck_pass=True,private_e_drive_file_only=True,original_wsl_root_fsck_not_performed=True,ensure_mount_required_before_next_build=True,goal_complete=False)
(ref/'build-volume-close-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
