"""Verify and remount the existing E-drive build image; never format it."""
from pathlib import Path
import fcntl, subprocess

def mounted_build():
    # Two callers may arrive while WSL is first mounting the backing image.
    # Serialize discovery and mount, so they cannot mount it on two loop devices.
    with open('/run/lock/samurai-full282-mount.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return _mounted_build_locked()


def _mounted_build_locked():
    backing=Path('/mnt/e/edk2-samurai-out/kernel282/full-kernel-build282.ext4')
    mount=Path('/mnt/samurai-full282')
    assert backing.is_file() and not backing.is_symlink() and backing.stat().st_size==32*1024**3
    assert mount.is_dir() and not mount.is_symlink()
    exact=[line for line in Path('/proc/self/mountinfo').read_text().splitlines() if line.split()[4]==str(mount)]
    if not exact:
        assert not any(mount.iterdir()), 'Refuse to hide files at the mountpoint'
        subprocess.run(['mount','-o','loop,noatime',str(backing),str(mount)],check=True,capture_output=True)
    fields=subprocess.check_output(['findmnt','-n','-o','FSTYPE,SOURCE,TARGET',str(mount)],text=True).split()
    assert len(fields)==3 and fields[0]=='ext4' and fields[1].startswith('/dev/loop') and fields[2]==str(mount)
    actual=Path('/sys/class/block',Path(fields[1]).name,'loop/backing_file').read_text().strip()
    assert Path(actual).resolve()==backing.resolve()
    assert (mount/'build/.config').is_file() and (mount/'tmp').is_dir()
    return mount/'build'
