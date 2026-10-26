"""Execute the real r6 transaction, fake only file/service/kernel/process edges."""
from pathlib import Path
import base64
import copy
import hashlib
import importlib.util
import io
import json
import os
import stat
import subprocess
import tarfile
import tempfile
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
MAIN = ROOT / 'reference/charging-management-20261023'
PRIVATE = ROOT.parent / 'edk2-samurai-out/charging-management-20261023'
spec = importlib.util.spec_from_file_location('r6_update', HERE / 'update-r6.py')
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

payload = (PRIVATE / 'r6-candidate/r5-to-r6-payload.tar.gz').read_bytes()
request = {'transaction': 'charging-update-r6', 'guard': u.GUARD,
           'identity': {'boot_id': 'explicit-test-boot', 'serial_sha256': u.sha(b'test-serial'), 'compatible_sha256': u.sha(b'test-compatible')},
           'window_token': 'new-r6-exclusive-window-unique-0001', 'old_manifest_sha256': u.OLD,
           'new_manifest_sha256': u.NEW, 'payload_sha256': u.PAYLOAD,
           'payload_base64': base64.b64encode(payload).decode()}
newfiles, newmeta = u.unpack_request(request)
oldraw = (PRIVATE / 'r5-deployed-snapshot/manifest.json').read_bytes()
oldmeta = json.loads(oldraw)
oldfiles = {u.MANIFEST: oldraw}
with tarfile.open(PRIVATE / 'r5-deployed-snapshot/samurai-charging-payload.tar.gz') as archive:
    for name in [u.KO, u.SERVICE]:
        oldfiles[name] = archive.extractfile(name.lstrip('/')).read()
assert u.sha(oldraw) == u.OLD
for name in [u.KO, u.SERVICE]:
    assert u.sha(oldfiles[name]) == oldmeta['installed_files'][name], name

# This actual production receipt is the baseline fixture, including the exact
# telemetry keys. Only r6's new fields are added, rather than invented aliases.
baseline_sample = json.loads((MAIN / 'charger-update-result.json').read_text())['sample']
assert 'session_seconds' in baseline_sample and 'session_s' not in baseline_sample


class Fake:
    def __init__(self, failures=(), full=False):
        self.files = {n: (b, u.MODES[n]) for n, b in oldfiles.items()}
        self.events = []
        self.count = {}
        self.failures = set(failures)
        self.loaded = 'old'
        self.running = True
        self.started_marker = True
        self.uncertain = False
        self.child = None
        self.created = False
        self.closed = False
        self.new_full = full
        self.invalid = {}
        self.old_invalid = {}
        self.old_after_stop_invalid = {}
        self.after_limits = {}
        self.camera_changed = False
        self.recovery_started = False

    def edge(self, name):
        self.events.append(name)
        self.count[name] = self.count.get(name, 0) + 1
        key = '%s:%d' % (name, self.count[name])
        if key in self.failures:
            raise RuntimeError('injected ' + key)
        if 'uncertain:' + key in self.failures:
            self.uncertain = True
            raise u.MutationUncertain('pending child at ' + key)

    def begin(self, req):
        self.edge('begin')
        assert req['identity'] == request['identity']
        self.check_window(req)
        self.edge('lock')
        if self.created:
            raise FileExistsError('r6 directory already exists')
        self.created = True

    def check_window(self, req):
        self.edge('window')
        assert req['window_token'] == request['window_token']

    def read_owned(self, name):
        self.edge('read:' + name)
        return self.files[name]

    def manager(self, service_hash):
        self.edge('fresh-manager:' + service_hash)
        assert u.sha(self.files[u.SERVICE][0]) == service_hash
        # Distinct objects preserve actual generation rather than just one
        # dictionary whose fake verify result follows the current filesystem.
        return {'service_hash': service_hash, 'generation': 'new' if service_hash == u.HASHES[u.SERVICE] else 'old',
                'id': len(self.events)}

    def manager_for_stop(self):
        return self.manager(u.sha(self.files[u.SERVICE][0]))

    def verify(self, manager):
        self.edge('verify:' + manager['generation'])
        assert manager['service_hash'] == u.sha(self.files[u.SERVICE][0])
        meta = json.loads(self.files[u.MANIFEST][0])
        assert meta['installed_files'][u.SERVICE] == manager['service_hash']
        assert meta['installed_files'][u.KO] == u.sha(self.files[u.KO][0])
        return meta

    def notes_match(self, manager, meta):
        self.edge('notes:' + manager['generation'])
        assert self.loaded == manager['generation']
        assert meta['modules']['samurai-mp2650']['sha256'] == u.sha(self.files[u.KO][0])

    def registers(self):
        self.edge('registers')
        return self.observation()['registers']

    def observation(self):
        sample = copy.deepcopy(baseline_sample)
        sample['desired_enable'] = int(self.running)
        if self.loaded == 'new':
            sample.update(gauge_current_ua=50000, logical_full=0, full_holding=0, hold_requested=0,
                          full_cause=0, sw_full_count=0, recharge_count=0, gauge_charge_stop=0)
            sample.update(self.invalid)
            if self.new_full and self.running:
                sample.update(logical_full=1, full_holding=1, hold_requested=1, full_cause=1,
                              desired_enable=0, session_seconds=0)
        else:
            sample.update(self.old_invalid)
            if not self.running:
                sample.update(self.old_after_stop_invalid)
        limits = {'native_ua': 100000, 'input_ua': 100000, 'charge_ua': 250000, 'cv_uv': 4362500}
        if self.loaded == 'new':
            limits.update(self.after_limits)
        bits08 = 8 if not self.running else (0 if sample.get('full_holding') else 0x10)
        if 'bad-stop-readback' in self.failures and not self.running:
            bits08 = 0x10
        return {'state': {'boot_id': 'explicit-test-boot', 'release': u.RELEASE, 'taint': '0',
                          'camera_pm': {'icp': 'suspended'}, 'm2m': 'idle' if not (self.loaded == 'new' and self.camera_changed) else 'changed',
                          'services': [{'pid': 3, 'comm': 'phosh', 'uid': 1000}]},
                'sample': sample, 'limits': limits,
                'registers': {'00': limits['input_ua'] // 50000, '0f': limits['input_ua'] // 50000,
                              '02': limits['charge_ua'] // 50000, '08': bits08, '04': 104},
                'notes': {'samurai-usb-input': 'usb-resident-note', 'samurai-gauge-protection': 'protection-resident-note',
                          'samurai-mp2650': self.loaded}, 'openrc_started': self.started_marker}

    def observe(self, manager):
        self.edge('observe:' + self.loaded)
        return self.observation()

    def manager_command(self, manager, meta, action):
        self.edge(action + ':' + manager['generation'])
        assert manager['service_hash'] == u.sha(self.files[u.SERVICE][0]), 'stale in-memory manager executed'
        if action == 'stop':
            self.running = False
        else:
            assert self.loaded == manager['generation']
            self.running = True
            self.recovery_started |= self.loaded == 'old'

    def backup(self, files, before):
        self.edge('backup')
        assert files == self.files
        self.saved = copy.deepcopy(files)

    def module_present(self):
        self.edge('present')
        return self.loaded is not None

    def module_state(self):
        self.edge('module-state')
        return 'live' if self.loaded else 'absent'

    def unload(self):
        self.edge('unload')
        assert self.running is False, 'unload without synchronous stop'
        self.loaded = None

    def replace(self, name, content, mode):
        suffix = 'new' if content == newfiles[name] else 'old'
        self.edge('write:' + Path(name).name + ':' + suffix)
        assert self.loaded is None
        assert mode == u.MODES[name]
        self.files[name] = (content, mode)

    def load(self, path):
        assert path == u.KO
        generation = 'new' if self.files[u.KO][0] == newfiles[u.KO] else 'old'
        self.edge('load:' + generation)
        assert self.loaded is None
        self.loaded = generation
        self.running = False

    def finish(self, result):
        self.edge('finish')
        self.result = copy.deepcopy(result)

    def close(self):
        self.closed = True


cases = []
def execute(name, fake=None, req=None):
    f = fake or Fake()
    result = u.update(req or copy.deepcopy(request), f)
    assert f.closed and result == f.result
    cases.append({'name': name, 'passed': True, 'update_passed': result['passed'],
                  'phase': (result.get('primary_error') or {}).get('phase'),
                  'recovery_state': result['recovery_state']})
    return result, f


normal, f = execute('normal-managed')
assert normal['passed'] and f.loaded == 'new' and f.running
assert f.files == {n: (b, u.MODES[n]) for n, b in newfiles.items()}
assert f.events.index('stop:old') < f.events.index('unload') < f.events.index('load:new') < f.events.index('verify:new') < f.events.index('start:new')
assert 'start:old' not in f.events
full, f = execute('precise-full-holding', Fake(full=True))
assert full['passed'] and full['accepted_state'] == 'full_holding'
assert full['sample']['session_seconds'] == 0 and 'session_s' not in full['sample']

for key, value in [('latched', 1), ('fault', 1), ('cycle_timeout', 1), ('error', -5), ('age_ms', 3001),
                   ('flags', 0x40c0), ('flags', 0x80c0), ('protection_ok', 0), ('source_inhibit', 1)]:
    fake = Fake(); fake.old_invalid[key] = value
    result, f = execute('preflight-reject-' + key + '-' + str(value), fake)
    assert not result['passed'] and result['primary_error']['phase'] == 'preflight'
    assert 'stop:old' not in f.events and 'unload' not in f.events

for edge in ['begin:1', 'window:1', 'lock:1', 'verify:old:1', 'notes:old:1', 'backup:1']:
    result, f = execute('preflight-edge-' + edge, Fake([edge]))
    assert not result['passed'] and 'unload' not in f.events

fake = Fake(); fake.created = True
result, f = execute('reject-directory-replay', fake)
assert not result['passed'] and 'stop:old' not in f.events
fake = Fake(); fake.started_marker = False
result, f = execute('reject-openrc-not-started', fake)
assert not result['passed'] and 'stop:old' not in f.events
fake = Fake(); fake.files[u.SERVICE] = (fake.files[u.SERVICE][0], 0o600)
result, f = execute('reject-service-mode600', fake)
assert not result['passed'] and 'stop:old' not in f.events

for field, value in [('transaction', 'charging-update-r5'), ('payload_sha256', '0' * 64),
                     ('old_manifest_sha256', '0' * 64), ('payload_base64', base64.b64encode(payload[:-1]).decode())]:
    req = copy.deepcopy(request); req[field] = value
    result, f = execute('reject-request-' + field, req=req)
    assert not result['passed'] and 'begin' not in f.events

for failure in ['stop:old:1', 'bad-stop-readback']:
    result, f = execute('old-stop-must-not-unload-' + failure, Fake([failure]))
    assert result['stop_error'] and 'unload' not in f.events
    assert f.files == {n: (b, u.MODES[n]) for n, b in oldfiles.items()}

for key, value in [('latched', 1), ('cycle_timeout', 1), ('fault', 1)]:
    fake = Fake(); fake.old_after_stop_invalid[key] = value
    result, f = execute('new-fault-during-old-stop-retains-module-' + key, fake)
    assert not result['passed'] and result['primary_error']['phase'] == 'old-stop-check'
    assert f.loaded == 'old' and not f.running and 'unload' not in f.events
    assert result['old_stopped_sample'][key] == value

# Every actual mutation/load/verify/start boundary has a failure before its
# completion. Rollback uses the original modes and fresh restored r5 service.
for failure in ['unload:1', 'window:2', 'write:samurai-mp2650.ko:new:1', 'write:samurai-charging:new:1',
                'write:manifest.json:new:1', 'load:new:1',
                'fresh-manager:' + u.HASHES[u.SERVICE] + ':1', 'verify:new:1', 'notes:new:1', 'start:new:1']:
    result, f = execute('recover-boundary-' + failure, Fake([failure]))
    assert not result['passed'] and result['recovery_error'] is None, (failure, result)
    assert f.files == {n: (b, u.MODES[n]) for n, b in oldfiles.items()}, failure
    assert f.loaded == 'old' and f.running and f.recovery_started, (failure, result)
    assert result['recovery_state'] == 'r5-managed-current-source-budget'

for key, value in [('latched', 1), ('fault', 1), ('cycle_timeout', 1), ('error', -5), ('age_ms', 3001),
                   ('flags', 0x40c0), ('thermal_inhibit', 1), ('gauge_charge_stop', 1)]:
    fake = Fake(); fake.invalid[key] = value
    result, f = execute('new-fault-holds-recovered-r5-' + key, fake)
    assert not result['passed'] and result['recovery_error'] is None
    assert f.loaded == 'old' and not f.running and not f.recovery_started
    assert result['recovery_withheld_sample'][key] == value
    assert f.files == {n: (b, u.MODES[n]) for n, b in oldfiles.items()}

fake = Fake(); fake.invalid.update(logical_full=1, full_cause=1)
result, f = execute('partial-full-not-healthy', fake)
assert not result['passed'] and result['primary_error']['phase'] == 'new-acceptance'
fake = Fake(); fake.after_limits.update(native_ua=500000, input_ua=500000)
result, f = execute('legal-source-budget-change-not-stable-acceptance', fake)
assert not result['passed'] and result['recovery_error'] is None
fake = Fake(); fake.after_limits['cv_uv'] = 4375000
result, f = execute('cv-ceiling-must-not-rise', fake)
assert not result['passed']
fake = Fake(); fake.camera_changed = True
result, f = execute('camera-state-change-not-passed', fake)
assert not result['passed']

result, f = execute('new-stop-failure-no-second-unload', Fake(['verify:new:1', 'stop:new:1', 'stop:new:2']))
assert result['stop_error'] and result['recovery_error'] and f.count['unload'] == 1
assert f.loaded == 'new' and 'write:samurai-mp2650.ko:old' not in f.events
for failure in ['write:samurai-charging:old:1', 'load:old:1', 'start:old:1']:
    result, f = execute('recovery-secondary-failure-' + failure, Fake(['verify:new:1', failure]))
    assert result['primary_error']['phase'] == 'fresh-new-manager' and result['recovery_error']
    assert not result['passed'] and not f.running

for failure in ['unload:1', 'load:new:1']:
    result, f = execute('unknown-child-no-fallback-' + failure, Fake(['uncertain:' + failure]))
    assert result['mutating_process_unknown'] and not result['passed']
    assert result['terminal'] is False
    idx = next(i for i, e in enumerate(f.events) if e == failure.rsplit(':', 1)[0])
    assert f.events[idx + 1:] == ['finish'], f.events[idx:]
result, f = execute('unknown-recovery-child-no-further-stop', Fake(['verify:new:1', 'uncertain:load:old:1']))
assert result['mutating_process_unknown'] and result['recovery_error'] and not f.running
assert result['terminal'] is False
result, f = execute('unknown-module-before-recovery-stop-no-I2C-or-unload', Fake(['verify:new:1', 'uncertain:module-state:2']))
assert result['mutating_process_unknown'] and result['terminal'] is False
assert f.count['unload'] == 1 and 'stop:new' not in f.events

# Execute concrete Device filesystem, lease and process methods. No sysfs,
# I2C, module tools, service or SDK are accessed by these tests.
with tempfile.TemporaryDirectory(prefix='r6-transaction-') as temporary:
    root = Path(temporary)
    mapped = lambda *names: root / str(Path(*names)).lstrip('/')
    for name in u.MODES:
        p = mapped(name); p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(oldfiles[name]); p.chmod(u.MODES[name])
    with patch.object(u, 'Path', mapped):
        device = u.Device()
        for name in u.MODES:
            device.replace(name, newfiles[name], u.MODES[name])
            assert device.read_owned(name) == (newfiles[name], u.MODES[name])
            device.replace(name, oldfiles[name], u.MODES[name])
            assert device.read_owned(name) == (oldfiles[name], u.MODES[name])
        manager = {'_r6_code_sha256': u.HASHES[u.SERVICE], 'verify': lambda: newmeta,
                   'command': lambda meta, action: (_ for _ in ()).throw(AssertionError('must never execute stale code'))}
        for call in [lambda: device.verify(manager), lambda: device.manager_command(manager, newmeta, 'start')]:
            try:
                call()
                raise AssertionError('accepted stale installed code generation')
            except RuntimeError:
                pass
        with patch.object(u.os, 'fsync', side_effect=OSError('injected data fsync failure')):
            try:
                device.replace(u.SERVICE, newfiles[u.SERVICE], u.MODES[u.SERVICE])
                raise AssertionError('failed atomic write accepted')
            except OSError:
                pass
        assert mapped(u.SERVICE).read_bytes() == oldfiles[u.SERVICE]
        assert not mapped(u.SERVICE).with_name('samurai-charging.r6-next').exists()
    cases.append({'name': 'actual-atomic-write-service755-module600-rollback', 'passed': True})
    cases.append({'name': 'actual-concrete-manager-rejects-stale-verify-and-start', 'passed': True})
    cases.append({'name': 'actual-failed-data-fsync-keeps-old-service-and-cleans-own-temp', 'passed': True})

    state_file = mapped('/sys/module/samurai_mp2650/initstate')
    state_file.parent.mkdir(parents=True, exist_ok=True)
    with patch.object(u, 'Path', mapped):
        for value in ['coming', 'going']:
            state_file.write_text(value)
            device = u.Device()
            try:
                device.module_state()
                raise AssertionError('transient module accepted')
            except u.MutationUncertain:
                pass
            assert device.uncertain
    cases.append({'name': 'actual-coming-going-module-is-unknown-and-not-live', 'passed': True})

    lease = {'transaction': 'charging-update-r6', 'owner': 'charging', 'camera_released': True,
             'exclusive': True, 'token': request['window_token'], 'boot_id': 'explicit-test-boot',
             'expires_boottime_s': 200}
    for name in [u.WINDOW, u.GUARD, '/proc/sys/kernel/random/boot_id']:
        p = mapped(name); p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(lease) if name == u.WINDOW else 'explicit-test-boot\n'); p.chmod(0o600)
    with patch.object(u, 'Path', mapped), patch.object(u.time, 'clock_gettime', return_value=100):
        device.check_window(request)
        for change in [{'camera_released': False}, {'expires_boottime_s': 99}, {'token': 'other-window'}, {'boot_id': 'other-boot'}]:
            bad = dict(lease, **change); mapped(u.WINDOW).write_text(json.dumps(bad))
            try:
                device.check_window(request)
                raise AssertionError('accepted bad lease')
            except RuntimeError:
                pass
    cases.append({'name': 'actual-lease-boot-token-expiry-camera-record', 'passed': True})

class Pending:
    pid = 123
    def communicate(self, timeout):
        assert timeout == 30
        raise subprocess.TimeoutExpired('insmod', timeout)
    def poll(self):
        return None

device = u.Device()
with patch.object(u.subprocess, 'Popen', return_value=Pending()) as popen:
    try:
        device.mutate_command('insmod', u.KO)
        raise AssertionError('timeout accepted')
    except u.MutationUncertain:
        pass
    assert device.uncertain and device.child.pid == 123
    try:
        device.mutate_command('rmmod', 'samurai_mp2650')
        raise AssertionError('mutated with pending child')
    except RuntimeError:
        pass
    assert popen.call_count == 1
cases.append({'name': 'actual-popen-timeout-retains-child-and-forbids-follow-up-mutation', 'passed': True})

# Receipt hashes cover real imported updater/test and frozen predecessors.
frozen = {}
for directory in [HERE.parent / 'kernel-v2', HERE.parent / 'full-integration-candidate']:
    receipt = json.loads((directory / 'test-result.json').read_text())
    for name, expected in receipt['candidate_files'].items():
        assert digest(directory / name) == expected, name
    frozen[directory.name] = digest(directory / 'test-result.json')
result = {'passed': True, 'cases': len(cases), 'sequences': cases,
          'scope': 'actual transaction and concrete atomic-write/lease/timeout methods; fake hardware and process boundaries only',
          'candidate_files': {p.name: digest(p) for p in [HERE / 'update-r6.py', HERE / 'test-update-r6.py']},
          'main_updater_sha256': digest(MAIN / 'update-charger.py'),
          'main_service_sha256': digest(MAIN / 'samurai-charging.py'),
          'payload_sha256': u.sha(payload), 'old_manifest_sha256': u.sha(oldraw),
          'new_manifest_sha256': u.sha(newfiles[u.MANIFEST]), 'frozen_kernel_receipts': frozen,
          'phone_accessed': False, 'sdk_accessed': False, 'installed': False}
result['tested_files'] = dict(result['candidate_files'])
(HERE / 'test-result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'passed': True, 'cases': len(cases), 'candidate_files': result['candidate_files']}, indent=2))
