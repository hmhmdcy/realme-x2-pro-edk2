"""Actual stage/atomic/validation functions; only OS/device boundaries are fake."""
from pathlib import Path
import base64
import copy
import importlib.util
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import types

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PRIVATE = Path('E:/edk2-samurai-out/charging-management-20261023/usb-irq-protection-cohort-private-01')
spec = importlib.util.spec_from_file_location('actual_stage', HERE / 'stage-worker.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
sha = m.sha
cases = []

def check(ok, message='condition'):
    if not ok:
        raise AssertionError(message)

def rejected(call):
    try:
        call()
    except (RuntimeError, ValueError, FileExistsError):
        return
    raise AssertionError('expected rejection')

def contents(name):
    with tarfile.open(PRIVATE / name, mode='r:gz') as tar:
        return {'/' + entry.name: tar.extractfile(entry).read() for entry in tar.getmembers()}

old_bytes = contents('rollback-r8-payload.tar.gz')
new_bytes = contents('usb-irq-protection-payload.tar.gz')
request = {'schema': 'samurai-usb-irq-protection-stage-request-v1',
           'transaction_id': 'usb-irq-protection-stage-fake-00000001',
           'cohort_delivery_sha256': m.COHORT, 'payload_sha256': m.PAYLOAD,
           'payload_base64': base64.b64encode((PRIVATE / 'usb-irq-protection-payload.tar.gz').read_bytes()).decode(),
           'worker_sha256': sha((HERE / 'stage-worker.py').read_bytes()),
           'identity': {'boot_id': '00000000-0000-4000-8000-000000000001', 'version': m.VERSION,
                        'serial_sha256': '1' * 64, 'compatible_sha256': sha(b'realme,samurai\0'), 'rootfs_sha256': '3' * 64},
           'adoption': {'transaction_id': 'image502-fake-00000001',
                        'guard_path': '/var/lib/samurai/image502-fake-00000001-adopted/boot-id-private.txt',
                        'guard_sha256': sha(b'00000000-0000-4000-8000-000000000001\n'), 'postboot_raw_sha256': '4' * 64},
           'lease_token': '5' * 48}
lease = {'transaction_id': request['transaction_id'], 'boot_id': request['identity']['boot_id'],
         'token': request['lease_token'], 'owner': 'charging', 'exclusive': True,
         'camera_released': True, 'bluetooth_released': True, 'issued_boottime_s': 90, 'expires_boottime_s': 210}

class FakeFS:
    def __init__(self):
        self.files = dict(old_bytes)
        self.handles = {}
        self.serial = 0
        self.failure = None
        self.renames = []
        self.blocked = set()
        self.short_writes = False

    def reader(self, name):
        name = str(name).replace('\\', '/')
        if name in self.blocked:
            raise OSError('injected unreadable target')
        if name not in self.files:
            raise FileNotFoundError(name)
        return self.files[name], 0o600

    def target(self, name):
        name = str(name).replace('\\', '/')
        for target in m.ORDER:
            prefix = str(Path(target).with_name('.' + Path(target).name + '.')).replace('\\', '/')
            if name == target or name.startswith(prefix):
                return target
        return None

    def fail(self, target, phase):
        if self.failure == (target, phase):
            raise OSError('injected ' + phase)

    def open(self, name, flags, *mode):
        name = str(name).replace('\\', '/')
        target = self.target(name)
        if target is not None:
            self.fail(target, 'temp-open')
            if name in self.files:
                raise FileExistsError(name)
            self.files[name] = b''
            kind = 'file'
        else:
            target = self.renames[-1]
            kind = 'directory'
        self.serial += 1
        self.handles[self.serial] = (name, target, kind)
        return self.serial

    def write(self, fd, raw):
        name, target, _ = self.handles[fd]
        self.fail(target, 'temp-write')
        count = min(97, len(raw)) if self.short_writes else len(raw)
        self.files[name] += raw[:count]
        return count

    def fchmod(self, fd, mode):
        check(mode == 0o600)

    def fsync(self, fd):
        _, target, kind = self.handles[fd]
        self.fail(target, 'file-fsync' if kind == 'file' else 'directory-fsync')

    def close(self, fd):
        del self.handles[fd]

    def replace(self, source, target):
        target = str(target).replace('\\', '/')
        self.fail(target, 'rename')
        self.files[target] = self.files.pop(str(source).replace('\\', '/'))
        self.renames.append(target)
        if self.failure == (target, 'readback'):
            self.blocked.add(target)

class FakeDevice(m.Device):
    def __init__(self, full=False, cdp=False):
        super().__init__()
        self.fs = FakeFS()
        self.out = Path('/fake/device-stage')
        self.request = copy.deepcopy(request)
        self.adoption_proof_sha256 = '6' * 64
        self.logs = {}
        self.closed = False
        self.stops = 0
        self.stop_error = self.stop_bad_readback = self.preflight_error = self.expire_after_usb = False
        self.verify_new_error = self.close_error = False
        input_ua, budget = (900000, 1500000) if cdp else (500000, 500000)
        sample = {k: 0 for k in ['shadow', 'error', 'stop_error', 'latched', 'fault', 'source_inhibit',
                  'cycle_timeout', 'thermal_inhibit', 'gauge_charge_stop', 'flags', 'logical_full',
                  'hold_requested', 'full_holding', 'full_cause']}
        sample.update(valid=1, protection_ok=1, online=1, age_ms=5, session_seconds=10, temp_decic=265,
                      thermal_band=4, desired_enable=1, budget_ua=budget, pack_uv=8600000, cell1_uv=4300000, cell2_uv=4300000)
        regs = {'00': input_ua // 50000, '01': 0, '02': 5, '03': 0, '04': 0x68, '05': 0,
                '07': 0, '08': 0x10, '09': 0, '0f': input_ua // 50000, '13': 2}
        if full:
            sample.update(logical_full=1, hold_requested=1, full_holding=1, full_cause=3, desired_enable=0, session_seconds=0)
            regs['08'] = 0
        self.observation = {'read_start': 99.5, 'read_end': 99.8, 'sample': sample,
             'state': {'boot_id': request['identity']['boot_id'], 'release': m.RELEASE, 'taint': '0',
                       'driver': 'samurai-mp2650', 'registers': regs,
                       'camera_pm': {str(i): 'suspended' for i in range(4)},
                       'm2m': json.dumps({'users': 0, 'orphans': 0, 'jobs': 0, 'first_error': 0,
                                          'running': False, 'fatal': False, 'pinned': False}),
                       'services': [{'pid': i + 10, 'comm': name, 'uid': 10000}
                                    for i, name in enumerate(['phoc', 'phosh', 'pipewire', 'wireplumber'])]},
             'source': {'online': '1', 'usb_type': '[CDP]' if cdp else '[SDP]',
                        'current_max': str(budget), 'input_current_limit': '500000'},
             'limits': {'input_ua': input_ua, 'charge_ua': 250000, 'cv_pack_uv': 8725000},
             'notes': copy.deepcopy(m.OLD_NOTES), 'openrc_started': True, 'protection_health': 'Good',
             'protection': {'id': 0x2719, 'error': 0, 'safety': 0, 'pf': 0, 'operation': 0x300, 'manufacturing': 0x18}}

    def begin(self, incoming):
        m.validate_lease(lease, 0o600, incoming, self.now())
        if self.preflight_error:
            raise RuntimeError('identity mismatch')

    def now(self): return 100
    def read_owned(self, name): return self.fs.reader(name)
    def manager(self): return {'real_boundary': 'fake installed module'}
    def verify(self, manager):
        current = json.loads(self.fs.files[m.MANIFEST])
        if self.verify_new_error and sha(self.fs.files[m.MANIFEST]) == m.NEW:
            raise RuntimeError('fresh new verify failed')
        return current
    def notes_match(self, manager, meta, backups=False):
        check(self.observation['notes'] == m.OLD_NOTES)
        if backups:
            check(all(self.logs[Path(target).name + '.before'] == old_bytes[target] for target in m.ORDER))
    def verify_partitions(self): pass
    def observe(self, manager): return copy.deepcopy(self.observation)
    def backup(self, files, before):
        for name, (raw, _) in files.items(): self.logs[Path(name).name + '.before'] = raw
        self.log('before-private.json', before)
    def check_window(self, incoming):
        m.validate_lease(lease, 0o600, incoming, self.now())
        if self.expire_after_usb and self.fs.renames:
            raise RuntimeError('expired lease before next write')
    def stop(self, manager, old):
        self.stops += 1
        if self.stop_error: raise RuntimeError('original manager stop failed')
        if not self.stop_bad_readback:
            self.observation['state']['registers']['08'] = (self.observation['state']['registers']['08'] & ~0x18) | 8
        self.observation['sample']['desired_enable'] = 0
    def registers(self, manager): return self.observation['state']['registers']
    def replace(self, target, raw):
        return m.atomic_replace(target, raw, self.request['transaction_id'], m.OLD_FILES[target],
                                self.event, ops=self.fs, reader=self.read_owned)
    def log(self, name, value): self.logs[name] = copy.deepcopy(value)
    def close(self):
        self.closed = True
        if self.close_error: raise RuntimeError('injected close error')

# Windows host has no Linux O_NOFOLLOW; its flag is an explicit fake OS boundary.
m.os = types.SimpleNamespace(O_WRONLY=os.O_WRONLY, O_RDONLY=os.O_RDONLY, O_CREAT=os.O_CREAT,
                             O_EXCL=os.O_EXCL, O_NOFOLLOW=getattr(os, 'O_NOFOLLOW', 0))

for full, cdp in [(False, False), (True, True)]:
    d = FakeDevice(full=full, cdp=cdp)
    result = m.stage(request, d, execute=True)
    check(result['staged'] and result['status'] == 'staged/runtime_pending' and result['runtime_pending'] and
          result['disk_state'] == 'all_new_fsynced' and d.fs.renames == m.ORDER and d.stops == 1 and d.closed, json.dumps(result))
    check(all(d.fs.files[name] == new_bytes[name] for name in m.ORDER) and result['old_resident_notes'] == m.OLD_NOTES)
    cases.append('actual stage success ' + ('Full/CDP900' if full else 'managed/SDP500'))

for kind in ['stop_error', 'stop_bad_readback']:
    d = FakeDevice()
    setattr(d, kind, True)
    result = m.stage(request, d, execute=True)
    check(not result['staged'] and not result['stop_verified'] and result['stop_error'] and not d.fs.renames and d.stops == 1)
    check(all(d.fs.files[name] == old_bytes[name] for name in m.ORDER) and d.closed)
    cases.append('stop failure zero replacement: ' + kind)

for target in m.ORDER:
    for phase in ['temp-write', 'file-fsync', 'rename', 'directory-fsync']:
        d = FakeDevice()
        d.fs.failure = (target, phase)
        result = m.stage(request, d, execute=True)
        check(not result['staged'] and result['stop_verified'] and result['primary_error']['atomic_stage'] == phase and d.closed)
        index = m.ORDER.index(target)
        expected = m.ORDER[:index + (phase == 'directory-fsync')]
        check(d.fs.renames == expected and all(d.fs.files[name] == old_bytes[name] for name in m.ORDER[index + 1:]))
        check(result['automatic_rollback_or_replay'] is False and result['final_files'] and not d.fs.handles)
        cases.append('actual atomic failure ' + Path(target).name + ':' + phase)

d = FakeDevice()
d.fs.failure = (m.USB, 'readback')
result = m.stage(request, d, execute=True)
check(not result['staged'] and result['unknown_write_state'] and d.fs.renames == [m.USB] and d.closed)
cases.append('renamed target unreadable: preserve unknown and do not advance/rollback')

for attr in ['expire_after_usb', 'verify_new_error', 'close_error', 'preflight_error']:
    d = FakeDevice()
    setattr(d, attr, True)
    result = m.stage(request, d, execute=True)
    check(not result['staged'] and d.closed)
    if attr == 'expire_after_usb': check(d.fs.renames == [m.USB] and result['disk_state'] == 'partial_known')
    if attr == 'verify_new_error': check(d.fs.renames == m.ORDER and result['disk_state'].startswith('all_new_known'))
    if attr == 'close_error': check(d.logs['result.json']['staged'] is False and 'close_error' in d.logs['result.json'])
    if attr == 'preflight_error': check(d.stops == 0 and not d.fs.renames)
    cases.append('ordered transaction boundary: ' + attr)

for key, value in [('expires_boottime_s', 100), ('expires_boottime_s', 211), ('issued_boottime_s', float('nan')),
                   ('exclusive', False), ('token', '0' * 48)]:
    altered = dict(lease)
    altered[key] = value
    rejected(lambda: m.validate_lease(altered, 0o600, request, 100))
cases.append('actual lease expiry/length/nonfinite/ownership rejection')

identity = {'boot_id': request['identity']['boot_id'], 'uname': {'version': m.VERSION, 'release': m.RELEASE, 'machine': 'aarch64'},
            'taint': '0', 'serial_sha256': request['identity']['serial_sha256'],
            'rootfs': {'sha256': request['identity']['rootfs_sha256']}, 'compatible_b64': base64.b64encode(b'realme,samurai\0').decode()}
proof = {'result': {'passed': True, 'read_only': True, 'hardware_writes': 0, 'errors': {}, 'checks': {k: {} for k in m.CHECKS}},
         'postboot_raw_sha256': request['adoption']['postboot_raw_sha256'],
         'raw': {'identity_before': identity, 'identity_after': copy.deepcopy(identity),
                 'boot_partition': {'sha256': m.BOOT, 'bytes': 100663296}, 'logdump_partition': {'sha256': m.LOGDUMP, 'bytes': 67108864},
                 'manifest': {'sha256': m.OLD}, 'manifest_text': old_bytes[m.MANIFEST].decode().strip(),
                 'charging_modules': {name: {'loaded_note_sha256': value} for name, value in m.OLD_NOTES.items()}}}
m.validate_adoption(proof, request)
for change in ['old_version', 'old_logdump', 'incomplete', 'wrong_postboot']:
    altered = copy.deepcopy(proof)
    if change == 'old_version': altered['raw']['identity_before']['uname']['version'] = '#501 fake'
    if change == 'old_logdump': altered['raw']['logdump_partition']['sha256'] = '0' * 64
    if change == 'incomplete': altered['result']['checks'].pop('instant_gauge')
    if change == 'wrong_postboot': altered['postboot_raw_sha256'] = '0' * 64
    rejected(lambda: m.validate_adoption(altered, request))
cases.append('actual adopted proof exact #502/carriers/nine checks; real collector stripped text accepted')

for change in ['old_kernel', 'wrong_guard', 'wrong_payload']:
    altered = copy.deepcopy(request)
    if change == 'old_kernel': altered['identity']['version'] = '#501 fake'
    if change == 'wrong_guard': altered['adoption']['guard_path'] = '/var/lib/samurai/old-r3/boot-id-private.txt'
    if change == 'wrong_payload': altered['payload_sha256'] = '0' * 64
    rejected(lambda: m.unpack(altered))
cases.append('actual request parser rejects historical kernel/guard/cohort')

with tempfile.TemporaryDirectory(prefix='samurai-stage-once-') as name:
    first = m.claim_result_dir(name)
    sentinel = first / 'sentinel'
    sentinel.write_bytes(b'old result retained')
    rejected(lambda: m.claim_result_dir(name))
    check(sentinel.read_bytes() == b'old result retained' and list(first.iterdir()) == [sentinel])
cases.append('actual exclusive result-dir claim rejects replay without changing old evidence')

q = subprocess.run([sys.executable, '-B', str(HERE / 'stage-worker.py'), '--check-only'], capture_output=True, text=True)
check(q.returncode == 0 and json.loads(q.stdout)['device_accessed'] is False)
cases.append('real default check-only process terminal rc0 without device calls')

result = {'passed': True, 'actual_function_and_boundary_cases': len(cases), 'cases': cases,
          'tested_files': {'stage-worker.py': sha((HERE / 'stage-worker.py').read_bytes()), 'test-stage.py': sha(Path(__file__).read_bytes())},
          'actual_frozen_payload_sha256': m.PAYLOAD, 'actual_frozen_old_manifest_sha256': m.OLD,
          'default_check_only_returncode': q.returncode,
          'boundary': 'actual Python transaction/atomic/lease/adoption functions; OS/device/manager edges fake; synthetic boot/proof fixtures',
          'driver_suites_compiler_storage_device_SSH_USB_SDK_Git_used': False}
(HERE / 'test-result.json').write_bytes(m.encode(result))
print(json.dumps({'passed': True, 'cases': len(cases), 'test_receipt_sha256': sha((HERE / 'test-result.json').read_bytes())}))
