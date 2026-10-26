from pathlib import Path
import hashlib,io,json,tarfile
import host
code=r'''
from pathlib import Path
import hashlib,json,tarfile
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes();p=r/'k238-vendor-followup';assert json.loads((p/'state-private.json').read_text())['exit_code']==0
target=p/'vendor-followup-source-private.tar.gz';assert not target.exists()
files=[f for f in sorted(p.rglob('*')) if f.is_file()];manifest={str(f.relative_to(p)):dict(bytes=f.stat().st_size,sha256=hashlib.sha256(f.read_bytes()).hexdigest()) for f in files}
with tarfile.open(target,'w:gz') as archive:
 for f in files:archive.add(f,arcname=str(f.relative_to(p)),recursive=False)
data=target.read_bytes();print(json.dumps(dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),files=manifest)))
'''
r=host.ssh('python3 -',input=code.encode(),timeout=35);manifest=json.loads(r.stdout);(host.PRIVATE/'vendor-followup-native-manifest-private.json').write_bytes(r.stdout)
data=bytearray()
for start in range(0,manifest['bytes'],48*1024):
 count=min(48*1024,manifest['bytes']-start)
 code="from pathlib import Path;import sys;f=Path('/var/lib/samurai/k238-vendor-followup/vendor-followup-source-private.tar.gz').open('rb');f.seek(%d);sys.stdout.buffer.write(f.read(%d));f.close()"%(start,count)
 block=host.ssh('python3 -',input=code.encode(),timeout=25).stdout;assert len(block)==count;data.extend(block)
assert hashlib.sha256(data).hexdigest()==manifest['sha256'];(host.PRIVATE/'vendor-followup-source-private.tar.gz').write_bytes(data)
dest=host.PRIVATE/'vendor-followup-source-private';assert not dest.exists();dest.mkdir(mode=0o700)
with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as archive:
 members=archive.getmembers();assert {m.name for m in members}==set(manifest['files'])
 for m in members:
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  payload=archive.extractfile(m).read();expected=manifest['files'][m.name];assert len(payload)==expected['bytes'] and hashlib.sha256(payload).hexdigest()==expected['sha256']
  target=dest/m.name;target.parent.mkdir(parents=True,exist_ok=True,mode=0o700);target.write_bytes(payload);target.chmod(0o600)
report=dict(stage=238,members=len(members),all_members_verified=True,private_payload_ready_for_elf_audit=True,no_vendor_code_run=True,no_partition_or_archive_fingerprint_published=True)
(Path(__file__).resolve().parent/'vendor-followup-export-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
