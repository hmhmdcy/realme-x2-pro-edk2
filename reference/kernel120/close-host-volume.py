from pathlib import Path
import runpy,subprocess,json,shutil
runpy.run_path('/mnt/e/RealmeX2Pro edk2/reference/kernel118/ensure-build-volume.py')
mount=Path('/home/cy122/pmos-samurai-kernel118')
image=Path('/mnt/e/edk2-samurai-out/kernel118/build-volume.ext4')
out=Path('/mnt/e/edk2-samurai-out/kernel120')
subprocess.run(['sync','-f',str(mount)],check=True,timeout=30)
subprocess.run(['umount',str(mount)],check=True,timeout=30)
assert not mount.is_mount()
with (out/'offline-volume-readonly-fsck.txt').open('w') as log:
    p=subprocess.run(['e2fsck','-f','-n',str(image)],stdout=log,stderr=subprocess.STDOUT,timeout=60)
report=dict(private_e_volume_unmounted=True,offline_readonly_fsck_exit=p.returncode,only_new_e_build_volume_checked=True,original_wsl_vhd_not_checked=True,host_c_free_bytes=shutil.disk_usage('/mnt/c').free,host_e_free_bytes=shutil.disk_usage('/mnt/e').free,goal_complete=False)
Path('/mnt/e/RealmeX2Pro edk2/reference/kernel120/host-volume-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report));assert p.returncode==0
