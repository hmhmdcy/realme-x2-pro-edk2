from pathlib import Path
from contextlib import contextmanager
import importlib.util,subprocess
s=importlib.util.spec_from_file_location('storage441',Path(__file__).resolve().parents[1]/'kernel441/storage.py');old=importlib.util.module_from_spec(s);s.loader.exec_module(old)
mount=old.mount;SDK=old.SDK
def candidate():
 root=mount.mounted_build().parent;p=root/'libcamera442-bounded-dispatch'
 return p if p.exists() else old.candidate()
@contextmanager
def sdk_candidate():
 p=candidate();slot=SDK/'work/libcamera'
 assert subprocess.run(['mountpoint','-q',str(slot)],capture_output=True).returncode
 subprocess.run(['mount','--bind',str(p),str(slot)],check=True,capture_output=True)
 try:yield slot/'src/libcamera-v0.7.2'
 finally:subprocess.run(['umount',str(slot)],check=True,capture_output=True)
