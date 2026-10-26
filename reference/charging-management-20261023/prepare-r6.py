"""Prepare the exact r5 -> r6 incremental payload offline, without device access."""
from pathlib import Path
import ast
import copy
import gzip
import hashlib
import io
import json
import tarfile

ref = Path(__file__).resolve().parent
workspace = ref.parent.parent
private = workspace.parent / 'edk2-samurai-out/charging-management-20261023'
v2 = ref.parent / 'charging-session-20261023/kernel-v2'
user = ref.parent / 'charging-session-20261023/full-integration-candidate/userspace'
sha = lambda data: hashlib.sha256(data).hexdigest()
read_json = lambda path: json.loads(path.read_text(encoding='utf-8'))
old_bytes = (private / 'r5-deployed-snapshot/manifest.json').read_bytes()
assert sha(old_bytes) == 'f1a885e2ca9c3226ca50d94f39c17c3cae5411b1047696976975df976aa971cf'
old = json.loads(old_bytes)
build = read_json(ref / 'oem-full-v2-build-result.json')
tests = read_json(v2 / 'test-result.json')
user_tests = read_json(user / 'test-result.json')
assert build['passed'] and not build['installed'] and build['intree']
assert tests['passed'] and user_tests['passed'] and user_tests['revision'] == 2
assert not build['configuration_differences']
assert sha((v2 / 'test-result.json').read_bytes()) == build['test_receipt_sha256']
for name, expected in build['sources'].items():
    assert sha((v2 / name).read_bytes()) == expected == tests['candidate_files'][name]
for name, expected in user_tests['candidate_files'].items():
    assert sha((user / name).read_bytes()) == expected
    ast.parse((user / name).read_text(encoding='utf-8'))
for name, expected in user_tests['baseline'].items():
    assert sha((ref / name).read_bytes()) == expected

module = (private / 'oem-full-candidate/kernel-v2/samurai-mp2650.ko').read_bytes()
service = (user / 'samurai-charging.py').read_bytes()
assert sha(module) == build['module_sha256']
new = copy.deepcopy(old)
new['adapter_revision'] = 'r6'
target = new['modules']['samurai-mp2650']['target']
new['modules']['samurai-mp2650']['sha256'] = sha(module)
new['installed_files'][target] = sha(module)
new['installed_files']['/usr/sbin/samurai-charging'] = sha(service)
assert {name for name in old['installed_files'] if old['installed_files'][name] != new['installed_files'][name]} == {target, '/usr/sbin/samurai-charging'}
for name in ['samurai-usb-input', 'samurai-gauge-protection']:
    assert old['modules'][name] == new['modules'][name]
for name in ['release', 'default_input_cap_ua', 'default_charge_cap_ua', 'source_budget_enforced']:
    assert old[name] == new[name]
manifest = (json.dumps(new, indent=2) + '\n').encode()
files = {target: (module, 0o600), '/usr/sbin/samurai-charging': (service, 0o755),
         '/usr/share/samurai-charging/manifest.json': (manifest, 0o600)}
tar_bytes = io.BytesIO()
with tarfile.open(fileobj=tar_bytes, mode='w') as archive:
    for name, (data, mode) in sorted(files.items()):
        info = tarfile.TarInfo(name.lstrip('/'))
        info.uid = info.gid = 0; info.uname = info.gname = 'root'
        info.size = len(data); info.mode = mode; info.mtime = 0
        archive.addfile(info, io.BytesIO(data))
compressed = io.BytesIO()
with gzip.GzipFile(filename='', mode='wb', fileobj=compressed, mtime=0) as stream:
    stream.write(tar_bytes.getvalue())
payload = compressed.getvalue()
with tarfile.open(fileobj=io.BytesIO(payload), mode='r:gz') as archive:
    members = archive.getmembers()
    assert {m.name for m in members} == {n.lstrip('/') for n in files}
    for m in members:
        data, mode = files['/' + m.name]
        assert m.isfile() and m.uid == m.gid == 0 and m.mode == mode
        assert archive.extractfile(m).read() == data

out = private / 'r6-candidate'
out.mkdir(exist_ok=True)
def freeze(name, data):
    path = out / name
    if path.exists():
        assert path.read_bytes() == data, 'Changed content requires a new candidate revision: ' + name
    else:
        path.write_bytes(data)
freeze('manifest.json', manifest)
freeze('r5-to-r6-payload.tar.gz', payload)
report = {'phase': 'offline-preparation', 'installed': False,
          'old_manifest_sha256': sha(old_bytes), 'new_manifest_sha256': sha(manifest),
          'payload_sha256': sha(payload), 'payload_bytes': len(payload),
          'changed_files': {n: {'sha256': sha(data), 'mode': oct(mode)} for n, (data, mode) in files.items()},
          'modules_retained': ['samurai-usb-input', 'samurai-gauge-protection'],
          'kernel_test_receipt_sha256': sha((v2 / 'test-result.json').read_bytes()),
          'kernel_build_receipt_sha256': sha((ref / 'oem-full-v2-build-result.json').read_bytes()),
          'userspace_test_receipt_sha256': sha((user / 'test-result.json').read_bytes()),
          'diagnostic_health_tool_installed': False,
          'boot_or_usb_configuration_changed': False, 'runtime_validation_pending': True}
encoded = (json.dumps(report, indent=2) + '\n').encode()
freeze('payload-result.json', encoded)
(ref / 'r6-payload-result.json').write_bytes(encoded)
print(json.dumps(report, indent=2))
