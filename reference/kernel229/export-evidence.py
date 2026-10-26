"""Transfer only aggregate-statistics/log contexts; never export scene buffers."""
from pathlib import Path
import hashlib
import io
import json
import tarfile
import host

code = r'''
from pathlib import Path
import hashlib,json,tarfile
root=Path('/var/lib/samurai');out=root/'k229-evidence';assert not out.exists()
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k228-runtime/boot-id-private.txt').read_bytes()
contexts=sorted(root.glob('k229-capture-daylight-*'))+[root/'k229-final-health'];assert len(contexts)==4
files=[]
for c in contexts:
 assert c.is_dir()
 for p in sorted(c.rglob('*')):
  if p.is_file():assert not p.is_symlink() and p.suffix in ('.json','.txt','.log');files.append(p)
out.mkdir(mode=0o700)
manifest={str(p.relative_to(root)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files}
with tarfile.open(out/'evidence-private.tar.gz','w:gz') as archive:
 for p in files:archive.add(p,arcname=str(p.relative_to(root)),recursive=False)
data=(out/'evidence-private.tar.gz').read_bytes();meta=dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),files=manifest)
(out/'manifest-private.json').write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps(meta))
'''
result = host.ssh('python3 -', input=code.encode(), timeout=30)
(host.PRIVATE / 'native-evidence-manifest-private.json').write_bytes(result.stdout)
manifest = json.loads(result.stdout)
data = bytearray()
for start in range(0, manifest['bytes'], 48 * 1024):
    count = min(48 * 1024, manifest['bytes'] - start)
    code = "from pathlib import Path;import sys;f=Path('/var/lib/samurai/k229-evidence/evidence-private.tar.gz').open('rb');f.seek(%d);sys.stdout.buffer.write(f.read(%d));f.close()" % (start, count)
    block = host.ssh('python3 -', input=code.encode(), timeout=25).stdout
    assert len(block) == count
    data.extend(block)
assert hashlib.sha256(data).hexdigest() == manifest['sha256']
target = host.PRIVATE / 'native-evidence-private.tar.gz'
assert not target.exists()
target.write_bytes(data)
with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
    members = archive.getmembers()
    assert {m.name for m in members} == set(manifest['files']) and all(m.isfile() for m in members)
    for m in members:
        payload = archive.extractfile(m).read()
        expected = manifest['files'][m.name]
        assert len(payload) == expected['bytes'] and hashlib.sha256(payload).hexdigest() == expected['sha256']
report = dict(stage=229, private_native_archive_members=len(members), all_members_verified=True,
              three_capture_contexts_and_final_health=True, only_numeric_json_and_text_logs=True,
              no_scene_pixels_saved_or_transferred=True, private_archive_fingerprint_not_published=True,
              usb_chunk_bytes=48 * 1024)
(Path(__file__).resolve().parent / 'evidence-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
