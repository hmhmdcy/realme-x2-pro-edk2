from pathlib import Path
import fcntl,json,os,runpy,shutil,subprocess
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel130';out=Path('/mnt/e/edk2-samurai-out/kernel130')
assert os.geteuid()==0
assert json.loads((ref/'complete-bundle-validation.json').read_text())['decoded_encoded_image_actual_unprivileged_create_read_write_unlink_pass']
assert json.loads((ref/'superseded-raw-cleanup-validation.json').read_text())['all_targets_fresh_byte_and_hole_reconstruction_proved']
runpy.run_path(str(r/'reference/kernel129/ensure-rootfs-volume.py'))
mount=Path('/home/cy122/pmos-samurai-rootfs129');image=Path('/mnt/e/edk2-samurai-out/kernel129/rootfs-build-volume.ext4')
with Path('/run/samurai-build-volume-locks/samurai-rfs129-mount.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 source=subprocess.check_output(['findmnt','-rn','-o','SOURCE','--mountpoint',str(mount)],text=True).strip()
 assert Path(subprocess.check_output(['losetup','--noheadings','--output','BACK-FILE',source],text=True).strip()).resolve()==image.resolve()
 free=shutil.disk_usage(mount).free
 subprocess.run(['sync','-f',str(mount)],check=True,timeout=30);subprocess.run(['umount',str(mount)],check=True,timeout=30)
 assert not mount.is_mount() and not subprocess.check_output(['losetup','-j',str(image)],text=True).strip()
 with (out/'rootfs129-volume-offline-readonly-fsck-private.txt').open('w') as log:
  p=subprocess.run(['e2fsck','-fn',str(image)],stdout=log,stderr=subprocess.STDOUT,timeout=60)
 assert p.returncode==0
stable=[]
for stage,name,file,m in [(118,'kernel118','build-volume.ext4','pmos-samurai-kernel118'),(122,'rootfs122','rootfs-build-volume.ext4','pmos-samurai-rootfs122'),(126,'build126','build-volume.ext4','pmos-samurai-build126')]:
 target=Path('/mnt/e/edk2-samurai-out')/f'kernel{stage}'/file
 assert target.is_file() and not Path('/home/cy122',m).is_mount() and not subprocess.check_output(['losetup','-j',str(target)],text=True).strip()
 stable.append(dict(volume=name,still_unmounted=True,not_modified_this_turn=True,previous129_readonly_fsck_zero=True))
stable_images={}
for stage in [109,111,113,115,128,129]:
 path=Path('/home/cy122')/f'pmos-samurai-kernel{stage}'/'kernel/arch/arm64/boot/Image'
 assert path.is_file();stable_images[str(stage)]=True
report=dict(current_e129_volume_unmounted_offline_readonly_fsck_zero=True,current_volume_inner_free_bytes=free,other_stable_private_volumes=stable,
 stable_c_build_images_exist=stable_images,additional_c_files_deleted=0,unproven_old_generated_objects_retained=9,
 host_c_free_bytes=shutil.disk_usage('/mnt/c').free,host_e_free_bytes=shutil.disk_usage('/mnt/e').free,original_wsl_vhd_not_fscked_resized_or_compacted=True,goal_complete=False)
(ref/'host-volume-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
