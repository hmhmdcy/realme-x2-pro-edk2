"""Fetch the already completed read-only collection in bounded transport chunks."""
from pathlib import Path
import hashlib,json,shlex,tarfile
import host
P=host.PRIVATE;report=json.loads((P/'oem-hal-source.json').read_text())
assert report['unmounted'] and report['read_only_noload_noexec']
archive=P/'hal-source.tar.gz'
with archive.open('wb') as output:
 for start in range(0,report['archive_bytes'],262144):
  size=min(262144,report['archive_bytes']-start)
  code="from pathlib import Path;import sys;p=Path('/var/lib/samurai/k316-oem-hal-source/hal-source.tar.gz');f=p.open('rb');f.seek("+str(start)+");sys.stdout.buffer.write(f.read("+str(size)+"))"
  q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=20,check=False)
  if q.returncode or len(q.stdout)!=size:raise RuntimeError(f'Chunk transport failed offset={start} code={q.returncode} bytes={len(q.stdout)} error={q.stderr.decode(errors="replace")[:250]}')
  output.write(q.stdout)
out=P/'hal-source';out.mkdir(exist_ok=True)
with tarfile.open(archive,'r:gz') as tar:tar.extractall(out,filter='data')
for row in report['files']:assert hashlib.sha256((out/row['file']).read_bytes()).hexdigest()==row['sha256']
print(json.dumps({'stock_hal_files':len(report['files']),'transferred_bytes':archive.stat().st_size,'source_fingerprints_match':True,'unmounted':True}))
