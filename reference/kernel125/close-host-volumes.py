from pathlib import Path
import subprocess,runpy,json,shutil,fcntl,os
root=Path('/mnt/e/RealmeX2Pro edk2');out=Path('/mnt/e/edk2-samurai-out/kernel125');assert os.geteuid()==0
runpy.run_path(str(root/'reference/kernel122/ensure-rootfs-volume.py'))
runpy.run_path(str(root/'reference/kernel118/ensure-build-volume.py'))
results=[]
for stage,label,mount,image in [(122,'rootfs',Path('/home/cy122/pmos-samurai-rootfs122'),Path('/mnt/e/edk2-samurai-out/kernel122/rootfs-build-volume.ext4')),(118,'kernel',Path('/home/cy122/pmos-samurai-kernel118'),Path('/mnt/e/edk2-samurai-out/kernel118/build-volume.ext4'))]:
 lockpath=Path('/run/samurai-build-volume-locks')/('samurai-rfs122-mount.lock' if stage==122 else 'samurai-k118-mount.lock')
 with lockpath.open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  sources=subprocess.check_output(['findmnt','-rn','-o','SOURCE','--mountpoint',str(mount)],text=True).splitlines();assert len(sources)==1
  assert Path(subprocess.check_output(['losetup','--noheadings','--output','BACK-FILE',sources[0]],text=True).strip()).resolve()==image.resolve()
  free=shutil.disk_usage(mount).free
  subprocess.run(['sync','-f',str(mount)],check=True,timeout=30)
  subprocess.run(['umount',str(mount)],check=True,timeout=30);assert not mount.is_mount()
  assert not subprocess.check_output(['losetup','-j',str(image)],text=True).strip()
  with (out/(label+'-volume-offline-readonly-fsck.txt')).open('w') as log:
   p=subprocess.run(['e2fsck','-f','-n',str(image)],stdout=log,stderr=subprocess.STDOUT,timeout=60)
  results.append(dict(volume=label,unmounted=True,inner_volume_free_bytes_before_unmount=free,offline_readonly_fsck_exit=p.returncode));assert p.returncode==0
report=dict(volumes=results,only_new_private_e_volumes_checked=True,original_wsl_vhd_not_fscked_or_resized=True,rootfs122_unmounted=True,kernel118_unmounted=True,host_c_free_bytes=shutil.disk_usage('/mnt/c').free,host_e_free_bytes=shutil.disk_usage('/mnt/e').free,goal_complete=False)
(root/'reference/kernel125/host-volume-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
