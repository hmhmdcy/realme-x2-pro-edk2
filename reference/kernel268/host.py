"""Use the actual267 boot/USB guard; keep268 userspace evidence separate."""
from pathlib import Path
import importlib.util
import hashlib
import shlex

PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel268');PRIVATE.mkdir(mode=0o700,parents=True,exist_ok=True)
spec=importlib.util.spec_from_file_location('current267',Path(__file__).resolve().parents[1]/'kernel267/host.py')
current=importlib.util.module_from_spec(spec);spec.loader.exec_module(current)
ssh=current.ssh

def upload(local,remote):
    local=Path(local);assert remote.startswith('/var/lib/samurai/k268-') and '..' not in Path(remote).parts
    data=local.read_bytes();digest=hashlib.sha256(data).hexdigest()
    code="from pathlib import Path;import sys,hashlib,os;os.umask(0o077);p=Path("+repr(remote)+");assert not p.exists();p.parent.mkdir(mode=0o700,parents=True,exist_ok=True);b=sys.stdin.buffer.read();assert len(b)=="+str(len(data))+" and hashlib.sha256(b).hexdigest()=="+repr(digest)+";p.write_bytes(b)"
    return ssh('python3 -c '+shlex.quote(code),input=data,timeout=45)
