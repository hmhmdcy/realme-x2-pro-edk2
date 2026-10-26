"""Freeze the tested, privately built Full kernel candidate for offline review."""
from pathlib import Path
import hashlib
import json
import shutil
import sys

ref = Path(__file__).resolve().parent
revision = int(sys.argv[1]) if len(sys.argv) > 1 else 1
assert revision in (1, 2)
v1 = ref.parent / 'charging-session-20261023/full-integration-candidate'
candidate = v1 if revision == 1 else ref.parent / 'charging-session-20261023/kernel-v2'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
build_receipt = ref / ('oem-full-build-result.json' if revision == 1 else 'oem-full-v2-build-result.json')
receipt = json.loads(build_receipt.read_text())
assert receipt['passed'] and not receipt['installed']
assert sha(candidate / 'test-result.json') == receipt['test_receipt_sha256']
module = Path(receipt['module'])
assert sha(module) == receipt['module_sha256']
assert sha(ref / 'samurai-mp2650.c') == receipt['main_r5_source_sha256']
for name, expected in receipt['sources'].items():
    assert sha(candidate / name) == expected, name
dest = Path('/mnt/e/edk2-samurai-out/charging-management-20261023/oem-full-candidate') / ('kernel-v' + str(revision))
dest.mkdir(parents=True, exist_ok=True)
if (dest / 'snapshot.json').exists():
    previous = json.loads((dest / 'snapshot.json').read_text())
    assert previous['sources'] == receipt['sources'], 'Use a new revision directory'
    assert previous['module_sha256'] == receipt['module_sha256'], 'Use a new revision directory'
sources = dest / 'sources'
sources.mkdir(exist_ok=True)
for name in receipt['sources']:
    shutil.copy2(candidate / name, sources / name)
shutil.copy2(module, dest / module.name)
shutil.copy2(build_receipt, dest / 'build-result.json')
shutil.copy2(candidate / 'test-result.json', dest / 'test-result.json')
shutil.copy2(Path(receipt['private_build']).parent / 'build.log', dest / 'build.log')
userspace_hashes = {}
if revision == 2:
    userspace = v1 / 'userspace'
    user_receipt = json.loads((userspace / 'test-result.json').read_text())
    assert user_receipt['passed'] and user_receipt['revision'] == 2
    assert all(user_receipt['main_unchanged'].values())
    for name, expected in user_receipt['baseline'].items():
        assert sha(ref / name) == expected, 'Deployed user-space baseline changed: ' + name
    (dest / 'userspace').mkdir(exist_ok=True)
    for name, expected in user_receipt['candidate_files'].items():
        assert sha(userspace / name) == expected, name
        shutil.copy2(userspace / name, dest / 'userspace' / name)
        userspace_hashes[name] = expected
    for name in ['test-result.json', 'userspace.patch', 'README.md']:
        shutil.copy2(userspace / name, dest / 'userspace' / name)
    shutil.copy2(candidate / 'full-integration.patch', dest / 'kernel-v1-to-v2.patch')
    shutil.copy2(v1 / 'full-integration.patch', dest / 'r5-to-kernel-v1.patch')
recovery_path = ref / 'pm-r5-recovery-result.json'
recovery = json.loads(recovery_path.read_text()) if recovery_path.exists() else {}
status = {
    'kind': 'offline-charging-review-candidate', 'revision': revision,
    'deployed': False, 'installation_authorized_by_snapshot': False,
    'kernel_build_verified': True, 'module_sha256': sha(dest / module.name),
    'sources': receipt['sources'],
    'test_receipt_sha256': receipt['test_receipt_sha256'],
    'build_receipt_sha256': sha(dest / 'build-result.json'),
    'candidate_device_health_verified': False,
    'pm_r5_terminal_recovered': bool(recovery.get('restored') and recovery.get('worker_exited')),
    'separate_r5_recovery_receipt_sha256': sha(recovery_path) if recovery else None,
    'physical_icon_latency_verified': False,
    'userspace_compatibility_included': bool(userspace_hashes),
    'userspace_sha256': userspace_hashes,
    'pending': (['user-space compatibility review', 'OEM caller gating review'] if revision == 1 else []) +
               ['coordinated deployment and hardware Full/recharge validation',
                'physical icon event timing', 'planned RTC and USB resume validation'],
}
(dest / 'snapshot.json').write_text(json.dumps(status, indent=2) + '\n')
(dest / 'README.txt').write_text(
    'Offline review only. This directory has no installer.\n'
    'Kernel source, tests and private k363 in-tree W=1 module match by SHA256.\n'
    'This candidate has never been deployed or hardware validated.\n'
    'The existing phone r5 was recovered separately; planned RTC and icon timing remain unaccepted.\n'
    'Do not treat this snapshot as a deployment or acceptance baseline.\n')
print(json.dumps({'path': str(dest), **status}, indent=2))
