"""One newly found terminal boundary, using the author's actual functions.

No transport, process control, module operation or real sysfs is permitted.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import types
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
AUTHOR = HERE.parents[1] / 'charging-oem-audit-20261023/apsd-usbin-init-host-candidate'
sha = lambda raw: hashlib.sha256(raw).hexdigest()
raw = {n: (AUTHOR / n).read_bytes() for n in ['device.py', 'protocol.py', 'gates.py']}
for name, data in raw.items():
    (HERE / ('tested-' + name)).write_bytes(data)
protocol = types.ModuleType('protocol')
exec(compile(raw['protocol.py'], str(AUTHOR / 'protocol.py'), 'exec'), protocol.__dict__)
common = types.ModuleType('common')
common.sha = sha
common.boot_ms = lambda: 123456
common.process = lambda receipt: {'state': 'absent'}
environment = {'scope': 'fake reviewed environment'}
common.environment = lambda: environment
common.save = lambda path, data: Path(path).write_text(json.dumps(data))
identity_calls = []
common.identity = lambda c: identity_calls.append(c['transaction'])
observer = types.ModuleType('observer')
gates = types.ModuleType('gates')


def forbidden(*a, **k):
    raise AssertionError('no helper/control/process/transport operation allowed in absent close')


observer.helper = forbidden
with patch.dict(sys.modules, {'common': common, 'gates': gates, 'observer': observer, 'protocol': protocol}):
    device = types.ModuleType('review_device')
    device.__file__ = str(AUTHOR / 'device.py')
    exec(compile(raw['device.py'], device.__file__, 'exec'), device.__dict__)


def state(instance):
    s = {k: False for k in protocol.BOOLS}
    s.update({k: 0 for k in protocol.INTS})
    s.update(schema=1, instance=instance, phase='timeout', op=1, armed=True,
             can_unload=True, error=-110, started_boottime_ms=1000,
             deadline_boottime_ms=61000, now_boottime_ms=61001)
    s.update({k: [0] * 8 for k in ['first', 'pre', 'post', 'saved']})
    return protocol.parse(s, instance)


def fixture(root):
    bundle = root / 'bundle'; capture = bundle / 'capture'; capture.mkdir(parents=True)
    c = {'bundle': str(bundle), 'capture': str(capture), 'transaction': 'usbin-init-review-expired',
         'token': 'offline-token', 'expected_boot': 'offline-boot', 'instance': '0123456789abcdef'}
    runtime = b'offline only'; (bundle / 'test-runtime.bin').write_bytes(runtime)
    c['files'] = {'test-runtime.bin': sha(runtime)}
    def save(name, data):
        (bundle / name).write_text(json.dumps(data))
    save('request-private.json', c); save('environment-before-private.json', environment)
    save('uncertain.json', {'operation': 'close-expired', 'reason': 'response lost after unload'})
    for name, pid in [('load', 900001), ('unload', 900002), ('observer', 900003)]:
        save(name + '-process.json', {'pid': pid, 'start_ticks': 100, 'argv': ['offline-' + name]})
    (capture / 'status.json').write_text(json.dumps({'terminal': True, 'active': False,
        'transaction': c['transaction'], 'token': c['token']}))
    (capture / 'capture-private.json').write_text(json.dumps({'monitor': {
        'started': True, 'errors': [], 'dbus_returncode': 0}}))
    (capture / 'result.json').write_text('{}')
    save('close-expired-intent.json', {'state': state(c['instance']), 'fresh': True})
    device.OWNER = root / 'owner.json'
    device.OWNER.write_text(json.dumps({k: c[k] for k in ['transaction', 'token', 'expected_boot']}))
    real_path = Path
    def safe_path(*parts):
        p = real_path(*parts)
        return root / 'fake-sys' / p.relative_to('/sys') if p == real_path('/sys') or real_path('/sys') in p.parents else p
    device.Path = safe_path
    device.command = device.stop_observer = device.success_evidence = forbidden
    return c


cases = []
with tempfile.TemporaryDirectory(prefix='usbin-expired-review-', dir=HERE) as temp:
    c = fixture(Path(temp))
    incoming = dict(c, terminal_state_confirmed=True, host_unknown_sha256='retained-host-error-digest')
    intent = Path(c['bundle']) / 'close-expired-intent.json'
    saved = json.loads(intent.read_text())
    bad = json.loads(intent.read_text()); bad['state']['instance'] = '1123456789abcdef'
    intent.write_text(json.dumps(bad))
    try: device.qualification(c, incoming)
    except ValueError: cases.append('wrong-instance absent-expiry receipt rejected')
    else: raise AssertionError('wrong instance accepted')
    assert device.OWNER.exists()
    intent.write_text(json.dumps(saved))
    proof = device.qualification(c, incoming)
    assert proof['next_action'] == 'close-expired' and proof['module_already_absent']
    before_unload = list(Path(c['bundle']).glob('unload*-process.json'))
    response = device.execute('close-expired', incoming)
    assert response['finished'] and response['module_absent'] and response['no_repeated_unload']
    assert response['owner_released'] and not device.OWNER.exists()
    assert list(Path(c['bundle']).glob('unload*-process.json')) == before_unload
    assert len(identity_calls) == 1
    cases.append('unknown close-expired after successful unload qualifies and releases owner without repeated action')

assert all((AUTHOR / name).read_bytes() == data for name, data in raw.items()), 'author changed during test'
result = {'passed': True, 'cases': cases, 'tested_files': {n: sha(b) for n, b in raw.items()},
          'actual_functions': ['qualification', 'execute', 'recovery_proof', 'mutators_terminal',
                               'observer_terminal', 'protocol.parse', 'protocol.expired_zero_write'],
          'fake_boundaries': ['identity/environment', 'process receipts', 'absent sysfs', 'local runtime files'],
          'helper_or_control_or_module_action_called': False,
          'author_generator_or_suites_run': False, 'author_files_modified': False,
          'phone_ssh_usb_sdk_accessed': False}
(HERE / 'absent-expiry-result.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
print(json.dumps(result, indent=2))
