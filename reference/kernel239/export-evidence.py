"""Archive native diagnostics and r15 transaction receipts, with no scene pixels."""
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
r=Path('/var/lib/samurai');out=r/'k239-evidence';assert not out.exists()
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
health=json.loads((r/'k239-final-health/summary.json').read_text())
assert health['taint']==0 and health['installed_r15_r10'] and health['rear_rgb_strict_acceptance_failed']
names=['k239-baseline','k239-candidate-stage','k239-fixed-rgb-r14','k239-paired-r14',
       'k239-r15-startup','k239-front-r15-raw','k239-front-r15-rgb',
       'k239-r15-installed-startup','k239-r15-package-transaction','k239-final-health']
files=[]
for name in names:
 context=r/name;assert context.is_dir()
 for p in sorted(context.rglob('*')):
  if p.is_file():
   assert not p.is_symlink() and p.suffix not in ['.raw','.dng','.png','.jpg','.rgb','.mp4','.apk']
   files.append(p)
# ODM payload is already exported and verified separately. Preserve its origin,
# cleanup and before/after block-hash receipts without duplicating payload.
for p in sorted((r/'k239-odm-source').iterdir()):
 if p.is_file():
  assert not p.is_symlink();files.append(p)
for name in ['forward-manifest.json']:
 files.append(r/'k239-r15-package-candidates'/name)
assert len(set(files))==len(files)
out.mkdir(mode=0o700)
manifest={str(p.relative_to(r)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files}
with tarfile.open(out/'evidence-private.tar.gz','w:gz') as a:
 for p in files:a.add(p,arcname=str(p.relative_to(r)),recursive=False)
data=(out/'evidence-private.tar.gz').read_bytes()
meta=dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),files=manifest)
(out/'manifest-private.json').write_text(json.dumps(meta,indent=2)+'\n')
print(json.dumps(meta))
'''
result = host.ssh('python3 -', input=code.encode(), timeout=50)
manifest_path = host.PRIVATE / 'native-evidence-manifest-private.json'
assert not manifest_path.exists()
manifest_path.write_bytes(result.stdout)
manifest = json.loads(result.stdout)
data = bytearray()
for start in range(0, manifest['bytes'], 48 * 1024):
    count = min(48 * 1024, manifest['bytes'] - start)
    read = "from pathlib import Path;import sys;f=Path('/var/lib/samurai/k239-evidence/evidence-private.tar.gz').open('rb');f.seek(%d);sys.stdout.buffer.write(f.read(%d));f.close()" % (start, count)
    block = host.ssh('python3 -', input=read.encode(), timeout=25).stdout
    assert len(block) == count
    data.extend(block)
assert hashlib.sha256(data).hexdigest() == manifest['sha256']
target = host.PRIVATE / 'native-evidence-private.tar.gz'
assert not target.exists()
target.write_bytes(data)
with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
    members = archive.getmembers()
    assert len(members) == len(manifest['files'])
    assert {m.name for m in members} == set(manifest['files'])
    assert all(m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts for m in members)
    for member in members:
        payload = archive.extractfile(member).read()
        expected = manifest['files'][member.name]
        assert len(payload) == expected['bytes'] and hashlib.sha256(payload).hexdigest() == expected['sha256']
report = dict(stage=239, native_members=len(members), all_members_verified=True,
              initial_r14_failure_paired_raw_rgb_r15_restart_and_default_receipts_preserved=True,
              strict_zero_frames_and_complete_cleanup_retained=True,
              signed_seven_package_upgrade_and_policy_reload_receipts_preserved=True,
              odm_payload_separately_exported_and_verified=True,
              no_scene_pixels_saved_or_transferred=True,
              private_archive_fingerprint_not_published=True, usb_chunk_bytes=48 * 1024)
(R / 'evidence-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
