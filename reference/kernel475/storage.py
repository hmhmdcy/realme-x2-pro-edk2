"""Guard the existing ext4 volume; 475 writes only its own private package area."""
from pathlib import Path
import importlib.util

spec = importlib.util.spec_from_file_location('storage461', Path(__file__).resolve().parents[1] / 'kernel461/storage.py')
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)
mount = old.mount
SDK = old.SDK


def workspace():
    return mount.mounted_build().parent / 'camera475-r33-r28'

