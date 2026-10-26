from pathlib import Path
import fcntl
import os
import subprocess
image = Path('/mnt/e/edk2-samurai-out/kernel134/build-volume.ext4')
mount = Path('/home/cy122/pmos-samurai-build134')
assert os.geteuid() == 0 and image.is_file() and image.stat().st_size == 8 * 1024**3
assert Path('/mnt/e/RealmeX2Pro edk2/reference/kernel134/volume-create-validation.json').is_file()
assert subprocess.check_output(['blkid', '-s', 'LABEL', '-o', 'value', str(image)], text=True).strip() == 'samurai-k134'
locks = Path('/run/samurai-build-volume-locks')
locks.mkdir(mode=0o700, exist_ok=True)
assert not locks.is_symlink() and locks.stat().st_uid == 0 and locks.stat().st_mode & 0o077 == 0
with (locks / 'samurai-k134-mount.lock').open('a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    if not mount.is_mount():
        assert mount.is_dir() and not list(mount.iterdir())
        subprocess.run(['mount', '-o', 'loop', str(image), str(mount)], check=True)
    sources = subprocess.check_output(['findmnt', '-rn', '-o', 'SOURCE', '--mountpoint', str(mount)], text=True).splitlines()
    assert len(sources) == 1 and sources[0].startswith('/dev/loop')
    assert Path(subprocess.check_output(['losetup', '--noheadings', '--output', 'BACK-FILE', sources[0]], text=True).strip()).resolve() == image.resolve()
print('K134_PRIVATE_BUILD_VOLUME_MOUNT_VERIFIED', flush=True)
