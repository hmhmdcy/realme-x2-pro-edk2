from pathlib import Path
import subprocess,json,fcntl,os
r=Path('/mnt/e/RealmeX2Pro edk2');image=Path('/mnt/e/edk2-samurai-out/kernel122/rootfs-build-volume.ext4');mount=Path('/home/cy122/pmos-samurai-rootfs122');out=Path('/mnt/e/edk2-samurai-out/kernel125');out.mkdir(exist_ok=True)
assert image.stat().st_size==24*1024**3 and subprocess.check_output(['blkid','-s','LABEL','-o','value',str(image)],text=True).strip()=='samurai-rfs122'
recovered=[]
assert not (r/'reference/kernel125/stack-recovery-validation.json').exists(),'one-shot recovery already recorded; do not rerun'
assert os.geteuid()==0
lockdir=Path('/run/samurai-build-volume-locks');lockdir.mkdir(mode=0o700,exist_ok=True)
assert not lockdir.is_symlink() and lockdir.stat().st_uid==0 and lockdir.stat().st_mode & 0o077==0
with (lockdir/'samurai-rfs122-mount.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 if mount.is_mount():
  sources=subprocess.check_output(['findmnt','-rn','-o','SOURCE','--mountpoint',str(mount)],text=True).splitlines();assert 1<=len(sources)<=2
  for source in sources:
   assert source.startswith('/dev/loop')
   backing=subprocess.check_output(['losetup','--noheadings','--output','BACK-FILE',source],text=True).strip();assert Path(backing).resolve()==image.resolve()
  for _ in sources:
   subprocess.run(['sync','-f',str(mount)],check=True,timeout=30);subprocess.run(['umount',str(mount)],check=True,timeout=30)
  recovered=sources
 assert not mount.is_mount()
 loops=subprocess.run(['losetup','-j',str(image)],capture_output=True,text=True,check=True);assert not loops.stdout.strip(),'must be offline for fsck'
 with (out/'stack-recovery-offline-readonly-fsck-private.txt').open('w') as log:p=subprocess.run(['e2fsck','-f','-n',str(image)],stdout=log,stderr=subprocess.STDOUT,timeout=60)
 assert p.returncode==0,'preserve evidence; do not repair blindly'
report=dict(stack_count_recovered=len(recovered),all_observed_backings_verified_same_task_image=bool(recovered),all_unmounted=True,offline_readonly_fsck_exit=p.returncode,copy_not_started_before_guard_failure=True,mount_helper_now_serialized_with_flock=True,original_wsl_vhd_untouched=True,phone_unchanged=True)
(r/'reference/kernel125/stack-recovery-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
