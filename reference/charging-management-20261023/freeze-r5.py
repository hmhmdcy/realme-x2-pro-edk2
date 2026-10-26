"""Freeze the deployed r5 files for packaging; PM acceptance stays pending.

No phone, shared source mutation, flashing, installation or PM operation.
"""
from pathlib import Path
import hashlib
import json
import shutil
import tarfile

ref = Path(__file__).resolve().parent
private = Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
out = private / 'r5-deployed-snapshot'
out.mkdir(exist_ok=True)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
build = json.loads((ref / 'integrated-build-result.json').read_text())
installed = json.loads((ref / 'charger-update-result.json').read_text())
payload_receipt = json.loads((ref / 'service-payload-result.json').read_text())
manifest_path = private / 'service/manifest.json'
payload = private / 'service/samurai-charging-payload.tar.gz'
manifest = json.loads(manifest_path.read_text())
assert installed['passed'] and installed['terminal']
assert sha(manifest_path) == installed['new_manifest_sha256'] == payload_receipt['manifest_sha256']
assert sha(payload) == payload_receipt['payload_sha256']
for name, digest in build['sources'].items(): assert sha(ref / name) == digest, name
for name, entry in build['modules'].items():
    assert sha(Path(entry['path'])) == manifest['modules'][name]['sha256'] == entry['sha256'], name
integration = json.loads((ref.parent / 'charging-session-20261023/integration-test-result.json').read_text())
assert integration['passed']
for name, digest in integration['production_files'].items(): assert sha(ref / name) == digest, name
expected = dict(manifest['installed_files'])
expected['/usr/share/samurai-charging/manifest.json'] = sha(manifest_path)
with tarfile.open(payload) as archive:
    assert len(archive.getmembers()) == 8
    for member in archive:
        assert member.isfile() and hashlib.sha256(archive.extractfile(member).read()).hexdigest() == expected['/' + member.name]
for p in [manifest_path, payload]: shutil.copy2(p, out / p.name)
facts = {
    'revision': 'r5-deployed-before-pm-check', 'manifest_sha256': sha(manifest_path),
    'payload_sha256': sha(payload), 'modules': manifest['modules'],
    'deployment_receipt_sha256': sha(ref / 'charger-update-result.json'),
    'runtime_notification_receipt_sha256': sha(ref / 'runtime-notification-result.json'),
    'deployment_and_inhibit_auto_verified_before_pm': True,
    'current_device_health_verified': False,
    'pm_r5_terminal_recovered': False,
    'pm_r5_acceptance': 'pending: USB unreachable; preserve and recover original transaction',
    'physical_icon_acceptance': False,
    'usb500_accepted': False,
    'packaging_is_offline_and_does_not_authorize_deployment': True,
    'notes': 'V3 delivery.json is historical. Do not install a new package or repeat PM until device recovery is complete.'}
(out / 'snapshot.json').write_text(json.dumps(facts, indent=2) + '\n')
print(json.dumps(facts, indent=2))
