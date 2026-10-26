"""Retain a bounded userspace core and inspect it with the matching build."""
from pathlib import Path
import io,json,shlex,subprocess,sys,tarfile
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;storage.mount.mounted_build()
attempt=sys.argv[1];assert attempt.startswith('r') and attempt[1:].isdigit()
code='''from pathlib import Path
import sys,tarfile
r=Path(ROOT)
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz',compresslevel=1) as tar:
 for p in r.rglob('*'):
  if p.is_file() and (p.name=='core' or p.suffix=='.log' or p.name=='state.json'):tar.add(p,arcname=str(p.relative_to(r)))
'''.replace('ROOT',repr('/var/lib/samurai/k441-variable-pd10-'+attempt))
folder=P/('core-'+attempt);folder.mkdir(exist_ok=True)
if not (folder/'1920x1080-isolated/core').exists():
 q=host.ssh('python3 -c '+shlex.quote(code),timeout=90);q.check_returncode()
 with tarfile.open(fileobj=io.BytesIO(q.stdout),mode='r:gz') as tar:
  for m in tar.getmembers():
   p=folder/m.name;assert m.isfile() and p.resolve().is_relative_to(folder.resolve());p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(m).read())
core=folder/'1920x1080-isolated/core';assert core.is_file()
tree=storage.candidate()/'src/libcamera-v0.7.2'
args=['gdb-multiarch','-batch','-nx','-ex','set debuginfod enabled off','-ex','set sysroot '+str(storage.SDK),'-ex','set solib-search-path '+':'.join(map(str,[P,tree/'output/src/libcamera',tree/'output/src/libcamera/base',storage.SDK/'usr/lib',storage.SDK/'lib'])),'-ex','file '+str(P/'capture'),'-ex','core-file '+str(core),'-ex','thread apply all bt 24']
q=subprocess.run(args,capture_output=True,timeout=45);(P/('core-'+attempt+'-backtrace-private.txt')).write_bytes(q.stdout+q.stderr)
print(q.stdout.decode(errors='replace')[-14000:]);print(q.stderr.decode(errors='replace')[-1800:]);q.check_returncode()
