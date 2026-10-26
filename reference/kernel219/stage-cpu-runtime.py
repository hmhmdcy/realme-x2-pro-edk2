from pathlib import Path
import hashlib,host,json,shlex

archive=host.PRIVATE.parent/'kernel218/cpu-runtime-private.tar.gz';data=archive.read_bytes()
code="from pathlib import Path;root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k219-runtime/boot-id-private.txt').read_bytes();p=root/'k219-cpu-runtime-stage';assert not p.exists();p.mkdir(mode=0o700);(p/'runtime.tar.gz').touch(mode=0o600)"
host.ssh('python3 -c '+shlex.quote(code),timeout=30)
for offset in range(0,len(data),65536):
    chunk=data[offset:offset+65536]
    code="from pathlib import Path;import hashlib,sys;p=Path('/var/lib/samurai/k219-cpu-runtime-stage/runtime.tar.gz');d=sys.stdin.buffer.read();assert len(d)=="+str(len(chunk))+" and hashlib.sha256(d).hexdigest()=="+repr(hashlib.sha256(chunk).hexdigest())+";assert p.stat().st_size=="+str(offset)+";p.open('ab').write(d)"
    host.ssh('python3 -c '+shlex.quote(code),input=chunk,timeout=30)
code=r'''
from pathlib import Path,PurePosixPath
import hashlib,json,os,tarfile
archive=Path('/var/lib/samurai/k219-cpu-runtime-stage/runtime.tar.gz');prefix=Path('/run/samurai-camera219-cpu')
assert hashlib.sha256(archive.read_bytes()).hexdigest()==ARCHIVE_SHA and not prefix.exists()
prefix.mkdir(mode=0o755)
with tarfile.open(archive) as tar:
    for member in tar.getmembers():
        p=PurePosixPath(member.name);assert not p.is_absolute() and '..' not in p.parts and not member.isdev()
        if member.issym():assert '/' not in member.linkname and member.linkname not in ['.','..']
    tar.extractall(prefix,filter='data')
for p in [prefix]+[p for p in prefix.rglob('*') if p.is_dir()]:p.chmod(0o755)
manifest=json.loads((prefix/'manifest.json').read_text())
for name,item in manifest.items():
    p=prefix/name
    if 'target' in item:assert p.is_symlink() and os.readlink(p)==item['target']
    else:assert hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256'];p.chmod(item['mode'])
print('Verified218 CPU prototype staged for physical full-mode testing; system r5 unchanged')
'''.replace('ARCHIVE_SHA',repr(hashlib.sha256(data).hexdigest()))
p=host.ssh('python3 -',input=code.encode(),timeout=40);print(p.stdout.decode().strip())
