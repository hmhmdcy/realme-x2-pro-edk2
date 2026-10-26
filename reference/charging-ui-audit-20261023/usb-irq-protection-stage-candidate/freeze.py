"""Local-only source/receipt freeze. Never binds a future runtime identity."""
from pathlib import Path
import ast
import hashlib
import json

HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def need(ok, message):
    if not ok:
        raise RuntimeError(message)

def save(name, value):
    raw = (json.dumps(value, indent=2) + '\n').encode()
    path = HERE / name
    if path.exists():
        need(path.read_bytes() == raw, 'new revision required: ' + name)
    else:
        with path.open('xb') as stream:
            stream.write(raw)

worker = HERE / 'stage-worker.py'
ast.parse(worker.read_text())
tests = json.loads((HERE / 'test-result.json').read_bytes())
need(tests['passed'] and tests['actual_function_and_boundary_cases'] == 26 and
     tests['tested_files']['stage-worker.py'] == sha(worker) and
     tests['tested_files']['test-stage.py'] == sha(HERE / 'test-stage.py'), 'exact new tests/source binding')
cohort = REF / 'charging-ui-audit-20261023/usb-irq-protection-cohort-candidate'
need(sha(cohort / 'delivery.json') == '3d5b78bc4c7a6b476bfb97c2fbad3e0d76497c94e13bd755a8e4aaa0b032a07b', 'frozen real cohort')
paths = {
    'manager614': REF / 'charging-session-20261023/r8-source-integration/rootfs-sources/usr/sbin/samurai-charging',
    'OpenRC': REF / 'charging-session-20261023/r8-source-integration/rootfs-sources/etc/init.d/samurai-charging',
    'live_library': REF / 'charging-session-20261023/r8-source-integration/rootfs-sources/usr/lib/samurai-charging/live-session.py',
    'R8_update_reference': REF / 'charging-oem-audit-20261023/r8-update/update-r8.py',
    'R7_atomic_reference': REF / 'charging-session-20261023/source-stage-r7/stage-r7.py',
    'Image502_adoption_reference': REF / 'charging-oem-audit-20261023/image502-adoption-candidate/adopt.py',
    'Image502_collector_reference': REF / 'charging-oem-audit-20261023/image502-postboot-readonly/device.py',
    'cohort_delivery': cohort / 'delivery.json', 'cohort_identity': cohort / 'cohort-manifest.json',
    'cohort_manifest': cohort / 'manifest.json',
}
need(sha(paths['manager614']) == '61451ffea87cca466dbbb2f1a2c6e7c05d0eee517479e8b019d43b1869355aa4', 'actual manager614')
need(sha(paths['OpenRC']) == 'bfed48ebbcaced5f017110564045eef500a88f12fefe7ebff6d1e74cabfe570a', 'actual OpenRC')
save('source-pins.json', {name: {'path': str(path), 'sha256': sha(path)} for name, path in paths.items()})
save('local-check-result.json', {'passed': True, 'worker_sha256': sha(worker),
     'default_check_only_actual_returncode': tests['default_check_only_returncode'],
     'source_AST_valid': True, 'device_or_storage_or_SDK_or_Git_accessed': False,
     'real_adoption_request_lease_guard_created': False,
     'source_only_boundary': 'default command and new fake-boundary tests only; no actual device stage'})
names = ['stage-worker.py', 'contract.json', 'README.md', 'test-stage.py', 'test-result.json',
         'source-pins.json', 'local-check-result.json', 'freeze.py', 'history/test-01-windows-fake-path.json']
delivery = {'schema': 'samurai-usb-irq-protection-stage-delivery-v1', 'passed': True, 'frozen': True,
            'files': {name: {'sha256': sha(HERE / name), 'bytes': (HERE / name).stat().st_size} for name in names},
            'worker_sha256': sha(worker), 'contract_sha256': sha(HERE / 'contract.json'),
            'test_receipt_sha256': sha(HERE / 'test-result.json'), 'actual_new_boundary_cases': 26,
            'default_check_only': True, 'actual_device_stage_or_request_created': False,
            'cohort_delivery_sha256': '3d5b78bc4c7a6b476bfb97c2fbad3e0d76497c94e13bd755a8e4aaa0b032a07b',
            'payload_sha256': '9dee06ddea1190ea70a188efe47742afb8b104bf53ac31cb57598f079ee4fb3c',
            'prepared_Image502_transaction_modified': False, 'kernel_or_old_tests_rerun': False,
            'source_boot_only_acceptance': 'actual adopted #502, boot97811/logdumpace2, R8 old disk and three old resident notes',
            'success_only': 'staged/runtime_pending; no runtime activation or MAC evidence capture',
            'future_restart_context_reusable': False}
save('delivery.json', delivery)
print(json.dumps({'passed': True, 'worker_sha256': sha(worker), 'contract_sha256': sha(HERE / 'contract.json'),
                  'delivery_sha256': sha(HERE / 'delivery.json'), 'test_receipt_sha256': sha(HERE / 'test-result.json')}))
