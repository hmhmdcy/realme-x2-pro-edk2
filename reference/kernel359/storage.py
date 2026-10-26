from contextlib import contextmanager
from pathlib import Path
import importlib.util, subprocess

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
def candidate():
    return old.mounted_build().parent/'libcamera359-exposure-built'
@contextmanager
def sdk_candidate():
    source=candidate();work=SDK/'work/libcamera'
    assert source.is_dir() and work.is_dir()
    assert subprocess.run(['mountpoint','-q',str(work)],capture_output=True).returncode
    subprocess.run(['mount','--bind',str(source),str(work)],check=True,capture_output=True)
    try:yield work/'src/libcamera-v0.7.2'
    finally:subprocess.run(['umount',str(work)],check=True,capture_output=True)
