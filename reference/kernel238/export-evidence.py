"""Archive current capture/cleanup evidence; vendor payload already has its own verified exports."""
from pathlib import Path
import hashlib
import io
import json
import tarfile
import host

R = Path(__file__).resolve().parent
code = r'''
from pathlib import Path
import hashlib,json,os,tarfile
os.umask(0o077)
r=Path('/var/lib/samurai');out=r/'k238-evidence';assert not out.exists()
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
health=json.loads((r/'k238-final-health/summary.json').read_text())
assert health['taint']==0 and health['rear_rgb_strict_acceptance_failed']
names=['k238-candidate-stage','k238-candidate-permissions-fix',
       'k238-controlled-rear-r14','k238-controlled-rear-r14-r2',
       'k238-controlled-rear-rgb-r14','k238-controlled-rear-rgb-r14-r2','k238-final-health']
files=[]
for name in names:
 context=r/name;assert context.is_dir()
 for p in sorted(context.rglob('*')):
  if p.is_file():
   assert not p.is_symlink() and p.suffix not in ['.raw','.dng','.png','.jpg','.rgb','.mp4']
   files.append(p)
# Keep audit summaries and origin manifests; do not duplicate proprietary ELF
# payloads or their already verified archives in this capture archive.
for name in ['k238-vendor-audit','k238-vendor-followup']:
 for leaf in ['state-private.json','summary.json']:
  p=r/name/leaf;assert p.is_file();files.append(p)
out.mkdir(mode=0o700)
manifest={str(p.relative_to(r)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files}
with tarfile.open(out/'evidence-private.tar.gz','w:gz') as a:
 for p in files:a.add(p,arcname=str(p.relative_to(r)),recursive=False)
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
    read = "from pathlib import Path;import sys;f=Path('/var/lib/samurai/k238-evidence/evidence-private.tar.gz').open('rb');f.seek(%d);sys.stdout.buffer.write(f.read(%d));f.close()" % (start, count)
    block = host.ssh('python3 -', input=read.encode(), timeout=25).stdout
    assert len(block) == count
    data.extend(block)
assert hashlib.sha256(data).hexdigest() == manifest['sha256']
target = host.PRIVATE / 'native-evidence-private.tar.gz'
assert not target.exists()
target.write_bytes(data)
with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
    members = archive.getmembers()
    assert {m.name for m in members} == set(manifest['files'])
    assert all(m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts for m in members)
    for member in members:
        payload = archive.extractfile(member).read()
        expected = manifest['files'][member.name]
        assert len(payload) == expected['bytes'] and hashlib.sha256(payload).hexdigest() == expected['sha256']
raw_log = (host.PRIVATE / 'controlled-r2-stderr-private.txt').read_bytes()
assert b'RAW-only CPU statistics enabled' in raw_log
report = dict(stage=238, native_members=len(members), all_members_verified=True,
              raw_control_success_rgb_startup_failure_and_full_cleanup_preserved=True,
              raw_statistics_log_found_in_actual_r2_stderr=True,
              earlier_claim_log_was_imaginary_corrected=True,
              vendor_payloads_separately_exported_and_verified=True,
              no_scene_pixels_saved_or_transferred=True,
              private_archive_fingerprint_not_published=True, usb_chunk_bytes=48 * 1024)
(R / 'evidence-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
