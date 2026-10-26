from contextlib import contextmanager
from pathlib import Path
import importlib.util,subprocess
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
def candidate():return old.mounted_build().parent/'libcamera360-combined-r28-built'
@contextmanager
def sdk_candidate():
    source=candidate();slot=SDK/'work/libcamera'
    assert source.is_dir() and not subprocess.run(['mountpoint','-q',str(slot)],capture_output=True).returncode==0
    subprocess.run(['mount','--bind',str(source),str(slot)],check=True,capture_output=True)
    try:yield slot/'src/libcamera-v0.7.2'
    finally:subprocess.run(['umount',str(slot)],check=True,capture_output=True)
