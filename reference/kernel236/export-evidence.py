"""Privately archive transition, failed first probe, correction and real ID."""
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
root=Path('/var/lib/samurai');out=root/'k236-evidence';assert not out.exists()
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k236-runtime/boot-id-private.txt').read_bytes()
assert json.loads((root/'k236-runtime/state-private.json').read_text())['exit_code']==1
assert json.loads((root/'k236-lab-fix/state-private.json').read_text())['exit_code']==0
assert json.loads((root/'k236-final-health-r2/summary.json').read_text())['taint']==0
names=['k236-baseline','k236-tools','k236-quiesce-runner','k236-quiesce','k236-runtime','k236-first-failure',
       'k236-lab-fix','k236-media-enumeration','k236-final-health','k236-health-failure','k236-final-health-r2']
names+=sorted(p.name for p in root.glob('k236-inspect-*') if p.is_dir())
files=[]
for name in names:
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
    read = "from pathlib import Path;import sys;f=Path('/var/lib/samurai/k236-evidence/evidence-private.tar.gz').open('rb');f.seek(%d);sys.stdout.buffer.write(f.read(%d));f.close()" % (start, count)
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
report = dict(stage=236, native_members=len(members), all_members_verified=True,
              transition_failed_first_probe_fixed_lab_id_trace_and_health_preserved=True,
              first_observer_failure_and_first_health_assumption_failure_retained=True,
              no_scene_pixels_saved_or_transferred=True, private_archive_fingerprint_not_published=True,
              usb_chunk_bytes=48 * 1024)
(Path(__file__).resolve().parent / 'evidence-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
