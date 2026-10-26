"""473 private copy; only sdk_candidate() binds the separately handed-off SDK."""
from contextlib import contextmanager
from pathlib import Path
import importlib.util
import subprocess

spec = importlib.util.spec_from_file_location('storage461', Path(__file__).resolve().parents[1] / 'kernel461/storage.py')
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)
mount = old.mount
SDK = old.SDK


def candidate():
    return mount.mounted_build().parent / 'libcamera473-processed-manager-capacity'


@contextmanager
def sdk_candidate():
    path = candidate()
    slot = SDK / 'work/libcamera'
    assert path.is_dir()
    assert subprocess.run(['mountpoint', '-q', str(slot)], capture_output=True).returncode != 0, 'SDK slot is already bound'
    subprocess.run(['mount', '--bind', str(path), str(slot)], check=True, capture_output=True)
    try:
        yield slot / 'src/libcamera-v0.7.2'
    finally:
        subprocess.run(['umount', str(slot)], check=True, capture_output=True)

