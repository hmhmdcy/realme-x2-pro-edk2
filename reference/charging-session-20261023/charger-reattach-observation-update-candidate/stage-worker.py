#!/usr/bin/python3
"""One explicit r7 -> r8 transaction. No device access on import."""
from pathlib import Path
import base64
import fcntl
import hashlib
import io
import json
import os
import runpy
import stat
import subprocess
import sys
import tarfile
import time

RELEASE = '7.3.0-rc6-rmx1931-samurai-k363+'
KO = '/lib/modules/' + RELEASE + '/extra/samurai-charging/samurai-mp2650.ko'
SERVICE = '/usr/sbin/samurai-charging'
MANIFEST = '/usr/share/samurai-charging/manifest.json'
GUARD = '/var/lib/samurai/charging-r7-8162b1e7040030d514a83534-adopted/boot-id-private.txt'
WINDOW = '/run/samurai-charging-r8-window.json'
SOC_SERIAL = '/sys/devices/soc0/serial_number'
OUT = '/root/charging-management-20261023/charging-update-r8'
OLD = '5638db4c183ec502ed1df4facfe91111d1956754bb2338a5ddaf8838e9552c68'
NEW = '320316c3d93c1dbcaae29440f1f17d72c75e4994d656a9da9fcd5aeb93c10a1f'
PAYLOAD = 'f2bcbe500463114a407d93ddb4e2081db179f61dcc35d0a194abb4d18b2a5722'
SERVICE_SHA = '61451ffea87cca466dbbb2f1a2c6e7c05d0eee517479e8b019d43b1869355aa4'
HASHES = {KO: '10ec06fb9d798d72e08495617cfc04e7e49c77e536a12f205053e9cdbfa6297f',
          MANIFEST: NEW}
MODES = {KO: 0o600, MANIFEST: 0o600}
PROVIDERS = ('samurai-usb-input', 'samurai-gauge-protection')
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def need(condition, message):
    if not condition:
        raise RuntimeError(message)


def detail(error):
    return type(error).__name__ + ': ' + str(error)


class MutationUncertain(RuntimeError):
    """A mutating child may still be running. Never initiate another mutation."""


def unpack_request(request):
    need(set(request) == {'transaction', 'guard', 'identity', 'window_token',
                         'old_manifest_sha256', 'new_manifest_sha256',
                         'payload_sha256', 'payload_base64'}, 'r8 request schema')
    need(request['transaction'] == 'charging-update-r8', 'only new r8 transaction')
    need(request['guard'] == GUARD, 'current boot guard only')
    need((request['old_manifest_sha256'], request['new_manifest_sha256'],
          request['payload_sha256']) == (OLD, NEW, PAYLOAD), 'exact r7/r8 identities')
    need(set(request['identity']) == {'boot_id', 'serial_sha256', 'compatible_sha256'}, 'device identity schema')
    for key in ['serial_sha256', 'compatible_sha256']:
        value = request['identity'][key]
        need(isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value), 'explicit identity digest')
    token = request['window_token']
    need(isinstance(token, str) and 32 <= len(token) <= 128 and not any(c.isspace() for c in token), 'unique r8 window token')
    raw = base64.b64decode(request['payload_base64'], validate=True)
    need(len(raw) == 51100 and sha(raw) == PAYLOAD, 'exact r8 payload')
    files = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as archive:
        members = archive.getmembers()
        need(len(members) == 2, 'exactly two payload files; service is read-only')
        for entry in members:
            target = '/' + entry.name
            need(target in MODES and target not in files, 'unexpected/duplicate tar member')
            need(entry.isfile() and entry.uid == entry.gid == 0 and entry.mode == MODES[target], 'payload type/owner/mode')
            content = archive.extractfile(entry).read()
            need(sha(content) == HASHES[target], 'payload file hash: ' + target)
            files[target] = content
    return files, json.loads(files[MANIFEST])


def manifest_delta(old, new):
    import copy
    expected = copy.deepcopy(old)
    expected['adapter_revision'] = 'r8'
    expected['modules']['samurai-mp2650']['sha256'] = HASHES[KO]
    expected['installed_files'][KO] = HASHES[KO]
    need(old['installed_files'][SERVICE] == new['installed_files'][SERVICE] == SERVICE_SHA, 'unchanged exact read-only service')
    need(expected == new, 'only charger hash and r8 revision may change')
    need(old['release'] == RELEASE and old['modules']['samurai-mp2650']['target'] == KO, 'exact module target/ABI')
    need(old['default_input_cap_ua'] == 900000 and old['default_charge_cap_ua'] == 250000
         and old['source_budget_enforced'] is True, 'original managed request limits')


class UnsafeSample(RuntimeError):
    def __init__(self, message, data):
        super().__init__(message)
        self.sample = dict(data.get('sample', {}))


def safe_sample(data):
    try:
        _safe_sample(data)
    except Exception as error:
        raise UnsafeSample(detail(error), data) from error


def _safe_sample(data):
    s = data['sample']
    need(s.get('valid') == s.get('protection_ok') == s.get('online') == 1
         and s.get('shadow') == 0 and 0 <= s.get('age_ms', -1) <= 3000, 'fresh complete online protection sample')
    need(all(s.get(k, -1) == 0 for k in ['error', 'stop_error', 'latched', 'fault',
                                       'source_inhibit', 'cycle_timeout', 'thermal_inhibit']), 'no current or old fault/timeout/hold')
    need('flags' in s and not s['flags'] & 0xc000, 'no gauge charge-stop/overcharge flags')
    need(s.get('gauge_charge_stop', 0) == 0, 'gauge hold is not healthy acceptance')


def healthy(data, allow_full):
    safe_sample(data)
    s = data['sample']
    fields = ('logical_full', 'hold_requested', 'full_holding', 'full_cause')
    if allow_full:
        need(all(key in s for key in (*fields, 'gauge_charge_stop', 'gauge_current_ua')),
             'complete new r8 telemetry fields')
    partial = any(s.get(k, 0) for k in fields)
    full = (allow_full and s.get('logical_full') == s.get('hold_requested') == s.get('full_holding') == 1
            and s.get('full_cause') in (1, 2, 3) and s.get('desired_enable') == 0
            and s.get('session_seconds') == 0 and data['registers']['08'] & 0x18 == 0)
    if partial:
        need(full, 'only exact healthy Full holding accepted')
    else:
        need(s.get('desired_enable') == 1 and data['registers']['08'] & 0x18 == 0x10, 'normal managed CHG readback')
    lim = data['limits']
    source = data['source']
    need(source['online'] == '1' and int(source['input_current_limit']) == lim['native_ua']
         and int(source['current_max']) == lim['source_budget_ua'], 'raw native and effective source fields agree')
    need(50000 <= lim['native_ua'] and 50000 <= lim['source_budget_ua'] <= 3000000
         and 50000 <= lim['input_ua'] <= min(900000, lim['source_budget_ua'])
         and 200000 <= lim['charge_ua'] <= 250000, 'current legal source/charge budget')
    r = data['registers']
    need((r['00'] & 0x7f) * 50000 == (r['0f'] & 0x7f) * 50000 == lim['input_ua'], 'both physical input limits')
    need((r['02'] & 0x7f) * 50000 == lim['charge_ua'], 'physical charge current limit')
    need(s.get('budget_ua') == lim['source_budget_ua'], 'fresh sample/effective source budget agreement')
    need(160 <= s.get('temp_decic', -999) < 440, 'this update window requires the NORMAL band')
    if 'thermal_band' in s:
        need(s['thermal_band'] == 4, 'new OEM thermal band must remain NORMAL')
    return 'full_holding' if full else 'managed'


def unchanged(before, after):
    for key in ['boot_id', 'release', 'camera_pm', 'm2m', 'services']:
        need(before['state'][key] == after['state'][key], 'environment changed: ' + key)
    need(before['state']['taint'] == after['state']['taint'] == '0', 'taint must remain zero')
    services = before['state']['services']
    need(len(services) == 4 and {s['comm'] for s in services} == {'phoc', 'phosh', 'pipewire', 'wireplumber'}
         and all(s['uid'] == 10000 and s['pid'] > 0 for s in services), 'four actual UID10000 session services')
    need(all(value == 'suspended' for value in before['state']['camera_pm'].values())
         and len(before['state']['camera_pm']) == 4, 'camera runtime PM must be idle')
    m2m = json.loads(before['state']['m2m'])
    need(all(m2m.get(key) == 0 for key in ['users', 'orphans', 'jobs', 'first_error'])
         and all(m2m.get(key) is False for key in ['running', 'fatal', 'pinned']), 'camera m2m must be idle')
    need(before['openrc_started'] is True and after['openrc_started'] is True, 'OpenRC started marker preserved')
    for name in PROVIDERS:
        need(before['notes'][name] == after['notes'][name], 'resident provider note changed: ' + name)


def stopped(io, manager, meta, result=None):
    # A raised stop is a failed transaction even if a later readback is paused.
    try:
        need(io.module_state() == 'live', 'stop only a known live module')
        io.manager_command(manager, meta, 'stop')
        need(io.registers()['08'] & 0x18 == 8, 'synchronous INHIBIT hardware readback')
    except Exception as error:
        if result is not None:
            result['stop_error'] = detail(error)
        raise


def update(request, io):
    """Actual ordered transaction; tests replace only device/file/process edges."""
    result = {'transaction_id': request['transaction_id'], 'schema': 'samurai-charger-reattach-update-result-v1', 'passed': False, 'terminal': True,
              'primary_error': None, 'stop_error': None, 'recovery_error': None,
              'recovery_state': None, 'mutating_process_unknown': False,
              'installed_new': False, 'runtime_validation_pending': True}
    result['request_sha256'] = sha(io.request_raw)
    phase = 'request'
    backup = old = before = None
    stopped_old = changed = False
    try:
        files, new = unpack_request(request)
        phase = 'exclusive-window'
        io.begin(request)  # identity + boot + owned lease + shared service lock + mkdir(exclusive)
        phase = 'preflight'
        backup = {name: io.read_owned(name) for name in MODES}
        need(sha(backup[MANIFEST][0]) == OLD, 'installed IRQ baseline manifest hash')
        old = json.loads(backup[MANIFEST][0])
        manifest_delta(old, new)
        for name in MODES:
            need(backup[name][1] == MODES[name], 'preserve actual installed file mode: ' + name)
            if name != MANIFEST:
                need(sha(backup[name][0]) == old['installed_files'][name], 'installed old file hash')
        service_raw, service_mode = io.read_owned(SERVICE)
        need(sha(service_raw) == SERVICE_SHA and service_mode == 0o755, 'exact read-only service identity/mode')
        manager = io.manager(SERVICE_SHA)
        need(io.verify(manager) == old, 'fresh old manager verify')
        io.notes_match(manager, old)  # includes old loaded charger note; never erase an unknown live module
        before = io.observe(manager)
        result['before_state'] = healthy(before, allow_full=True)
        need(result['before_state'] == 'managed', 'Full state cannot be restored by the existing API; no stop/unload')
        need(before['limits']['charge_ua'] == 250000, 'current charge baseline 250mA')
        unchanged(before, before)
        io.backup(backup, before)
        result['before_session_seconds'] = before['sample']['session_seconds']
        result['volatile_cycle_reload_boundary'] = True
        result['service_read_only_sha256'] = SERVICE_SHA
        phase = 'old-stop'
        continuity(before, io.observe(manager), allow_full=False)
        try:
            stopped(io, manager, old, result)
        except Exception as error:
            result['stop_error'] = detail(error)
            raise
        phase = 'old-stop-check'
        old_paused = io.observe(manager)
        result['old_stopped_sample'] = old_paused['sample']
        io.log('old-inhibited-private.json', old_paused)
        continuity(before, old_paused, allow_full=False)  # preserve Full, faults and budget history
        stopped_old = True
        io.check_window(request)
        phase = 'old-unload'
        io.unload()
        changed = True
        phase = 'install-two-files'
        for name in [KO, MANIFEST]:
            io.replace(name, files[name], MODES[name])
        phase = 'explicit-new-load'
        io.check_window(request)
        io.load(KO)
        phase = 'fresh-new-manager'
        manager = io.manager(SERVICE_SHA)  # never reuse the old Python function globals
        need(io.verify(manager) == new, 'fresh installed r8 service verify')
        io.notes_match(manager, new)
        io.cap_inhibited(before)
        phase = 'new-inhibited-sample'
        new_paused = io.inhibited_ready(manager, request)
        result['new_inhibited_sample'] = new_paused['sample']
        io.log('new-inhibited-private.json', new_paused)
        phase = 'new-start'
        io.manager_command(manager, new, 'start')  # original 900/250 requests, current kernel budget authority
        phase = 'new-acceptance'
        after = io.observe(manager)
        io.log('after-private.json', after)
        result['accepted_state'] = healthy(after, allow_full=True)
        need(after['sample'].get('thermal_band') == 4 and 'band_pre_shake' in after['sample'], 'complete r8 NORMAL thermal telemetry')
        unchanged(before, after)
        need(after['limits'] == before['limits'], 'input/charge/CV/native/effective budget must remain exact')
        need(after['source'] == before['source'], 'source changed during acceptance')
        io.check_window(request)
        result.update(passed=True, installed_new=True, runtime_validation_pending=False,
                      old_manifest_sha256=OLD, new_manifest_sha256=NEW,
                      sample=after['sample'], limits=after['limits'],
                      native_usb_and_protection_kept_loaded=True, camera_services_unchanged=True)
    except Exception as error:
        result['primary_error'] = {'phase': phase, 'error': detail(error)}
        if isinstance(error, UnsafeSample):
            result['first_unsafe_sample'] = error.sample
        result['mutating_process_unknown'] = io.uncertain
        # A timed-out child/coming-going module is not a completed operation.
        # In particular, never race a still-running insmod/rmmod with fallback.
        if io.uncertain:
            result['terminal'] = False
            result['recovery_state'] = 'unknown-worker-or-module-state; no further mutation'
        elif stopped_old:
            try:
                retained = False
                if io.module_present():
                    need(io.module_state() == 'live', 'recover only a known live module')
                    manager = io.manager_for_stop()
                    current = None
                    try:
                        current = io.observe(manager)
                        continuity(before, current, allow_full=False)
                        need(not isinstance(error, UnsafeSample), 'earlier observed unsafe sample remains disqualifying')
                    except Exception as sample_error:
                        if io.uncertain:
                            raise
                        # Preserve the live module's fault/timeout/history. A
                        # reload followed by AUTO would erase a transient latch.
                        result['recovery_withheld_reason'] = detail(sample_error)
                        result['recovery_withheld_sample'] = current.get('sample') if current else None
                        stopped(io, manager, old, result)
                        try:
                            current_meta = io.verify(manager)
                            need(sha(io.read_owned(MANIFEST)[0]) in (OLD, NEW), 'known coherent installed version')
                            io.notes_match(manager, current_meta)
                            result['recovery_state'] = current_meta['adapter_revision'] + '-consistent-inhibited; unsafe sample retained; no unload/AUTO'
                        except Exception as coherence_error:
                            if io.uncertain:
                                raise
                            result['recovery_coherence_error'] = detail(coherence_error)
                            # Only an already inconsistent installation may need
                            # disk repair. Never unload its unsafe live module.
                            repaired = []
                            if changed:
                                for name in [KO, MANIFEST]:
                                    io.replace(name, backup[name][0], backup[name][1])
                                    repaired.append(name)
                            result['repaired_disk_files'] = repaired
                            result['runtime_disk_mismatch_requires_review'] = True
                            result['recovery_state'] = 'unsafe-live-module-inhibited; IRQ baseline disk repair only; no unload/AUTO'
                        result['observed_unsafe_state_preserved_in_live_module'] = True
                        retained = True
                    if not retained:
                        stopped(io, manager, old, result)
                        io.unload()
                if not retained:
                    if changed:
                        for name in [KO, MANIFEST]:
                            io.replace(name, backup[name][0], backup[name][1])
                    manager = io.manager(SERVICE_SHA)
                    need(io.verify(manager) == old, 'fresh restored IRQ baseline service verify')
                    io.load(KO)
                    io.notes_match(manager, old)
                    io.cap_inhibited(before)
                    result['restored_inhibited_sample'] = io.inhibited_ready(manager, request)['sample']
                    io.check_window(request)
                    io.manager_command(manager, old, 'start')
                    recovered = io.observe(manager)
                    healthy(recovered, allow_full=True)
                    unchanged(before, recovered)
                    need(recovered['limits']['cv_uv'] <= before['limits']['cv_uv'], 'restored CV ceiling')
                    result['recovery_state'] = 'irq-baseline-managed-current-source-budget'
            except Exception as recovery_error:
                result['recovery_error'] = detail(recovery_error)
                result['recovery_state'] = 'recovery-failed; live-module safety stop only; operator review'
                result['mutating_process_unknown'] = io.uncertain
                result['terminal'] = not io.uncertain
                # No additional unload/load. If the module is live and no child
                # is pending, make one explicit safety stop, preserving its error.
                if not io.uncertain and io.module_present():
                    try:
                        stopped(io, io.manager_for_stop(), old, result)
                    except Exception as stop_error:
                        result['stop_error'] = detail(stop_error)
        elif phase in ('old-stop', 'old-stop-check'):
            result['recovery_state'] = 'irq-baseline-files-and-module-retained; stop or fresh post-stop check failed; no unload'
        else:
            result['recovery_state'] = 'preflight-only; no charging mutation'
    finally:
        try:
            io.close()
        except Exception as close_error:
            result['close_error'] = detail(close_error)
            result['passed'] = False
        io.finish(result)
    return result


class R8Device:
    """Fixed Samurai paths only. Not an SSH launcher or a general updater."""
    def __init__(self):
        self.out = None
        self.lock = None
        self.uncertain = False
        self.child = None
        self.events = []

    def read_owned(self, name):
        p = Path(name)
        st = p.lstat()
        need(stat.S_ISREG(st.st_mode) and st.st_uid == 0 and not st.st_mode & 0o022,
             'regular root-owned protected file: ' + name)
        return p.read_bytes(), stat.S_IMODE(st.st_mode)

    def check_window(self, request):
        need(Path('/proc/sys/kernel/random/boot_id').read_text().strip() == request['identity']['boot_id'], 'same explicit boot identity')
        need(Path(GUARD).read_text().strip() == request['identity']['boot_id'], 'current guard')
        raw, mode = self.read_owned(WINDOW)
        need(mode == 0o600, 'private window lease mode')
        lease = json.loads(raw)
        need(lease['transaction'] == 'charging-update-r8' and lease['owner'] == 'charging'
             and lease['camera_released'] is True and lease['exclusive'] is True
             and lease['token'] == request['window_token']
             and lease['boot_id'] == request['identity']['boot_id'], 'explicit coordinated exclusive window')
        now = time.clock_gettime(time.CLOCK_BOOTTIME)
        need(now < lease['expires_boottime_s'] <= now + 300, 'live short BOOTTIME window')

    def begin(self, request):
        need(os.geteuid() == 0 and os.uname().release == RELEASE and not sys.flags.optimize,
             'root, exact k363 ABI, and enabled original service assertions')
        base = Path('/sys/firmware/devicetree/base')
        compat = (base / 'compatible').read_bytes()
        need(b'realme,samurai' in compat.split(b'\0'), 'Samurai board')
        # Qualcomm socinfo hardware serial exported by the SoC bus, raw bytes
        # including the sysfs newline. No DT/other-path fallback is permitted.
        serial = Path(SOC_SERIAL).read_bytes()
        need(serial.strip() and sha(serial) == request['identity']['serial_sha256']
             and sha(compat) == request['identity']['compatible_sha256'], 'exact SoC serial and compatible identity')
        need(Path('/sys/bus/i2c/devices/0-005c/name').read_text().strip() == 'mp2650', 'real charger client')
        need(Path('/sys/bus/i2c/devices/0-005c/of_node').resolve().as_posix().endswith('/soc@0/geniqup@8c0000/i2c@884000/charger@5c'), 'real charger DT node')
        self.check_window(request)
        self.lock = os.open('/run/lock/samurai-charging.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        need(os.fstat(self.lock).st_uid == 0 and stat.S_ISREG(os.fstat(self.lock).st_mode)
             and not os.fstat(self.lock).st_mode & 0o022, 'service lock identity/mode')
        fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        p = Path(OUT)
        p.mkdir(mode=0o700, exist_ok=False)  # existing failed or finished transaction can never replay
        self.out = p
        self.check_window(request)

    def manager(self, expected_service):
        need(sha(self.read_owned(SERVICE)[0]) == expected_service, 'installed manager code identity')
        manager = runpy.run_path(SERVICE)
        need(sha(self.read_owned(SERVICE)[0]) == expected_service, 'manager code changed while loading')
        manager['_r8_code_sha256'] = expected_service
        self.events.append(['fresh-manager', expected_service])
        return manager

    def manager_for_stop(self):
        digest = sha(self.read_owned(SERVICE)[0])
        need(digest == SERVICE_SHA, 'only exact unchanged manager code may stop')
        return self.manager(digest)

    def verify(self, manager):
        need(sha(self.read_owned(SERVICE)[0]) == manager['_r8_code_sha256'], 'cannot verify with stale in-memory manager')
        return manager['verify']()

    def notes_match(self, manager, meta):
        for name, entry in meta['modules'].items():
            need(self.module_state(name) == 'live', 'loaded module not live: ' + name)
            manager['loaded_matches'](Path(entry['target']), name.replace('-', '_'))

    def registers(self):
        # Read-only accesses reuse the installed original library.
        return self.manager_for_stop()['live'].registers()

    def observe(self, manager):
        live = manager['live']
        state = live.state()
        supply = live.PSY / 'mp2650-input'
        notes = {name: sha(Path('/sys/module', name.replace('-', '_'), 'notes/.note.gnu.build-id').read_bytes())
                 for name in (*PROVIDERS, 'samurai-mp2650')}
        source = {key: (live.PSY / 'samurai-usb-input' / key).read_text().strip()
                  for key in ['online', 'usb_type', 'current_max', 'input_current_limit']}
        return {'state': state, 'sample': manager['sample'](), 'registers': state['registers'], 'notes': notes, 'source': source,
                'openrc_started': Path('/run/openrc/started/samurai-charging').exists(),
                'limits': {'native_ua': int(source['input_current_limit']),
                           'source_budget_ua': int(source['current_max']),
                           'input_ua': int((supply / 'input_current_limit').read_text()),
                           'charge_ua': int((supply / 'constant_charge_current').read_text()),
                           'cv_uv': 3712500 + ((state['registers']['04'] & 0x7e) >> 1) * 12500}}

    def inhibited_ready(self, manager, request):
        # A newly probed module starts with valid=0/error=-ENODATA. Only that
        # documented initialization state may wait, at most three seconds.
        deadline = time.monotonic() + 3
        while True:
            self.check_window(request)
            current = self.observe(manager)
            s = current['sample']
            initializing = (s.get('valid') == 0 and s.get('error') == -61
                            and all(s.get(key, -1) == 0 for key in
                                    ['latched', 'fault', 'stop_error', 'cycle_timeout', 'source_inhibit', 'thermal_inhibit']))
            need(current['registers']['08'] & 0x18 == 8, 'pre-AUTO synchronous INHIBIT readback')
            if not initializing:
                safe_sample(current)
                need(160 <= s.get('temp_decic', -999) < 440, 'pre-AUTO NORMAL band')
                return current
            need(time.monotonic() < deadline, 'new module never produced a fresh safe inhibited sample')
            time.sleep(.2)

    def manager_command(self, manager, meta, action):
        # Caller already owns the actual service lock. A child rc-service would
        # deadlock on this lock; directly execute freshly loaded installed code.
        need(not self.uncertain, 'unknown child/module: no further manager mutation')
        actual = sha(self.read_owned(SERVICE)[0])
        need(actual == manager['_r8_code_sha256'], 'cannot start/stop with stale in-memory manager')
        self.events.append(['manager-command', actual, action])
        return manager['command'](meta, action)

    def backup(self, files, before):
        for name, (content, mode) in files.items():
            p = self.out / (Path(name).name + '.before')
            with p.open('xb') as stream:
                stream.write(content); stream.flush(); os.fsync(stream.fileno())
            p.chmod(0o600)
        self.log('before-private.json', {'observation': before, 'modes': {n: m for n, (_, m) in files.items()}})

    def replace(self, name, content, mode):
        need(name in MODES and mode == MODES[name], 'only exact charger/manifest pair and original modes')
        p = Path(name)
        temp = p.with_name(p.name + '.reattach-next')
        created = False
        try:
            with temp.open('xb') as stream:
                created = True
                stream.write(content); stream.flush(); os.fchmod(stream.fileno(), mode); os.fsync(stream.fileno())
            temp.replace(p)
            fd = os.open(p.parent, os.O_DIRECTORY | os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        except Exception:
            if created:
                temp.unlink(missing_ok=True)
            raise

    def mutate_command(self, *args):
        need(not self.uncertain, 'mutating child still unknown')
        self.events.append(['process', *args])
        self.child = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            stdout, stderr = self.child.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            self.uncertain = True
            self.log('pending-process-private.json', {'pid': self.child.pid, 'args': args, 'returncode': self.child.poll()})
            raise MutationUncertain('pid %d timed out; no kill/retry/fallback' % self.child.pid)
        self.child.wait()
        self.log('last-process-private.json', {'args': args, 'returncode': self.child.returncode, 'stdout': stdout, 'stderr': stderr})
        need(self.child.returncode == 0, 'mutating child failed: ' + repr(args))

    def module_present(self):
        return Path('/sys/module/samurai_mp2650').exists()

    def module_state(self, name='samurai-mp2650'):
        p = Path('/sys/module', name.replace('-', '_'))
        if not p.exists():
            return 'absent'
        try:
            value = (p / 'initstate').read_text().strip()
        except OSError as error:
            self.uncertain = True
            raise MutationUncertain('cannot establish module %s state: %s' % (name, error)) from error
        if value != 'live':
            self.uncertain = True
            raise MutationUncertain('module %s is %s' % (name, value))
        return value

    def unload(self):
        need(self.module_state() == 'live', 'only live charger may unload')
        self.mutate_command('rmmod', 'samurai_mp2650')
        need(not self.module_present() and not Path('/sys/bus/i2c/devices/0-005c/driver').exists(), 'charger fully removed')

    def load(self, path):
        need(path == KO and not self.module_present(), 'explicit absent charger load only')
        self.mutate_command('insmod', KO, 'runtime_board=1', 'control=1')
        need(self.module_state() == 'live', 'new charger live')

    def log(self, name, data):
        if self.out is not None:
            (self.out / name).write_text(json.dumps(data, indent=2) + '\n')

    def finish(self, result):
        if self.out is not None:
            final = {}
            for name in MODES:
                try:
                    raw, mode = self.read_owned(name)
                    final[name] = {'sha256': sha(raw), 'mode': oct(mode)}
                except Exception as error:
                    final[name] = {'error': detail(error)}
            result['final_files'] = final
            result['installed_new'] = all(final[n].get('sha256') == HASHES[n] and final[n].get('mode') == oct(MODES[n]) for n in MODES)
            result['pending_child_pid'] = self.child.pid if self.uncertain and self.child else None
        self.log('events-private.json', self.events)
        self.log('result.json', result)

    def close(self):
        if self.uncertain:
            # __main__ keeps this quarantined worker alive. Only an explicit
            # operator decision after child/module inspection may release it.
            return
        if self.lock is not None:
            os.close(self.lock)
            self.lock = None



# Narrow current-IRQ binding. The R8 transaction/atomic replacement/recovery body above is reused.
import argparse
import math
import re
import uuid

VERSION = '#502 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026'
ROOT = '/root/charging-management-20261023'
LOCK = '/run/lock/samurai-charging.lock'
INSTANCE = '/sys/devices/platform/samurai-gauge-protection'
OLD = '5fca8e5a0795325bd780b7965579068c7edc35fa7da12bac357bb30bbde69417'
NEW = '18e8a1049a2c497fbc47ace50f8319aefccd63a9cd1ce5a7e9ef06916773b4e5'
PAYLOAD = '0870e32b1c6f5a927a1480a4cd523c2804dc7f44fe1796e8adb2b0100ffc71ea'
OLD_CHARGER = '10ec06fb9d798d72e08495617cfc04e7e49c77e536a12f205053e9cdbfa6297f'
HASHES = {KO: '97c16c3dc0b458fa4d2c686912ffdf805b899abfb846201767843a0348cbffdd', MANIFEST: NEW}
NOTES = {'samurai-usb-input': 'a845cd08aa415ca01ad4791b8c66047a927577e76439e632c73b6b4e2cff8c6d',
         'samurai-gauge-protection': 'fc0d253d556b6ba656db263aaa50c37e3af2c7fe115b67e6b02641ae8b5733ec',
         'samurai-mp2650': 'f4d5768a4250b901ea956560d9c6b4b1dd32ac80893cbbd31609d9c032c4680d'}
NEW_NOTE = 'fe15a2fcb618dee0b161952cd66c32f2d5ecc9c8d50b0975242da5353c472016'
MAC_CACHE_SHA = '02c98143301bb5db896c6f535f490495428df8b8c6fd6ab3cdc69ca507a545a8'
CARRIERS = {'boot': (100663296, 'eddadec33fcd1d114c45af76cb9fc6d6b5f1de2c81c0e9fada099c5b884f6e06'),
            'logdump': (67108864, 'ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1')}
_r8_healthy = healthy
_r8_sample = _safe_sample
_r8_unchanged = unchanged


def validate_request(request):
    need(set(request) == {'schema', 'transaction_id', 'worker_sha256', 'identity', 'adoption', 'lease_token',
                         'old_manifest_sha256', 'new_manifest_sha256', 'payload_sha256', 'payload_base64'}, 'request fields')
    need(request['schema'] == 'samurai-charger-reattach-update-v1' and
         re.fullmatch(r'charger-reattach-update-[a-z0-9-]{8,48}', request['transaction_id']), 'request schema/unique transaction')
    i, a = request['identity'], request['adoption']
    need(set(i) == {'boot_id', 'version', 'serial_sha256', 'compatible_sha256', 'rootfs_sha256'} and
         str(uuid.UUID(i['boot_id'])) == i['boot_id'] and i['version'] == VERSION, 'current IRQ identity fields')
    need(set(a) == {'transaction_id', 'guard_path', 'guard_sha256'} and
         re.fullmatch(r'usb-irq-protection-activate-[a-z0-9-]{8,48}', a['transaction_id']) and
         a['guard_path'] == '/var/lib/samurai/' + a['transaction_id'] + '-adopted/boot-id-private.txt', 'actual IRQ adopted guard')
    for value in [request['worker_sha256'], a['guard_sha256'], i['serial_sha256'], i['compatible_sha256'], i['rootfs_sha256']]:
        need(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value), 'identity/source hash')
    need(isinstance(request['lease_token'], str) and re.fullmatch('[0-9a-f]{48}', request['lease_token']), 'unique lease token')
    need((request['old_manifest_sha256'], request['new_manifest_sha256'], request['payload_sha256']) == (OLD, NEW, PAYLOAD), 'fixed two-file transition')


def unpack_request(request):
    validate_request(request)
    raw = base64.b64decode(request['payload_base64'], validate=True)
    need(len(raw) == 52491 and sha(raw) == PAYLOAD, 'exact forward payload')
    files = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as archive:
        members = archive.getmembers()
        need(len(members) == 2, 'only charger and manifest')
        for entry in members:
            target = '/' + entry.name
            need(target in MODES and target not in files and entry.isfile() and entry.uid == entry.gid == 0 and
                 entry.mode == MODES[target], 'exact regular payload member/mode/owner')
            content = archive.extractfile(entry).read()
            need(sha(content) == HASHES[target], 'exact payload member hash')
            files[target] = content
    return files, json.loads(files[MANIFEST])


def manifest_delta(old, new):
    import copy
    expected = copy.deepcopy(old)
    expected['modules']['samurai-mp2650']['sha256'] = HASHES[KO]
    expected['installed_files'][KO] = HASHES[KO]
    need(expected == new and old['installed_files'][KO] == OLD_CHARGER and
         old['installed_files'][SERVICE] == SERVICE_SHA, 'only two charger hash occurrences change')
    need(old['release'] == RELEASE and old['default_input_cap_ua'] == 900000 and old['default_charge_cap_ua'] == 250000 and
         old['source_budget_enforced'] is True, 'unchanged ABI and caps')


def source_limits(data):
    source, lim, s = data['source'], data['limits'], data['sample']
    kinds = re.findall(r'\[([^\]]+)\]', source['usb_type'])
    need(source['online'] == '1' and len(kinds) == 1, 'known online source')
    native, budget = lim['native_ua'], lim['source_budget_ua']
    need(type(native) is int and type(budget) is int and native == 500000 and
         ((kinds[0] == 'SDP' and budget == native) or (kinds[0] in ('CDP', 'DCP') and budget == 1500000) or
          (kinds[0] == 'C' and budget in (1500000, 3000000))), 'classified legal source/native permission')
    need(lim['input_ua'] == min(900000, budget) and lim['charge_ua'] == 250000 and s['budget_ua'] == budget,
         'existing managed physical limits and effective budget')


def _safe_sample(data):
    _r8_sample(data)
    s, p = data['sample'], data['protection']
    need(all(2000000 <= s.get(k, 0) <= 4600000 for k in ('cell1_uv', 'cell2_uv')) and
         4000000 <= s.get('pack_uv', 0) <= 9200000 and abs(s['cell1_uv'] + s['cell2_uv'] - s['pack_uv']) <= 200000,
         'complete consistent pack/cell sample')
    need(0 <= s.get('session_seconds', -1) < 36000 and 160 <= s.get('temp_decic', -999) < 440 and
         s.get('thermal_band') == 4, 'fresh NORMAL and nonexpired volatile cycle')
    need(data['protection_health'] == 'Good' and p.get('id') == 0x2719 and
         p.get('error') == p.get('safety') == p.get('pf') == 0 and p.get('operation', 0) & 0x300 == 0x300 and
         not p['operation'] & ((1 << 20) | (1 << 16) | 0x7c00) and p.get('manufacturing', 0) & 0x18 == 0x18 and
         not p['manufacturing'] & 0x8006, 'independent complete protection state')
    need(0 <= data['read_end'] - data['read_start'] <= 3 and
         0 <= time.clock_gettime(time.CLOCK_BOOTTIME) - data['read_end'] <= 1, 'bounded fresh observation')


def healthy(data, allow_full=True):
    mode = _r8_healthy(data, allow_full)
    source_limits(data)
    need(7425000 <= 2 * data['limits']['cv_uv'] <= 8725000, 'inherited pack CV ceiling')
    return mode


def continuity(before, current, allow_full=False):
    try:
        safe_sample(current)
        source_limits(current)
        need(before['source'] == current['source'] and before['limits'] == current['limits'], 'source, budget or limits changed')
        unchanged(before, current)
        if not allow_full:
            need(not any(current['sample'].get(k, 0) for k in ('logical_full', 'hold_requested', 'full_holding', 'full_cause')),
                 'new Full history cannot be erased by reloading')
    except Exception as error:
        raise UnsafeSample(detail(error), current) from error


def unchanged(before, after):
    _r8_unchanged(before, after)
    need(before['state']['driver'] == after['state']['driver'] == 'samurai-mp2650', 'actual managed charger client')
    need(before['mac_evidence'] == after['mac_evidence'], 'consumed MAC report or bound instance changed')
    need(before['identity'] == after['identity'], 'same current boot/guard/board/rootfs')


def preflight(request, device, request_raw=None):
    result = {'schema': 'samurai-charger-reattach-preflight-v1', 'transaction_id': request.get('transaction_id'),
              'request_sha256': sha(request_raw if request_raw is not None else device.request_raw),
              'identity_match': False, 'eligible': False, 'healthy_state': None, 'snapshot': None,
              'reason': None, 'passed': False, 'read_only': True, 'directory_or_lease_created': False}
    try:
        files, new = unpack_request(request)
        device.open_readonly(request)
        result['identity'] = device.identity(request)
        old_raw, mode = device.read_owned(MANIFEST)
        need(sha(old_raw) == OLD and mode == 0o600, 'exact old manifest')
        old = json.loads(old_raw); manifest_delta(old, new)
        need(sha(device.read_owned(KO)[0]) == OLD_CHARGER and device.read_owned(KO)[1] == 0o600, 'old charger disk identity')
        manager = device.manager(SERVICE_SHA)
        need(device.verify(manager) == old, 'read-only actual manager verify')
        device.notes_match(manager, old)
        snapshot = device.observe(manager)
        result['snapshot'] = snapshot
        mode = healthy(snapshot, True)
        unchanged(snapshot, snapshot)
        need(snapshot['notes'] == NOTES, 'exact old live notes')
        result['identity_after'] = device.identity(request)
        need(result['identity'] == result['identity_after'], 'preflight identity bracket')
        result.update(passed=True, identity_match=True, healthy_state=mode, eligible=mode == 'managed',
                      reason=None if mode == 'managed' else 'full_state_not_restorable')
    except Exception as error:
        result['reason'] = detail(error)
    finally:
        try: device.close()
        except Exception as error:
            result.update(passed=False, eligible=False, close_error=detail(error))
    return result


class Device(R8Device):
    def __init__(self, request_raw):
        super().__init__()
        self.request_raw = request_raw
        self.request = None
        self.mac_fd = None
        self.mac_baseline = None
        self.before = None

    def identity(self, request):
        comp = Path('/sys/firmware/devicetree/base/compatible').read_bytes()
        boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        result = {'boot_id': boot, 'version': os.uname().version,
                  'serial_sha256': sha(Path(SOC_SERIAL).read_bytes()), 'compatible_sha256': sha(comp),
                  'rootfs_sha256': sha(Path('/etc/samurai-rootfs-release').read_bytes())}
        need(os.geteuid() == 0 and os.uname().release == RELEASE and not sys.flags.optimize and
             b'realme,samurai' in comp.split(b'\0') and result == request['identity'], 'same actual IRQ kernel/board/rootfs')
        raw, mode = self.read_owned(request['adoption']['guard_path'])
        need(raw == (boot + '\n').encode() and sha(raw) == request['adoption']['guard_sha256'], 'actual IRQ adopted guard')
        return dict(result, guard_sha256=sha(raw))

    def board_client(self):
        client = Path('/sys/bus/i2c/devices/0-005c')
        need((client / 'name').read_text().strip() == 'mp2650' and
             (client / 'of_node').resolve().as_posix().endswith('/soc@0/geniqup@8c0000/i2c@884000/charger@5c') and
             (client / 'driver').resolve().as_posix() == '/sys/bus/i2c/drivers/samurai-mp2650' and
             Path('/sys/module/samurai_mp2650/parameters/control').read_text().strip() == 'Y', 'actual controlled board charger')

    def verify_carriers(self):
        for name, (length, expected) in CARRIERS.items():
            with open('/dev/disk/by-partlabel/' + name, 'rb', buffering=0) as stream:
                need(os.lseek(stream.fileno(), 0, os.SEEK_END) == length, 'exact carrier bytes')
                stream.seek(0); digest = hashlib.sha256(); remaining = length
                while remaining:
                    raw = stream.read(min(1048576, remaining)); need(raw, 'short carrier read')
                    digest.update(raw); remaining -= len(raw)
                need(digest.hexdigest() == expected, 'actual current carrier ' + name)

    def open_mac(self):
        need(Path(INSTANCE, 'driver').resolve().as_posix() == '/sys/bus/platform/drivers/samurai-gauge-protection', 'bound protection driver')
        self.mac_fd = os.open(Path(INSTANCE, 'mac_evidence'), os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        self.mac_baseline = self.mac_evidence()

    def mac_evidence(self):
        need(self.mac_fd is not None, 'held MAC evidence descriptor')
        held, current = os.fstat(self.mac_fd), Path(INSTANCE, 'mac_evidence').stat()
        need((held.st_dev, held.st_ino) == (current.st_dev, current.st_ino) and
             Path(INSTANCE, 'driver').resolve().as_posix() == '/sys/bus/platform/drivers/samurai-gauge-protection', 'same bound kernfs instance')
        os.lseek(self.mac_fd, 0, os.SEEK_SET); raw = os.read(self.mac_fd, 16384)
        need(0 < len(raw) < 16384 and raw.endswith(b'\n'), 'complete consumed MAC cache')
        first = dict(x.split('=', 1) for x in raw.decode().splitlines()[0].split())
        need(first.get('attempted') == first.get('terminal') == '1' and sha(raw) == MAC_CACHE_SHA,
             'preserve exact already-consumed actual MAC report only; no new capture')
        return {'raw_base64': base64.b64encode(raw).decode(), 'sha256': sha(raw), 'attribute_dev': held.st_dev,
                'attribute_inode': held.st_ino, 'instance_inode': Path(INSTANCE).stat().st_ino}

    def lock_existing(self, shared):
        self.lock = os.open(LOCK, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        info = os.fstat(self.lock)
        need(stat.S_ISREG(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022, 'existing protected charging lock')
        fcntl.flock(self.lock, (fcntl.LOCK_SH if shared else fcntl.LOCK_EX) | fcntl.LOCK_NB)

    def open_readonly(self, request):
        self.request = request
        self.identity(request); self.lock_existing(True); self.board_client(); self.open_mac(); self.verify_carriers()

    def begin(self, request):
        self.request = request
        self.identity(request); self.check_window(request)
        root = Path(ROOT) / request['transaction_id']
        info = root.lstat()
        need(stat.S_ISDIR(info.st_mode) and info.st_uid == 0 and stat.S_IMODE(info.st_mode) == 0o700 and not root.is_symlink(), 'owned unique transport directory')
        need(Path(__file__).resolve() == root / 'stage-worker.py' and sha(Path(__file__).read_bytes()) == request['worker_sha256'], 'executed worker source/path')
        self.lock_existing(False); self.board_client(); self.open_mac(); self.verify_carriers()
        self.out = root / 'device-update'; self.out.mkdir(mode=0o700, exist_ok=False)
        with (self.out / 'request-private.json').open('xb') as stream:
            stream.write(self.request_raw); stream.flush(); os.fsync(stream.fileno())
        ticks = int(Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()[19])
        self.log('process-private.json', dict(transaction_id=request['transaction_id'], boot_id=request['identity']['boot_id'],
                 pid=os.getpid(), start_ticks=ticks, argv=[x.decode() for x in Path('/proc/self/cmdline').read_bytes().split(b'\0') if x]))
        self.check_window(request)

    def check_window(self, request):
        self.identity(request)
        raw, mode = self.read_owned('/run/' + request['transaction_id'] + '-window-private.json')
        need(mode == 0o600, 'private current lease')
        lease = json.loads(raw)
        need(set(lease) == {'transaction_id', 'boot_id', 'token', 'owner', 'exclusive', 'camera_released', 'bluetooth_released',
                           'issued_boottime_s', 'expires_boottime_s'}, 'lease fields')
        now = time.clock_gettime(time.CLOCK_BOOTTIME)
        start, end = lease['issued_boottime_s'], lease['expires_boottime_s']
        need(type(start) in (int, float) and type(end) in (int, float) and math.isfinite(start) and math.isfinite(end) and
             0 <= start <= now < end <= start + 120 and lease['transaction_id'] == request['transaction_id'] and
             lease['boot_id'] == request['identity']['boot_id'] and lease['token'] == request['lease_token'] and
             lease['owner'] == 'charging' and all(lease[k] is True for k in ('exclusive', 'camera_released', 'bluetooth_released')),
             'unexpired same-boot coordinated lease at most120s')

    def observe(self, manager):
        start = time.clock_gettime(time.CLOCK_BOOTTIME)
        data = super().observe(manager)
        p = Path(INSTANCE)
        data['protection'] = {k: int(v, 0) for k, v in (x.split('=') for x in (p / 'protection_state').read_text().split())}
        data['protection_health'] = (manager['live'].PSY / 'samurai-gauge-protection/health').read_text().strip()
        data['identity'] = self.identity(self.request)
        data['mac_evidence'] = self.mac_evidence()
        need(data['mac_evidence'] == self.mac_baseline and all(data['notes'][k] == NOTES[k] and self.module_state(k) == 'live' for k in PROVIDERS),
             'providers and consumed MAC instance continuously retained')
        data.update(read_start=start, read_end=time.clock_gettime(time.CLOCK_BOOTTIME))
        return data

    def backup(self, files, before):
        self.before = before
        super().backup(files, before)

    def cap_inhibited(self, before):
        need(self.registers()['08'] & 0x18 == 8, 'cap only the new inhibited module')
        supply = Path('/sys/class/power_supply/mp2650-input')
        for field, value in [('input_current_limit', before['limits']['input_ua']), ('constant_charge_current', 250000)]:
            (supply / field).write_text(str(value) + '\n')
        r = self.registers()
        need(r['08'] & 0x18 == 8 and (r['02'] & 0x7f) * 50000 == 250000 and
             (r['00'] & 0x7f) * 50000 == (r['0f'] & 0x7f) * 50000 == before['limits']['input_ua'], 'inhibited safe caps read back')

    def manager_command(self, manager, meta, action):
        if action == 'start':
            # This is also used by the original exact rollback tail. Never
            # start after changed permission, Full or lost provider evidence.
            self.check_window(self.request)
            continuity(self.before, self.observe(manager), allow_full=False)
            for name in PROVIDERS:
                need(self.module_state(name) == 'live', 'manager must not reload a provider')
        return super().manager_command(manager, meta, action)

    def log(self, name, data):
        if self.out is not None:
            with (self.out / name).open('w') as stream:
                stream.write(json.dumps(data, indent=2) + '\n'); stream.flush(); os.fsync(stream.fileno())

    def close(self):
        if self.uncertain: return  # The same worker quarantines its original pending child.
        errors = []
        for attr in ('mac_fd', 'lock'):
            fd = getattr(self, attr)
            if fd is not None:
                try: os.close(fd)
                except OSError as error: errors.append(detail(error))
                setattr(self, attr, None)
        need(not errors, 'owned descriptor close errors: ' + repr(errors))


def main():
    parser = argparse.ArgumentParser(description='One explicit IRQ single-charger update; default source only.')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--preflight', action='store_true'); group.add_argument('--execute-stage', action='store_true')
    args = parser.parse_args()
    if not (args.preflight or args.execute_stage):
        print(json.dumps({'source_only': True, 'device_accessed': False, 'runtime_request_created': False})); return 0
    need(not sys.flags.optimize, 'non-optimized Python'); os.umask(0o077)
    raw = sys.stdin.buffer.read(120001); need(0 < len(raw) <= 120000, 'bounded explicit request')
    request = json.loads(raw); validate_request(request)
    device = Device(raw)
    try:
        answer = preflight(request, device, raw) if args.preflight else update(request, device)
        answer['request_sha256'] = sha(raw)
        print(json.dumps(answer), flush=True)
    except BaseException:
        if not device.uncertain: raise
        while True: time.sleep(1)  # A failed receipt/output must not release an unknown mutation.
    while device.uncertain:
        time.sleep(1)  # Original unknown child remains owned; never unload/reload/retry.
    return 0 if answer['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
