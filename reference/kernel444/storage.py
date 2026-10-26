from pathlib import Path
from contextlib import contextmanager
import importlib.util,subprocess
s=importlib.util.spec_from_file_location('storage443',Path(__file__).resolve().parents[1]/'kernel443/storage.py');old=importlib.util.module_from_spec(s);s.loader.exec_module(old)
mount=old.mount;SDK=old.SDK
def candidate():
 return mount.mounted_build().parent/'libcamera444-focused-ipe'
@contextmanager
def sdk_candidate():
 p=candidate();assert p.is_dir();slot=SDK/'work/libcamera'
 assert subprocess.run(['mountpoint','-q',str(slot)],capture_output=True).returncode
 subprocess.run(['mount','--bind',str(p),str(slot)],check=True,capture_output=True)
 try:yield slot/'src/libcamera-v0.7.2'
 finally:subprocess.run(['umount',str(slot)],check=True,capture_output=True)
