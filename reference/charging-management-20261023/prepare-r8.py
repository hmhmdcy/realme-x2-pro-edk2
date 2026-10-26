"""Freeze only the tested temperature-band module and manifest; no device IO."""
from pathlib import Path
import copy
import gzip
import hashlib
import io
import json
import tarfile

REF = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
CANDIDATE = REF.parent / 'charging-session-20261023/thermal-bands-candidate'
BASE = CANDIDATE.parent / 'kernel-v2'
sha = lambda raw: hashlib.sha256(raw).hexdigest()
old_raw = (PRIVATE / 'r7-candidate/manifest.json').read_bytes()
assert sha(old_raw) == '5638db4c183ec502ed1df4facfe91111d1956754bb2338a5ddaf8838e9552c68'
old = json.loads(old_raw)
receipt_raw = (REF / 'thermal-bands-build-result.json').read_bytes()
build = json.loads(receipt_raw)
tests_raw = (CANDIDATE / 'test-result.json').read_bytes()
tested = json.loads(tests_raw)
assert build['passed'] and build['intree'] and not build['installed']
assert not build['configuration_differences'] and tested['passed']
assert sha(tests_raw) == build['test_receipt_sha256']
for name, expected in build['sources'].items():
    path = (CANDIDATE if name in tested['files'] else BASE) / name
    assert sha(path.read_bytes()) == expected
module = Path(build['module']).read_bytes()
assert sha(module) == build['module_sha256']
target = old['modules']['samurai-mp2650']['target']
assert old['modules']['samurai-mp2650']['sha256'] == 'fac827cfd3d1d847cb1db82f0a29e451652bd16a996b20666be2d9b330889cb6'
new = copy.deepcopy(old)
new['adapter_revision'] = 'r8'
new['modules']['samurai-mp2650']['sha256'] = sha(module)
new['installed_files'][target] = sha(module)
assert {name for name in old['installed_files']
        if old['installed_files'][name] != new['installed_files'][name]} == {target}
for name in ['samurai-usb-input', 'samurai-gauge-protection']:
    assert old['modules'][name] == new['modules'][name]
manifest = (json.dumps(new, indent=2) + '\n').encode()
files = {target: module, '/usr/share/samurai-charging/manifest.json': manifest}
archive_raw = io.BytesIO()
with tarfile.open(fileobj=archive_raw, mode='w') as archive:
    for name, raw in sorted(files.items()):
        entry = tarfile.TarInfo(name.lstrip('/'))
        entry.uid = entry.gid = 0
        entry.uname = entry.gname = 'root'
        entry.mode = 0o600
        entry.size = len(raw)
        entry.mtime = 0
        archive.addfile(entry, io.BytesIO(raw))
compressed = io.BytesIO()
with gzip.GzipFile(filename='', fileobj=compressed, mode='wb', mtime=0) as stream:
    stream.write(archive_raw.getvalue())
payload = compressed.getvalue()
with tarfile.open(fileobj=io.BytesIO(payload), mode='r:gz') as archive:
    members = archive.getmembers()
    assert len(members) == 2 and {m.name for m in members} == {n.lstrip('/') for n in files}
    for entry in members:
        assert entry.isfile() and entry.uid == entry.gid == 0 and entry.mode == 0o600
        assert archive.extractfile(entry).read() == files['/' + entry.name]
out = PRIVATE / 'r8-candidate'
out.mkdir(exist_ok=True)


def freeze(name, raw):
    path = out / name
    if path.exists():
        assert path.read_bytes() == raw, 'New bytes require a new revision: ' + name
    else:
        path.write_bytes(raw)


freeze('manifest.json', manifest)
freeze('samurai-mp2650.ko', module)
freeze('thermal-bands-payload.tar.gz', payload)
report = dict(phase='offline-payload-preparation', installed=False,
              old_manifest_sha256=sha(old_raw), new_manifest_sha256=sha(manifest),
              payload_sha256=sha(payload), payload_bytes=len(payload),
              changed_files={name: dict(sha256=sha(raw), mode='0o600') for name, raw in files.items()},
              source_build_receipt_sha256=sha(receipt_raw),
              source_test_receipt_sha256=sha(tests_raw),
              service_usb_protection_boot_unchanged=True,
              source_budget_caps_unchanged=True,
              runtime_validation_pending=True, phone_accessed=False)
report_raw = (json.dumps(report, indent=2) + '\n').encode()
freeze('payload-result.json', report_raw)
(REF / 'r8-payload-result.json').write_bytes(report_raw)
print(json.dumps(report, indent=2))
