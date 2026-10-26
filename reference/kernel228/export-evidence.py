"""Archive only the bounded228 contexts; transfer in small verified USB chunks."""
from pathlib import Path
import hashlib
import io
import json
import tarfile
import host

code = r'''
from pathlib import Path
import hashlib,json,os,tarfile
root=Path('/var/lib/samurai');out=root/'k228-evidence';assert not out.exists()
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k228-runtime/boot-id-private.txt').read_bytes()
out.mkdir(mode=0o700)
names=['k228-baseline','k228-tools','k228-module-install','k228-quiesce-runner','k228-quiesce','k228-runtime','k228-native-sensors','k228-native-sensors-r2','k228-intree-stage']
files=[]
for name in names:
 for p in sorted((root/name).rglob('*')):
  if p.is_file():assert not p.is_symlink();files.append(p)
manifest={str(p.relative_to(root)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files}
with tarfile.open(out/'evidence-private.tar.gz','w:gz') as archive:
 for p in files:archive.add(p,arcname=str(p.relative_to(root)),recursive=False)
data=(out/'evidence-private.tar.gz').read_bytes();meta=dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),files=manifest)
(out/'manifest-private.json').write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps(meta))
'''
result = host.ssh('python3 -', input=code.encode(), timeout=35)
(host.PRIVATE / 'native-evidence-manifest-private.json').write_bytes(result.stdout)
manifest = json.loads(result.stdout)
data = bytearray()
for start in range(0, manifest['bytes'], 48 * 1024):
    end = min(manifest['bytes'], start + 48 * 1024)
    read = "from pathlib import Path;import sys;f=Path('/var/lib/samurai/k228-evidence/evidence-private.tar.gz').open('rb');f.seek(%d);sys.stdout.buffer.write(f.read(%d));f.close()" % (start, end - start)
    block = host.ssh('python3 -', input=read.encode(), timeout=25).stdout
    assert len(block) == end - start
    data.extend(block)
assert hashlib.sha256(data).hexdigest() == manifest['sha256']
archive_path = host.PRIVATE / 'native-evidence-private.tar.gz'
assert not archive_path.exists()
archive_path.write_bytes(data)
with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
    members = archive.getmembers()
    assert {m.name for m in members} == set(manifest['files']) and all(m.isfile() for m in members)
    for m in members:
        payload = archive.extractfile(m).read()
        expected = manifest['files'][m.name]
        assert len(payload) == expected['bytes'] and hashlib.sha256(payload).hexdigest() == expected['sha256']
report = dict(stage=228, private_native_archive_members=len(members), all_members_verified=True,
              usb_transfer_chunk_bytes=48 * 1024, archive_fingerprint_kept_private=True,
              first_runtime_taint_failure_retained=True, first_ordinary_claim_denial_retained=True,
              corrected_active_session_claims_retained=True, external_and_intree_modules_retained=True,
              new_boot_guard_retained=True, next_clean_intree_boot_pending=True)
(Path(__file__).resolve().parent / 'evidence-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
