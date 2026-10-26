from pathlib import Path
from contextlib import contextmanager
import importlib.util,subprocess
s=importlib.util.spec_from_file_location('storage284',Path(__file__).resolve().parents[1]/'kernel284/storage.py');mount=importlib.util.module_from_spec(s);s.loader.exec_module(mount)
SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
def candidate():return mount.mounted_build().parent/'libcamera436-tone-domain'
@contextmanager
def sdk_candidate():
 source=candidate();slot=SDK/'work/libcamera'
 assert source.is_dir() and subprocess.run(['mountpoint','-q',str(slot)],capture_output=True).returncode
 subprocess.run(['mount','--bind',str(source),str(slot)],check=True,capture_output=True)
 try:yield slot/'src/libcamera-v0.7.2'
 finally:subprocess.run(['umount',str(slot)],check=True,capture_output=True)
