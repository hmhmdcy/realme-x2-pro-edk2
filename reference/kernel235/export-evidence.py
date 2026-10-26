"""Keep native staging/health receipts privately and verify each archived member."""
from pathlib import Path
import hashlib
import io
import json
import tarfile
import host

code = r'''
from pathlib import Path
import hashlib,json,os,tarfile
os.umask(0o077)
root=Path('/var/lib/samurai');out=root/'k235-evidence';assert not out.exists()
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k233-runtime/boot-id-private.txt').read_bytes()
assert json.loads((root/'k235-module-stage/transaction-state-private.json').read_text())['state']=='verified'
assert json.loads((root/'k235-final-health/summary.json').read_text())['taint']==0
files=[]
for name in ['k235-baseline','k235-tools','k235-module-stage','k235-final-health']:
 context=root/name;assert context.is_dir()
 for p in sorted(context.rglob('*')):
  if p.is_file():
   assert not p.is_symlink() and p.suffix not in ('.raw','.dng','.png','.jpg','.rgb','.mp4')
   files.append(p)
out.mkdir(mode=0o700)
manifest={str(p.relative_to(root)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files}
with tarfile.open(out/'evidence-private.tar.gz','w:gz') as archive:
 for p in files:archive.add(p,arcname=str(p.relative_to(root)),recursive=False)
data=(out/'evidence-private.tar.gz').read_bytes()
meta=dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),files=manifest)
(out/'manifest-private.json').write_text(json.dumps(meta,indent=2)+'\n')
print(json.dumps(meta))
'''
result = host.ssh('python3 -', input=code.encode(), timeout=40)
manifest_path = host.PRIVATE / 'native-evidence-manifest-private.json'
assert not manifest_path.exists()
manifest_path.write_bytes(result.stdout)
manifest = json.loads(result.stdout)
data = bytearray()
for start in range(0, manifest['bytes'], 48 * 1024):
    count = min(48 * 1024, manifest['bytes'] - start)
    read = "from pathlib import Path;import sys;f=Path('/var/lib/samurai/k235-evidence/evidence-private.tar.gz').open('rb');f.seek(%d);sys.stdout.buffer.write(f.read(%d));f.close()" % (start, count)
    block = host.ssh('python3 -', input=read.encode(), timeout=25).stdout
    assert len(block) == count
    data.extend(block)
assert hashlib.sha256(data).hexdigest() == manifest['sha256']
target = host.PRIVATE / 'native-evidence-private.tar.gz'
assert not target.exists()
target.write_bytes(data)
with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
    members = archive.getmembers()
    assert {member.name for member in members} == set(manifest['files'])
    assert all(member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts for member in members)
    for member in members:
        payload = archive.extractfile(member).read()
        expected = manifest['files'][member.name]
        assert len(payload) == expected['bytes'] and hashlib.sha256(payload).hexdigest() == expected['sha256']
report = dict(stage=235, native_members=len(members), all_members_verified=True,
              native_baseline_staging_backups_and_health_preserved=True,
              no_scene_pixels_saved_or_transferred=True, private_archive_fingerprint_not_published=True,
              usb_chunk_bytes=48 * 1024)
(Path(__file__).resolve().parent / 'evidence-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
