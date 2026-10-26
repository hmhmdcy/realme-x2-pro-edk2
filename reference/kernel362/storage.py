from pathlib import Path
from contextlib import contextmanager
import importlib.util,subprocess
spec=importlib.util.spec_from_file_location('storage361',Path(__file__).resolve().parents[1]/'kernel361/storage.py')
previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
SDK=previous.SDK
def candidate():return previous.candidate().parent/'libcamera362-serialized-built'
@contextmanager
def sdk_candidate():
    source=candidate();slot=SDK/'work/libcamera';assert source.is_dir()
    assert subprocess.run(['mountpoint','-q',str(slot)],capture_output=True).returncode
    subprocess.run(['mount','--bind',str(source),str(slot)],check=True,capture_output=True)
    try:yield slot/'src/libcamera-v0.7.2'
    finally:subprocess.run(['umount',str(slot)],check=True,capture_output=True)
