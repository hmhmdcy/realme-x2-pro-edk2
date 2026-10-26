"""Directed R7/two-file migration tests; do not rerun or relabel the old 67."""
from pathlib import Path
import ast
import base64
import copy
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import tarfile
from types import SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PRIVATE = ROOT.parent / 'edk2-samurai-out/charging-management-20261023'
OLD_TEST = ROOT / 'reference/charging-session-20261023/r6-update/test-update-r6.py'
OLD_WORKER = OLD_TEST.with_name('update-r6.py')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(OLD_TEST) == 'ceadca9c49dce32d9d4202156606f675c10e28be4fff243804b232cda13fe273'
assert sha(OLD_WORKER) == 'b5cfad278a1d1887e0cb38e47edcb796929b760151e5cb5bb59e775f1e2b2e98'
spec = importlib.util.spec_from_file_location('r8_update', HERE / 'update-r8.py')
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)  # no Device/SSH/USB operation on import
payload = (PRIVATE / 'r8-candidate/thermal-bands-payload.tar.gz').read_bytes()
request = dict(transaction='charging-update-r8', guard=u.GUARD,
               identity=dict(boot_id='explicit-test-boot', serial_sha256=u.sha(b'test-serial'), compatible_sha256=u.sha(b'test-compatible')),
               window_token='new-r8-exclusive-window-unique-0001', old_manifest_sha256=u.OLD,
               new_manifest_sha256=u.NEW, payload_sha256=u.PAYLOAD,
               payload_base64=base64.b64encode(payload).decode())
newfiles, newmeta = u.unpack_request(request)
oldraw = (PRIVATE / 'r7-candidate/manifest.json').read_bytes()
oldmeta = json.loads(oldraw)
oldfiles = {u.MANIFEST: oldraw}
with tarfile.open(PRIVATE / 'r6-candidate/r5-to-r6-payload.tar.gz') as archive:
    for name in [u.KO, u.SERVICE]:
        oldfiles[name] = archive.extractfile(name.lstrip('/')).read()
assert u.sha(oldraw) == u.OLD
assert u.sha(oldfiles[u.SERVICE]) == u.SERVICE_SHA == oldmeta['installed_files'][u.SERVICE]
assert u.sha(oldfiles[u.KO]) == oldmeta['installed_files'][u.KO]
trial = PRIVATE / 'usb500-r7-18306f77ab5726a7929b99d2131242353f7a7c45a1f69e24/fetch-1792747154239432418/result.json'
actual = json.loads(trial.read_bytes())['final_observation']
baseline_sample = actual['sample']

# Reuse only the actual old Fake class, not its test program/matrix. R8 has
# the same service bytes on both sides, so generation follows the manifest.
old_ast = ast.parse(OLD_TEST.read_text())
node = next(n for n in old_ast.body if isinstance(n, ast.ClassDef) and n.name == 'Fake')
fake_source = ast.get_source_segment(OLD_TEST.read_text(), node)
fake_source = fake_source.replace('u.MODES[n]) for n, b in oldfiles.items()', '(0o755 if n == u.SERVICE else u.MODES[n])) for n, b in oldfiles.items()')
namespace = dict(u=u, oldfiles=oldfiles, newfiles=newfiles, request=request,
                 baseline_sample=baseline_sample, copy=copy, Path=Path, json=json)
exec(compile(fake_source, str(OLD_TEST) + ':Fake-only', 'exec'), namespace)
OriginalFake = namespace['Fake']


class Fake(OriginalFake):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.new_after_start_invalid = {}
        self.transient_once = None
        self.initializing_once = False
        self.corrupt_new_manifest = False

    def manager(self, service_hash):
        self.edge('fresh-manager:' + service_hash)
        assert service_hash == u.SERVICE_SHA == u.sha(self.files[u.SERVICE][0])
        generation = 'new' if u.sha(self.files[u.MANIFEST][0]) == u.NEW else 'old'
        return dict(service_hash=service_hash, generation=generation, id=len(self.events))

    def observation(self):
        row = super().observation()
        row['state']['services'] = copy.deepcopy(actual['state']['services'])
        row['state']['camera_pm'] = copy.deepcopy(actual['state']['camera_pm'])
        row['state']['m2m'] = actual['state']['m2m'] if not self.camera_changed else '{}'
        row['limits'].setdefault('source_budget_ua', 100000)
        row['source'] = dict(online='1', usb_type='Unknown [SDP] DCP CDP C',
                             current_max=str(row['limits']['source_budget_ua']),
                             input_current_limit=str(row['limits']['native_ua']))
        row['sample']['budget_ua'] = row['limits']['source_budget_ua']
        if self.loaded == 'new':
            row['sample']['thermal_band'] = 4
            row['sample']['band_pre_shake'] = row['sample']['temp_decic']
            if self.running:
                row['sample'].update(self.new_after_start_invalid)
        return row

    def observe(self, manager):
        row = super().observe(manager)
        if self.loaded == 'new' and not self.running and self.initializing_once:
            self.initializing_once = False
            row['sample'].update(valid=0, error=-61, age_ms=-1)
        if self.loaded == 'new' and self.running and self.transient_once:
            row['sample'].update(self.transient_once)
            self.transient_once = None
        return row

    def inhibited_ready(self, manager, req):
        return u.Device.inhibited_ready(self, manager, req)

    def backup(self, files, before):
        self.edge('backup')
        assert set(files) == {u.KO, u.MANIFEST}
        assert files == {n: self.files[n] for n in u.MODES}
        self.saved = copy.deepcopy(files)

    def replace(self, name, content, mode):
        assert name in {u.KO, u.MANIFEST} and name != u.SERVICE
        if self.loaded is not None:
            assert not self.running, 'live disk-only repair must already be inhibited'
            assert self.invalid or self.new_after_start_invalid
        suffix = 'new' if content == newfiles[name] else 'old'
        self.edge('write:' + Path(name).name + ':' + suffix)
        assert mode == u.MODES[name]
        self.files[name] = (content, mode)

    def manager_command(self, manager, meta, action):
        super().manager_command(manager, meta, action)
        if self.loaded == 'new' and action == 'start' and self.corrupt_new_manifest:
            self.files[u.MANIFEST] = (b'{}\n', 0o600)


cases = []
def record(name, callback):
    callback()
    cases.append(dict(name=name, passed=True))

def reject(callback):
    try:
        callback()
    except Exception:
        return
    raise AssertionError('expected rejection')

def execute(fake=None, req=None):
    f = fake or Fake()
    service_before = f.files[u.SERVICE]
    r = u.update(copy.deepcopy(req or request), f)
    assert f.closed and r == f.result
    assert not any(e.startswith('write:samurai-charging:') for e in f.events)
    assert f.files[u.SERVICE] == service_before
    return r, f

def managed():
    r, f = execute()
    assert r['passed'] and r['accepted_state'] == 'managed' and f.loaded == 'new' and f.running
    assert f.count['unload'] == 1 and f.count['start:new'] == 1
    assert f.files[u.KO][0] == newfiles[u.KO] and f.files[u.MANIFEST][0] == newfiles[u.MANIFEST]
    assert r['limits'] == actual['limits'] and r['sample']['thermal_band'] == 4
    assert f.events.index('stop:old') < f.events.index('unload') < f.events.index('load:new') < f.events.index('start:new')
    assert f.count['observe:new'] >= 2  # inhibited safety gate, then acceptance
    assert r['before_session_seconds'] == baseline_sample['session_seconds'] and r['volatile_cycle_reload_boundary']
record('actual-r7-profile-two-file-managed-normal-sdp100', managed)

def full():
    r, f = execute(Fake(full=True))
    assert r['passed'] and r['accepted_state'] == 'full_holding' and r['sample']['session_seconds'] == 0
record('precise-full-remains-accepted', full)

def schema():
    assert set(u.MODES) == set(u.HASHES) == set(newfiles) == {u.KO, u.MANIFEST}
    assert len(payload) == 51100 and u.sha(payload) == u.PAYLOAD
    u.manifest_delta(oldmeta, newmeta)
    for field, value in [('guard', '/var/lib/samurai/k449-adopted/boot-id-private.txt'),
                         ('old_manifest_sha256', '944f2d91f66c5642bbcb130c3ef59e022ca6652e599401908f8528a29d34202d'),
                         ('transaction', 'charging-update-r6')]:
        req = copy.deepcopy(request); req[field] = value
        r, f = execute(req=req)
        assert not r['passed'] and 'begin' not in f.events
record('exact-r7-newguard-r8-request-no-r6-replay', schema)

def manifest_refusal():
    for kind in ['service', 'usb', 'protection', 'boot-like-extra']:
        bad = copy.deepcopy(newmeta)
        if kind == 'service': bad['installed_files'][u.SERVICE] = '0' * 64
        elif kind == 'boot-like-extra': bad['extra'] = 'boot'
        else:
            name = 'samurai-usb-input' if kind == 'usb' else 'samurai-gauge-protection'
            bad['modules'][name]['sha256'] = '0' * 64
        reject(lambda: u.manifest_delta(oldmeta, bad))
    reject(lambda: u.Device().replace(u.SERVICE, b'forbidden', 0o755))
record('service-usb-protection-manifest-delta-and-service-write-refused', manifest_refusal)

def tar_refusal():
    # Temporary hash pin alteration reaches inner structural guards; it does
    # not test an alternate payload accepted by the frozen production pins.
    for names in [[u.KO, u.MANIFEST, u.SERVICE], [u.MANIFEST, u.SERVICE]]:
        b = io.BytesIO()
        with tarfile.open(fileobj=b, mode='w:gz') as archive:
            for name in names:
                entry = tarfile.TarInfo(name.lstrip('/')); entry.mode = 0o600
                entry.uid = entry.gid = 0; entry.size = 0
                archive.addfile(entry, io.BytesIO(b''))
        raw = b.getvalue(); raw += b'\0' * (51100 - len(raw))
        req = copy.deepcopy(request)
        req.update(payload_sha256=u.sha(raw), payload_base64=base64.b64encode(raw).decode())
        with patch.object(u, 'PAYLOAD', u.sha(raw)):
            reject(lambda: u.unpack_request(req))
record('inner-two-member-whitelist-rejects-three-files-and-service-substitution', tar_refusal)

def service_refusal():
    f = Fake(); f.files[u.SERVICE] = (b'changed-service', 0o755)
    r, f = execute(f)
    assert not r['passed'] and 'stop:old' not in f.events and 'unload' not in f.events
    f = Fake(); f.files[u.SERVICE] = (oldfiles[u.SERVICE], 0o600)
    r = u.update(copy.deepcopy(request), f)
    assert not r['passed'] and 'stop:old' not in f.events
record('unchanged-service-bound-by-bytes-and-mode-without-writing', service_refusal)

def old_fault():
    for field in ['latched', 'cycle_timeout']:
        f = Fake(); f.old_invalid[field] = 1
        r, f = execute(f)
        assert not r['passed'] and 'stop:old' not in f.events and 'unload' not in f.events
    f = Fake(); f.old_after_stop_invalid['latched'] = 1
    r, f = execute(f)
    assert not r['passed'] and 'unload' not in f.events and not f.running
record('old-latch-timeout-and-poststop-fault-never-unloaded', old_fault)

def stop_failure():
    for failure in ['stop:old:1', 'bad-stop-readback']:
        r, f = execute(Fake([failure]))
        assert not r['passed'] and r['stop_error'] and 'unload' not in f.events
record('stop-return-and-inhibit-readback-required', stop_failure)

def new_fault():
    for field in ['latched', 'cycle_timeout', 'protection_ok']:
        f = Fake(); f.invalid[field] = 0 if field == 'protection_ok' else 1
        r, f = execute(f)
        assert not r['passed'] and f.loaded == 'new' and not f.running
        assert f.count['unload'] == 1 and 'start:new' not in f.events and 'start:old' not in f.events
        assert r['observed_unsafe_state_preserved_in_live_module']
        assert r['recovery_state'].startswith('r8-consistent-inhibited')
        assert f.files[u.KO][0] == newfiles[u.KO] and f.files[u.MANIFEST][0] == newfiles[u.MANIFEST]
record('new-preauto-fault-timeout-protection-keeps-consistent-r8-inhibited', new_fault)

def after_start_fault():
    f = Fake(); f.new_after_start_invalid.update(latched=1, error=-5)
    r, f = execute(f)
    assert not r['passed'] and f.loaded == 'new' and not f.running
    assert f.count['unload'] == 1 and f.count['start:new'] == 1 and 'start:old' not in f.events
    assert r['first_unsafe_sample']['latched'] == 1
record('fault-after-first-auto-preserves-live-latch-no-second-auto', after_start_fault)

def recovery_stop_failure():
    f = Fake(['stop:new:1']); f.invalid['latched'] = 1
    r, f = execute(f)
    assert not r['passed'] and r['stop_error'] and r['recovery_error']
    assert f.loaded == 'new' and not f.running and f.count['unload'] == 1
    assert f.count['stop:new'] == 2 and 'start:new' not in f.events and 'start:old' not in f.events
record('recovery-stop-error-retained-even-if-final-safety-stop-succeeds', recovery_stop_failure)

def transient_fault():
    f = Fake(); f.transient_once = dict(error=-5, latched=1)
    r, f = execute(f)
    assert not r['passed'] and f.loaded == 'new' and not f.running and f.count['unload'] == 1
    assert r['first_unsafe_sample']['latched'] == 1 and r['recovery_withheld_sample']['latched'] == 0
    assert r['observed_unsafe_state_preserved_in_live_module'] and 'start:old' not in f.events
record('earlier-unsafe-observation-not-pardoned-by-later-good-read', transient_fault)

def inconsistent_fault():
    f = Fake(); f.corrupt_new_manifest = True; f.new_after_start_invalid.update(latched=1)
    r, f = execute(f)
    assert not r['passed'] and f.loaded == 'new' and not f.running and f.count['unload'] == 1
    assert r['runtime_disk_mismatch_requires_review'] and set(r['repaired_disk_files']) == {u.KO, u.MANIFEST}
    assert f.files[u.KO][0] == oldfiles[u.KO] and f.files[u.MANIFEST][0] == oldfiles[u.MANIFEST]
    assert 'start:old' not in f.events
record('already-inconsistent-files-only-repair-records-live-disk-mismatch', inconsistent_fault)

def failed_install():
    for failure in ['write:samurai-mp2650.ko:new:1', 'write:manifest.json:new:1', 'load:new:1']:
        r, f = execute(Fake([failure]))
        assert not r['passed'] and r['recovery_state'] == 'r7-managed-current-source-budget'
        assert f.loaded == 'old' and f.running
        assert f.files[u.KO][0] == oldfiles[u.KO] and f.files[u.MANIFEST][0] == oldfiles[u.MANIFEST]
record('two-install-edges-and-known-load-failure-safe-r7-rollback', failed_install)

def unknown():
    for failure in ['uncertain:unload:1', 'uncertain:load:new:1']:
        r, f = execute(Fake([failure]))
        assert not r['passed'] and not r['terminal'] and r['mutating_process_unknown']
        key = failure.removeprefix('uncertain:').rsplit(':', 1)[0]
        later = f.events[f.events.index(key) + 1:]
        assert not any(e.startswith(('stop:', 'start:', 'write:', 'load:', 'unload')) for e in later)
record('unknown-unload-or-load-quarantine-no-recovery-mutation', unknown)

def unknown_during_retention():
    f = Fake(['uncertain:notes:new:2']); f.invalid['latched'] = 1
    r, f = execute(f)
    assert not r['passed'] and not r['terminal'] and r['mutating_process_unknown']
    assert f.loaded == 'new' and not f.running and f.count['unload'] == 1
    later = f.events[f.events.index('notes:new', f.events.index('notes:new') + 1) + 1:]
    assert not any(e.startswith(('stop:', 'start:', 'write:', 'load:', 'unload')) for e in later)
    d = u.Device(); d.uncertain = True
    d.read_owned = lambda *a: (_ for _ in ()).throw(AssertionError('must reject before file/manager access'))
    reject(lambda: d.manager_command({}, {}, 'stop'))
record('uncertain-provider-during-retention-no-disk-repair-or-manager-command', unknown_during_retention)

def budget_cv():
    f = Fake(); f.after_limits['cv_uv'] = 4375000
    r, f = execute(f)
    assert not r['passed']
    f = Fake(); f.after_limits.update(native_ua=500000, source_budget_ua=500000, input_ua=500000)
    r, f = execute(f)
    assert not r['passed'] and r['primary_error']['phase'] == 'new-acceptance'
    row = copy.deepcopy(actual)
    row['source'].update(usb_type='Unknown SDP DCP [CDP] C', current_max='1500000')
    row['limits'].update(source_budget_ua=1500000, input_ua=900000)
    row['sample']['budget_ua'] = 1500000
    row['registers']['00'] = row['registers']['0f'] = 18
    assert u.healthy(row, True) == 'managed'  # CDP is not falsely capped by raw native100
    row['sample']['budget_ua'] = 100000
    reject(lambda: u.healthy(row, True))
record('cv-or-source-change-fails-window-and-raw-native-distinct-from-cdp-budget', budget_cv)

def services():
    before = Fake().observation()
    for name, value in [('uid', 1000), ('comm', 'weston')]:
        row = copy.deepcopy(before); row['state']['services'][0][name] = value
        reject(lambda: u.unchanged(row, row))
    after = copy.deepcopy(before); after['state']['services'][0]['pid'] += 1
    reject(lambda: u.unchanged(before, after))
record('four-uid10000-service-identities-and-pids-exact', services)

def initialization():
    f = Fake(); f.initializing_once = True
    with patch.object(u.time, 'sleep') as sleep:
        r, f = execute(f)
    assert r['passed'] and sleep.call_count == 1
    assert f.count['observe:new'] == 3
record('documented-valid0-enodata-only-bounded-preauto-initialization', initialization)

def lease():
    d = u.Device()
    lease = dict(transaction='charging-update-r8', owner='charging', camera_released=True, exclusive=True,
                 token=request['window_token'], boot_id=request['identity']['boot_id'], expires_boottime_s=200)
    texts = {'/proc/sys/kernel/random/boot_id': request['identity']['boot_id'], u.GUARD: request['identity']['boot_id']}
    def read_owned(name):
        assert name == '/run/samurai-charging-r8-window.json'
        return json.dumps(lease).encode(), 0o600
    d.read_owned = read_owned
    with patch.object(u, 'Path', lambda p: SimpleNamespace(read_text=lambda: texts[p])), patch.object(u.time, 'clock_gettime', return_value=100):
        d.check_window(request)
        lease['transaction'] = 'charging-update-r6'; reject(lambda: d.check_window(request))
        lease['transaction'] = 'charging-update-r8'; lease['expires_boottime_s'] = 99
        reject(lambda: d.check_window(request))
record('actual-device-new-guard-r8-lease-rejects-old-or-expired', lease)

def pending_child():
    d = u.Device(); d.log = lambda *a: None
    child = SimpleNamespace(pid=999, communicate=lambda **kw: (_ for _ in ()).throw(subprocess.TimeoutExpired('insmod', 30)), poll=lambda: None)
    with patch.object(u.subprocess, 'Popen', return_value=child) as popen:
        reject(lambda: d.mutate_command('insmod', 'test-only'))
        assert d.uncertain and d.child is child
        reject(lambda: d.mutate_command('rmmod', 'test-only'))
        assert popen.call_count == 1
    # Real close must keep its lock while uncertain; no /run or device access.
    import tempfile
    with tempfile.TemporaryFile() as lock:
        d.lock = os.dup(lock.fileno()); d.close(); os.fstat(d.lock); os.close(d.lock)
record('actual-popen-timeout-and-lock-retention-no-second-child', pending_child)

def manager_identity():
    d = u.Device(); d.read_owned = lambda n: (oldfiles[u.SERVICE], 0o755)
    with patch.object(u.runpy, 'run_path', return_value={}) as run:
        manager = d.manager(u.SERVICE_SHA)
        assert manager['_r8_code_sha256'] == u.SERVICE_SHA and run.call_args.args == (u.SERVICE,)
        d.read_owned = lambda n: (b'changed-service', 0o755)
        reject(lambda: d.verify(manager))
        reject(lambda: d.manager_for_stop())
record('actual-fresh-manager-readonly-binding-stale-code-refused', manager_identity)

def unknown_tail():
    # Execute the actual CLI tail with all filesystem/process edges replaced.
    # A lost stdout or failed receipt must still enter the quarantine loop.
    class QuarantineReached(BaseException): pass
    def sleep(_): raise QuarantineReached()
    tail = ast.parse((HERE / 'update-r8.py').read_text()).body[-1]
    assert isinstance(tail, ast.If)
    for failure in ['stdout', 'receipt']:
        dev = SimpleNamespace(uncertain=True)
        def update(*args):
            if failure == 'receipt': raise OSError('simulated receipt write failure')
            return dict(passed=False)
        def output(*args, **kwargs): raise BrokenPipeError('simulated closed output')
        namespace = dict(__name__='__main__', sys=SimpleNamespace(argv=['update-r8.py', '--execute-r8'],
                          stdin=SimpleNamespace(buffer=io.BytesIO(b'{}'))),
                          need=u.need, os=SimpleNamespace(umask=lambda _: None),
                          Device=lambda: dev, update=update, print=output, json=json,
                          time=SimpleNamespace(sleep=sleep))
        try:
            exec(compile(ast.Module(body=[tail], type_ignores=[]), 'actual-r8-cli-tail', 'exec'), namespace)
        except QuarantineReached:
            pass
        else:
            raise AssertionError('unknown child escaped quarantine')
record('actual-cli-unknown-worker-holds-on-stdout-or-receipt-failure', unknown_tail)

report = dict(passed=True, phase='offline-directed-r8-migration', executed_case_count=len(cases), cases=cases,
              worker_sha256=sha(HERE / 'update-r8.py'),
              tested_files={n: sha(HERE / n) for n in ['update-r8.py', 'test-update-r8.py', 'prepare.py']},
              reused_frozen_worker_sha256=sha(OLD_WORKER), reused_fake_source_sha256=sha(OLD_TEST),
              previous_67_case_receipt_sha256=sha(OLD_TEST.with_name('test-result.json')),
              old_67_case_matrix_rerun=False, fixture_actual_r7_trial_result_sha256=sha(trial),
              tested_payload_sha256=u.sha(payload), tested_payload_bytes=len(payload),
              test_scope='actual update transaction/health/manifest/payload, selected actual Device methods; fake device boundaries only',
              phone_accessed=False, ssh_executed=False, usb_accessed=False, sdk_invoked=False,
              runtime_validation_pending=True)
(HERE / 'test-result.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: report[k] for k in ['passed', 'executed_case_count', 'worker_sha256', 'old_67_case_matrix_rerun']}, indent=2))
