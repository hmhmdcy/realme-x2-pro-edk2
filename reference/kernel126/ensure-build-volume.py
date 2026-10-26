from pathlib import Path
import subprocess,fcntl,os
image=Path('/mnt/e/edk2-samurai-out/kernel126/build-volume.ext4');mount=Path('/home/cy122/pmos-samurai-build126')
assert os.geteuid()==0 and image.is_file() and image.stat().st_size==24*1024**3
assert Path('/mnt/e/RealmeX2Pro edk2/reference/kernel126/volume-create-validation.json').is_file(),'creation must finish before dependent mount'
assert subprocess.check_output(['blkid','-s','LABEL','-o','value',str(image)],text=True).strip()=='samurai-k126'
lockdir=Path('/run/samurai-build-volume-locks');lockdir.mkdir(mode=0o700,exist_ok=True)
assert not lockdir.is_symlink() and lockdir.stat().st_uid==0 and lockdir.stat().st_mode & 0o077==0
with (lockdir/'samurai-k126-mount.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 if not mount.is_mount():
  assert mount.is_dir() and not list(mount.iterdir())
  subprocess.run(['mount','-o','loop',str(image),str(mount)],check=True)
 sources=subprocess.check_output(['findmnt','-rn','-o','SOURCE','--mountpoint',str(mount)],text=True).splitlines();assert len(sources)==1 and sources[0].startswith('/dev/loop')
 assert Path(subprocess.check_output(['losetup','--noheadings','--output','BACK-FILE',sources[0]],text=True).strip()).resolve()==image.resolve()
print('K126_E_BUILD_VOLUME_MOUNT_VERIFIED')
