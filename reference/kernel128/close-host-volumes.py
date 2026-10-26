from pathlib import Path
import subprocess,runpy,json,shutil,fcntl,os
r=Path('/mnt/e/RealmeX2Pro edk2');out=Path('/mnt/e/edk2-samurai-out/kernel128');assert os.geteuid()==0
assert json.loads((r/'reference/kernel128/complete-bundle-validation.json').read_text())['decoded_encoded_image_actual_unprivileged_create_read_write_unlink_pass']
assert (r/'reference/kernel128/superseded-raw-cleanup-validation.json').is_file()
runpy.run_path(str(r/'reference/kernel118/ensure-build-volume.py'))
runpy.run_path(str(r/'reference/kernel122/ensure-rootfs-volume.py'))
runpy.run_path(str(r/'reference/kernel126/ensure-build-volume.py'))
results=[]
for stage,label,mount,image,lockname in [
 (118,'kernel118',Path('/home/cy122/pmos-samurai-kernel118'),Path('/mnt/e/edk2-samurai-out/kernel118/build-volume.ext4'),'samurai-k118-mount.lock'),
 (122,'rootfs122',Path('/home/cy122/pmos-samurai-rootfs122'),Path('/mnt/e/edk2-samurai-out/kernel122/rootfs-build-volume.ext4'),'samurai-rfs122-mount.lock'),
 (126,'build126',Path('/home/cy122/pmos-samurai-build126'),Path('/mnt/e/edk2-samurai-out/kernel126/build-volume.ext4'),'samurai-k126-mount.lock')]:
 with (Path('/run/samurai-build-volume-locks')/lockname).open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  sources=subprocess.check_output(['findmnt','-rn','-o','SOURCE','--mountpoint',str(mount)],text=True).splitlines();assert len(sources)==1
  assert Path(subprocess.check_output(['losetup','--noheadings','--output','BACK-FILE',sources[0]],text=True).strip()).resolve()==image.resolve()
  free=shutil.disk_usage(mount).free;subprocess.run(['sync','-f',str(mount)],check=True,timeout=30)
  subprocess.run(['umount',str(mount)],check=True,timeout=30);assert not mount.is_mount()
  assert not subprocess.check_output(['losetup','-j',str(image)],text=True).strip()
  with (out/(label+'-volume-offline-readonly-fsck-private.txt')).open('w') as log:
   p=subprocess.run(['e2fsck','-fn',str(image)],stdout=log,stderr=subprocess.STDOUT,timeout=60)
  assert p.returncode==0
  item=dict(volume=label,unmounted=True,inner_volume_free_bytes=free,offline_readonly_fsck_exit=0);results.append(item);print(json.dumps(item),flush=True)
report=dict(volumes=results,all3_private_e_volumes_unmounted_readonly_fsck_zero=True,original_wsl_vhd_not_fscked_resized_or_compacted=True,stable_builds_preserved=True,host_c_free_bytes=shutil.disk_usage('/mnt/c').free,host_e_free_bytes=shutil.disk_usage('/mnt/e').free,goal_complete=False)
(r/'reference/kernel128/host-volume-validation.json').write_text(json.dumps(report,indent=2)+'\n');print('K128_HOST_VOLUMES_CLOSED_READONLY_CHECKED',flush=True)
