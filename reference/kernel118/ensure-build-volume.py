from pathlib import Path
import subprocess,fcntl,os
image=Path('/mnt/e/edk2-samurai-out/kernel118/build-volume.ext4')
mount=Path('/home/cy122/pmos-samurai-kernel118')
assert image.is_file() and image.stat().st_size==20*1024**3
assert subprocess.check_output(['blkid','-s','LABEL','-o','value',str(image)],text=True).strip()=='samurai-k118'
assert os.geteuid()==0,'mount verification requires root'
lockdir=Path('/run/samurai-build-volume-locks');lockdir.mkdir(mode=0o700,exist_ok=True)
assert not lockdir.is_symlink() and lockdir.stat().st_uid==0 and lockdir.stat().st_mode & 0o077==0
with (lockdir/'samurai-k118-mount.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    if not mount.is_mount():
        assert mount.is_dir() and not list(mount.iterdir()),'do not hide host files under mount'
        subprocess.run(['mount','-o','loop',str(image),str(mount)],check=True)
    assert mount.is_mount()
    sources=subprocess.check_output(['findmnt','-n','-o','SOURCE','--mountpoint',str(mount)],text=True).strip().splitlines()
    assert len(sources)==1,'refuse stacked mounts; recover and check offline first'
    source=sources[0]
    assert source.startswith('/dev/loop')
    backing=subprocess.check_output(['losetup','--noheadings','--output','BACK-FILE',source],text=True).strip()
    assert Path(backing).resolve()==image.resolve()
print('K118_E_DRIVE_BUILD_VOLUME_MOUNT_VERIFIED')
