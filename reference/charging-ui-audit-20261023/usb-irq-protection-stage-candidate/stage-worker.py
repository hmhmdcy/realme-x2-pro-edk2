#!/usr/bin/python3
"""Default inert check; one adopted-Image502, disk-only charging cohort stage."""
from pathlib import Path
import argparse
import base64
import copy
import errno
import hashlib
import io
import json
import math
import os
import re
import runpy
import stat
import sys
import tarfile
import time
import uuid

sys.dont_write_bytecode = True
RELEASE = '7.3.0-rc6-rmx1931-samurai-k363+'
VERSION = '#502 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026'
ROOT = '/root/charging-management-20261023'
SERVICE = '/usr/sbin/samurai-charging'
MANAGER = '61451ffea87cca466dbbb2f1a2c6e7c05d0eee517479e8b019d43b1869355aa4'
STARTUP = '/usr/local/sbin/samurai-usb'
STARTUP_SHA = '2a364e12d72229ef7b0ddfd7620d5ff434b97eaf93eb60899fd24a03b5b9a54a'
MANIFEST = '/usr/share/samurai-charging/manifest.json'
MODULE_ROOT = '/lib/modules/' + RELEASE + '/extra/samurai-charging/'
USB = MODULE_ROOT + 'samurai-usb-input.ko'
PROTECTION = MODULE_ROOT + 'samurai-gauge-protection.ko'
CHARGER = MODULE_ROOT + 'samurai-mp2650.ko'
ORDER = [USB, PROTECTION, MANIFEST]
LOCK = '/run/lock/samurai-charging.lock'
OLD = '320316c3d93c1dbcaae29440f1f17d72c75e4994d656a9da9fcd5aeb93c10a1f'
NEW = '5fca8e5a0795325bd780b7965579068c7edc35fa7da12bac357bb30bbde69417'
COHORT = '3d5b78bc4c7a6b476bfb97c2fbad3e0d76497c94e13bd755a8e4aaa0b032a07b'
PAYLOAD = '9dee06ddea1190ea70a188efe47742afb8b104bf53ac31cb57598f079ee4fb3c'
OLD_FILES = {USB: '7d4e0f948b993a6e0cc9459bac4ade2db2fe7b88ce7b7d462ea34bcb933c4f70',
             PROTECTION: '75b97e0d6b906ec600171ce68adec6f25a91556758f76bbf3d563cf831e783c7', MANIFEST: OLD}
NEW_FILES = {USB: '7cbf10c0f74609effb415c30145e58b0fbe554511ef55a96baeeaf367c94ff5f',
             PROTECTION: '7848cfab264dde1f7f02b24b8022b951d4f3a604eba120b313bac23d0f4a3044', MANIFEST: NEW}
OLD_NOTES = {'samurai-usb-input': 'f0edb792d30ee1168ee1793e89707aa48b2085c845acde8f472f2c13a03804b0',
             'samurai-gauge-protection': '930e0e1f34e89e4e06a7632ca14a26181975f9f35e55a51209af71480b56fe76',
             'samurai-mp2650': 'f4d5768a4250b901ea956560d9c6b4b1dd32ac80893cbbd31609d9c032c4680d'}
BOOT = '97811cc4ae13b36fec98b2eae7cd54a4f12bca988864df0f3d8f663a8c67f695'
LOGDUMP = 'ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1'
CHECKS = {'identity', 'partitions', 'R8_install', 'charging', 'camera481',
          'EUD_producers', 'instant_gauge', 'services_faults', 'identity_after'}

def need(ok, message):
    if not ok:
        raise RuntimeError(message)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def detail(error):
    return type(error).__name__ + ': ' + str(error)

def encode(value):
    return (json.dumps(value, indent=2) + '\n').encode()

def read_owned(path, limit=4_000_000):
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        need(stat.S_ISREG(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022,
             'regular root-owned protected file: ' + str(path))
        need(0 <= info.st_size <= limit, 'bounded regular file: ' + str(path))
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(limit + 1)
        need(len(raw) <= limit, 'growing file bound')
        return raw, stat.S_IMODE(info.st_mode)
    finally:
        os.close(fd)

def unpack(request):
    need(set(request) == {'schema', 'transaction_id', 'cohort_delivery_sha256', 'payload_sha256',
                         'payload_base64', 'worker_sha256', 'identity', 'adoption', 'lease_token'}, 'request keys')
    need(request['schema'] == 'samurai-usb-irq-protection-stage-request-v1', 'request schema')
    need(re.fullmatch(r'usb-irq-protection-stage-[a-z0-9-]{8,48}', request['transaction_id']), 'new unique stage name')
    need(request['cohort_delivery_sha256'] == COHORT and request['payload_sha256'] == PAYLOAD, 'exact frozen cohort')
    identity = request['identity']
    need(set(identity) == {'boot_id', 'version', 'serial_sha256', 'compatible_sha256', 'rootfs_sha256'}, 'identity keys')
    need(str(uuid.UUID(identity['boot_id'])) == identity['boot_id'] and identity['version'] == VERSION, 'actual Image502 boot identity')
    for value in [identity['serial_sha256'], identity['compatible_sha256'], identity['rootfs_sha256'], request['worker_sha256']]:
        need(re.fullmatch(r'[0-9a-f]{64}', value), 'explicit identity hash')
    adoption = request['adoption']
    need(set(adoption) == {'transaction_id', 'guard_path', 'guard_sha256', 'postboot_raw_sha256'}, 'adoption keys')
    need(re.fullmatch(r'image502-[a-z0-9-]{8,64}', adoption['transaction_id']), 'Image502 adoption transaction')
    need(adoption['guard_path'] == '/var/lib/samurai/' + adoption['transaction_id'] + '-adopted/boot-id-private.txt', 'derived adopted guard path')
    for key in ['guard_sha256', 'postboot_raw_sha256']:
        need(re.fullmatch(r'[0-9a-f]{64}', adoption[key]), 'actual adopted proof hash')
    need(re.fullmatch(r'[0-9a-f]{48}', request['lease_token']), 'unique lease token')
    raw = base64.b64decode(request['payload_base64'], validate=True)
    need(len(raw) == 51736 and sha(raw) == PAYLOAD, 'exact actual three-file payload')
    files = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as tar:
        members = tar.getmembers()
        need(len(members) == 3, 'exact three members')
        for member in members:
            target = '/' + member.name
            need(target in NEW_FILES and target not in files and member.name == target.lstrip('/'), 'member path')
            need(member.isfile() and member.mode == 0o600 and member.uid == member.gid == 0 and
                 member.uname == member.gname == 'root' and member.mtime == 0 and not member.pax_headers, 'member metadata')
            raw_file = tar.extractfile(member).read()
            need(sha(raw_file) == NEW_FILES[target], 'member bytes')
            files[target] = raw_file
    return files, json.loads(files[MANIFEST])

def manifest_delta(old, new):
    expected = copy.deepcopy(old)
    expected['adapter_revision'] = 'usb-irq-protection-observer-01'
    for name, target in [('samurai-usb-input', USB), ('samurai-gauge-protection', PROTECTION)]:
        need(old['modules'][name] == {'target': target, 'sha256': OLD_FILES[target]}, 'old module identity')
        expected['modules'][name]['sha256'] = NEW_FILES[target]
        expected['installed_files'][target] = NEW_FILES[target]
    need(expected == new and old['adapter_revision'] == 'r8' and old['release'] == RELEASE, 'minimal new manifest')
    need(old['installed_files'][SERVICE] == MANAGER and old['modules']['samurai-mp2650']['sha256'] ==
         '10ec06fb9d798d72e08495617cfc04e7e49c77e536a12f205053e9cdbfa6297f', 'retained manager/charger')
    need(old['default_input_cap_ua'] == 900000 and old['default_charge_cap_ua'] == 250000 and
         old['source_budget_enforced'] is True, 'retained caps/source authority')

def validate_adoption(proof, request):
    result, raw = proof['result'], proof['raw']
    need(result['passed'] is True and result['read_only'] is True and result['hardware_writes'] == 0 and
         not result['errors'] and set(result['checks']) == CHECKS and
         all(item.get('ready', True) is True for item in result['checks'].values()), 'actual complete adoption validation')
    need(proof['postboot_raw_sha256'] == request['adoption']['postboot_raw_sha256'], 'original passed postboot binding')
    before = raw['identity_before']
    need(before == raw['identity_after'], 'adoption identity complete')
    identity = request['identity']
    need(before['boot_id'] == identity['boot_id'] and before['uname']['version'] == VERSION and
         before['uname']['release'] == RELEASE and before['uname']['machine'] == 'aarch64' and before['taint'] == '0', 'adopted kernel/boot')
    need(before['serial_sha256'] == identity['serial_sha256'] and before['rootfs']['sha256'] == identity['rootfs_sha256'] and
         sha(base64.b64decode(before['compatible_b64'], validate=True)) == identity['compatible_sha256'], 'adopted board/rootfs')
    need(raw['boot_partition']['sha256'] == BOOT and raw['boot_partition']['bytes'] == 100663296 and
         raw['logdump_partition']['sha256'] == LOGDUMP and raw['logdump_partition']['bytes'] == 67108864, 'adopted old boot/Image502 carrier')
    # The frozen collector deliberately strips text; its separate file fact
    # hashes the original bytes including the final newline.
    need(raw['manifest']['sha256'] == OLD and json.loads(raw['manifest_text'])['adapter_revision'] == 'r8', 'adopted R8 disk')
    need(all(raw['charging_modules'][name]['loaded_note_sha256'] == digest for name, digest in OLD_NOTES.items()), 'adopted R8 notes')

def safe_sample(data, now):
    s = data['sample']
    need(s.get('valid') == s.get('protection_ok') == s.get('online') == 1 and
         s.get('shadow') == 0 and 0 <= s.get('age_ms', -1) <= 3000, 'fresh complete online protection sample')
    need(all(s.get(k, -1) == 0 for k in ['error', 'stop_error', 'latched', 'fault', 'source_inhibit',
                                       'cycle_timeout', 'thermal_inhibit', 'gauge_charge_stop']), 'no fault/timeout/gauge or thermal stop')
    need('flags' in s and not s['flags'] & 0xc000 and 0 <= s.get('session_seconds', -1) < 36000, 'safe raw flags/session')
    need(all(2000000 <= s.get(key, 0) <= 4600000 for key in ['cell1_uv', 'cell2_uv']) and
         4000000 <= s.get('pack_uv', 0) <= 9200000 and
         abs(s['cell1_uv'] + s['cell2_uv'] - s['pack_uv']) <= 200000, 'safe complete pack/cell values')
    need(160 <= s.get('temp_decic', -999) < 440 and s.get('thermal_band') == 4, 'known safe NORMAL window')
    need(0 <= data['read_end'] - data['read_start'] <= 3 and 0 <= now - data['read_end'] <= 1, 'fresh bounded observation')
    p = data['protection']
    need(data['protection_health'] == 'Good' and p.get('id') == 0x2719 and p.get('error') == p.get('safety') == p.get('pf') == 0,
         'independent fresh protection state')
    need(p.get('operation', 0) & 0x300 == 0x300 and not p['operation'] & ((1 << 20) | (1 << 16) | 0x7c00) and
         p.get('manufacturing', 0) & 0x18 == 0x18 and not p['manufacturing'] & 0x8006, 'sealed autonomous factory protection')
    need(data['notes'] == OLD_NOTES and data['openrc_started'] is True, 'old resident modules and service retained')

def healthy(data, now):
    safe_sample(data, now)
    s, r, lim = data['sample'], data['state']['registers'], data['limits']
    full_fields = ['logical_full', 'hold_requested', 'full_holding', 'full_cause']
    full = (s.get('logical_full') == s.get('hold_requested') == s.get('full_holding') == 1 and
            s.get('full_cause') in (1, 2, 3) and s.get('desired_enable') == 0 and s['session_seconds'] == 0)
    if any(s.get(key, 0) for key in full_fields):
        need(full and r['08'] & 0x18 == 0, 'precise healthy Full holding')
    else:
        need(s.get('desired_enable') == 1 and r['08'] & 0x18 == 0x10, 'managed CHG readback')
    source = data['source']
    active = re.findall(r'\[([^\]]+)\]', source['usb_type'])
    need(len(active) == 1 and source['online'] == '1', 'real known online source')
    budget, native = int(source['current_max']), int(source['input_current_limit'])
    need(native == 500000 and ((active[0] == 'SDP' and budget == 500000) or
         (active[0] in ['CDP', 'DCP'] and budget == 1500000) or
         (active[0] == 'C' and budget in [1500000, 3000000])), 'actual 500 native and classified budget')
    need(s['budget_ua'] == budget and lim['input_ua'] == min(900000, budget) and lim['charge_ua'] == 250000,
         'existing input/charge policy limits')
    need((r['00'] & 0x7f) * 50000 == (r['0f'] & 0x7f) * 50000 == lim['input_ua'] and
         (r['02'] & 0x7f) * 50000 == lim['charge_ua'], 'actual hardware limits')
    need(7425000 <= lim['cv_pack_uv'] <= 8725000 and lim['cv_pack_uv'] ==
         2 * (3712500 + ((r['04'] & 0x7e) >> 1) * 12500), 'unchanged inherited CV cap')
    return 'healthy_full_holding' if full else 'healthy_managed'

def environment(data):
    state = data['state']
    need(state['taint'] == '0' and state['driver'] == 'samurai-mp2650' and
         len(state['camera_pm']) == 4 and all(v == 'suspended' for v in state['camera_pm'].values()), 'idle camera and managed charger')
    m2m = json.loads(state['m2m'])
    need(all(m2m.get(k) == 0 for k in ['users', 'orphans', 'jobs', 'first_error']) and
         all(m2m.get(k) is False for k in ['running', 'fatal', 'pinned']), 'idle camera m2m')
    services = state['services']
    need(len(services) == 4 and {s['comm'] for s in services} == {'phoc', 'phosh', 'pipewire', 'wireplumber'} and
         all(s['uid'] == 10000 and s['pid'] > 0 for s in services), 'actual four session processes')

def unchanged(before, after):
    environment(before)
    environment(after)
    for key in ['boot_id', 'release', 'camera_pm', 'm2m', 'services', 'taint', 'driver']:
        need(before['state'][key] == after['state'][key], 'environment changed: ' + key)
    need(before['notes'] == after['notes'] == OLD_NOTES and before['source'] == after['source'] and
         before['limits'] == after['limits'], 'resident/source/limits retained')
    br, ar = before['state']['registers'], after['state']['registers']
    need(set(br) == set(ar) and '14' not in br, 'known non-destructive register set')
    for key in br:
        if key == '08':
            need(ar[key] == (br[key] & ~0x18) | 8, 'only original INHIBIT bits may change')
        elif key != '13':
            need(br[key] == ar[key], 'configuration changed: ' + key)
    need(ar['13'] & 2, 'ACOK retained')

class AtomicFailure(RuntimeError):
    def __init__(self, message, stage):
        super().__init__(message)
        self.stage = stage

def claim_result_dir(base):
    out = Path(base) / 'device-stage'
    out.mkdir(mode=0o700, exist_ok=False)
    return out

def validate_lease(lease, mode, request, now):
    need(mode == 0o600 and set(lease) == {'transaction_id', 'boot_id', 'token', 'owner', 'exclusive',
         'camera_released', 'bluetooth_released', 'issued_boottime_s', 'expires_boottime_s'}, 'lease exact schema/mode')
    need(lease['transaction_id'] == request['transaction_id'] and lease['boot_id'] == request['identity']['boot_id'] and
         lease['token'] == request['lease_token'] and lease['owner'] == 'charging' and
         lease['exclusive'] is lease['camera_released'] is lease['bluetooth_released'] is True, 'explicit coordinated device window')
    issued, expires = lease['issued_boottime_s'], lease['expires_boottime_s']
    need(all(type(x) in [int, float] and math.isfinite(x) for x in [issued, expires]) and
         issued <= now < expires and 0 < expires - issued <= 120, 'live BOOTTIME lease <=120s')

def atomic_replace(path, raw, transaction, expected_old, record, ops=os, reader=read_owned):
    """Synchronous exclusive temp -> fsync -> replace -> directory fsync. No retry/rollback."""
    path = Path(path)
    temporary = path.with_name('.' + path.name + '.' + transaction + '.next')
    old, mode = reader(path)
    need(mode == 0o600 and sha(old) == expected_old, 'target must still be exact old bytes/mode')
    fd = directory = failure = None
    phase = 'temp-open'
    try:
        record({'step': phase, 'target': str(path), 'temporary': str(temporary)})
        fd = ops.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        phase = 'temp-write'
        offset = 0
        while offset < len(raw):
            count = ops.write(fd, raw[offset:])
            need(type(count) is int and 0 < count <= len(raw) - offset, 'invalid/short regular write')
            offset += count
        ops.fchmod(fd, 0o600)
        phase = 'file-fsync'
        ops.fsync(fd)
        ops.close(fd)
        fd = None
        record({'step': 'temp-fsynced', 'target': str(path), 'new_sha256': sha(raw)})
        phase = 'rename'
        ops.replace(temporary, path)
        record({'step': 'renamed', 'target': str(path), 'new_sha256': sha(raw)})
        phase = 'directory-fsync'
        directory = ops.open(path.parent, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
        ops.fsync(directory)
        ops.close(directory)
        directory = None
        phase = 'readback'
        actual, mode = reader(path)
        need(actual == raw and mode == 0o600, 'new target exact readback')
        record({'step': 'complete', 'target': str(path), 'new_sha256': sha(actual)})
        return {'sha256': sha(actual), 'mode': '0600', 'file_and_directory_fsynced': True}
    except BaseException as error:
        failure = AtomicFailure(detail(error), phase)
        raise failure from error
    finally:
        cleanup = []
        for descriptor in [fd, directory]:
            if descriptor is not None:
                try:
                    ops.close(descriptor)
                except BaseException as error:
                    cleanup.append(detail(error))
        if cleanup:
            if failure is not None:
                failure.args = (str(failure) + '; cleanup=' + repr(cleanup),)
            else:
                raise AtomicFailure('descriptor cleanup=' + repr(cleanup), 'cleanup')
        # A failed temp is deliberately retained. No unowned temp is removed.

def stage(request, device, execute=False):
    need(execute, 'explicit --execute-stage only')
    result = {'schema': 'samurai-usb-irq-protection-stage-result-v1', 'transaction_id': request.get('transaction_id'),
              'cohort_delivery_sha256': COHORT, 'old_manifest_sha256': OLD, 'new_manifest_sha256': NEW,
              'payload_sha256': PAYLOAD, 'phase': 'rejected', 'status': 'not_staged', 'staged': False,
              'runtime_pending': True, 'terminal': True, 'stop_verified': False, 'primary_error': None,
              'disk_state': 'not_inspected', 'automatic_rollback_or_replay': False, 'resident_notes_expected': OLD_NOTES,
              'stop_error': None}
    phase = 'request'
    before = None
    try:
        files, new = unpack(request)
        phase = 'begin'
        device.begin(request)
        device.event({'step': 'preflight'})
        phase = 'preflight'
        backups = {name: device.read_owned(name) for name in ORDER}
        for name, (raw, mode) in backups.items():
            need(mode == 0o600 and sha(raw) == OLD_FILES[name], 'exact old disk file/mode: ' + name)
        old = json.loads(backups[MANIFEST][0])
        manifest_delta(old, new)
        manager = device.manager()
        need(device.verify(manager) == old, 'fresh original manager.verify R8')
        device.notes_match(manager, old)
        device.verify_partitions()
        before = device.observe(manager)
        result['before_healthy_mode'] = healthy(before, device.now())
        # Existing configuration is allowed to be enabled or precise Full.
        environment(before)
        device.backup(backups, before)
        device.check_window(request)
        phase = 'synchronous-stop'
        device.event({'step': phase})
        device.stop(manager, old)
        need(device.registers(manager)['08'] & 0x18 == 8, 'original manager stop INHIBIT readback')
        result['stop_verified'] = True
        phase = 'stopped-proof'
        device.check_window(request)
        paused = device.observe(manager)
        safe_sample(paused, device.now())
        unchanged(before, paused)
        device.log('stopped-private.json', paused)
        for name in ORDER:
            phase = {USB: 'replace-usb', PROTECTION: 'replace-protection', MANIFEST: 'replace-manifest'}[name]
            device.check_window(request)
            device.event({'step': phase, 'target': name})
            device.replace(name, files[name])
        phase = 'staged-proof'
        device.check_window(request)
        need(device.verify(manager) == new, 'manager verifies new disk only')
        device.notes_match(manager, old, backups=True)
        after = device.observe(manager)
        safe_sample(after, device.now())
        unchanged(before, after)
        need(after['state']['registers']['08'] & 0x18 == 8, 'INHIBIT retained')
        device.check_window(request)
        device.log('after-private.json', after)
        result.update(staged=True, phase='staged', status='staged/runtime_pending', disk_state='all_new_fsynced',
                      old_resident_notes=after['notes'], configuration='INHIBIT retained',
                      source_boot_id=before['state']['boot_id'], source_version=VERSION,
                      source_guard_path=request['adoption']['guard_path'],
                      adoption_fresh_validation_sha256=device.adoption_proof_sha256,
                      activation_attempted=False, new_module_loaded=False, capture_issued=False)
    except BaseException as error:
        result['phase'] = 'rejected' if phase in ['request', 'begin', 'preflight'] else 'failed'
        result['primary_error'] = {'phase': phase, 'error': detail(error)}
        if phase == 'synchronous-stop':
            result['stop_error'] = detail(error)
        if isinstance(error, AtomicFailure):
            result['primary_error']['atomic_stage'] = error.stage
        result['status'] = 'failed_preserved_no_replay'
    finally:
        try:
            device.finish(result)
        except BaseException as error:
            result['receipt_error'] = detail(error)
            result['staged'] = False
            result['phase'] = 'failed'
            result['status'] = 'receipt_failure_inspect_same_worker'
        try:
            device.close()
        except BaseException as error:
            result['close_error'] = detail(error)
            result['staged'] = False
            result['phase'] = 'failed'
            result['status'] = 'close_failure_inspect_same_worker'
        try:
            device.publish_result(result)
        except BaseException as error:
            result['receipt_error'] = detail(error)
            result['staged'] = False
            result['phase'] = 'failed'
            result['status'] = 'receipt_failure_inspect_same_worker'
    return result

class Device:
    def __init__(self):
        self.out = self.lock = self.journal = None
        self.events = []
        self.request = None
        self.adoption_proof_sha256 = None

    def now(self):
        return time.clock_gettime(time.CLOCK_BOOTTIME)

    def read_owned(self, name):
        return read_owned(name)

    def check_window(self, request):
        identity, adoption = request['identity'], request['adoption']
        need(os.uname().release == RELEASE and os.uname().version == identity['version'] == VERSION,
             'current exact Image502 kernel')
        need(Path('/proc/sys/kernel/random/boot_id').read_text().strip() == identity['boot_id'], 'same actual boot')
        compatible = Path('/sys/firmware/devicetree/base/compatible').read_bytes()
        serial = Path('/sys/devices/soc0/serial_number').read_bytes()
        need(serial.strip() and sha(serial) == identity['serial_sha256'] and sha(compatible) == identity['compatible_sha256'] and
             b'realme,samurai' in compatible.split(b'\0'), 'exact SoC identity')
        need(sha(read_owned('/etc/samurai-rootfs-release')[0]) == identity['rootfs_sha256'], 'same rootfs release')
        guard, mode = read_owned(adoption['guard_path'])
        need(mode == 0o600 and guard == (identity['boot_id'] + '\n').encode() and sha(guard) == adoption['guard_sha256'], 'actual adopted guard')
        raw, mode = read_owned('/run/' + request['transaction_id'] + '-window-private.json')
        validate_lease(json.loads(raw), mode, request, self.now())

    def begin(self, request):
        import fcntl
        need(os.geteuid() == 0 and not sys.flags.optimize, 'root/non-optimized interpreter')
        self.request = request
        base = Path(ROOT) / request['transaction_id']
        info = base.lstat()
        need(stat.S_ISDIR(info.st_mode) and info.st_uid == 0 and stat.S_IMODE(info.st_mode) == 0o700 and
             not base.is_symlink(), 'owned unique host transaction directory')
        worker = base / 'stage-worker.py'
        need(Path(__file__).resolve() == worker and sha(read_owned(worker)[0]) == request['worker_sha256'], 'exact uploaded worker path/hash')
        self.out = claim_result_dir(base)
        self.journal = (self.out / 'journal-private.jsonl').open('xb')
        fields = Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()
        argv = Path('/proc/self/cmdline').read_bytes().rstrip(b'\0').split(b'\0')
        self.log('process-private.json', {'pid': os.getpid(), 'start_ticks': int(fields[19]),
                 'argv': [x.decode() for x in argv], 'worker_sha256': request['worker_sha256'],
                 'transaction_id': request['transaction_id'], 'boot_id': request['identity']['boot_id']})
        self.log('request-private.json', {k: v for k, v in request.items() if k != 'payload_base64'})
        self.check_window(request)
        self.lock = os.open(LOCK, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        info = os.fstat(self.lock)
        need(info.st_uid == 0 and stat.S_ISREG(info.st_mode) and not info.st_mode & 0o022, 'original service lock identity')
        fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.check_window(request)
        need(Path('/sys/bus/i2c/devices/0-005c/name').read_text().strip() == 'mp2650' and
             Path('/sys/bus/i2c/devices/0-005c/of_node').resolve().as_posix().endswith('/soc@0/geniqup@8c0000/i2c@884000/charger@5c'), 'actual charger client')
        need(Path('/sys/module/bq27xxx_battery/parameters/samurai_instant_current').read_text().strip() == 'Y', 'instant-current gate enabled')
        proof_raw = read_owned(Path(request['adoption']['guard_path']).parent / 'fresh-validation-private.json')[0]
        validate_adoption(json.loads(proof_raw), request)
        self.adoption_proof_sha256 = sha(proof_raw)
        self.log('adoption-proof-private.json', {'actual_fresh_validation_sha256': self.adoption_proof_sha256,
                 'postboot_raw_sha256': request['adoption']['postboot_raw_sha256'], 'guard_sha256': request['adoption']['guard_sha256']})

    def manager(self):
        need(sha(read_owned(SERVICE)[0]) == MANAGER and sha(read_owned(STARTUP)[0]) == STARTUP_SHA, 'unchanged installed manager/startup500')
        manager = runpy.run_path(SERVICE)
        need(sha(read_owned(SERVICE)[0]) == MANAGER, 'manager stable while loading')
        need(0x14 not in manager['live'].REGS, 'do not consume REG14')
        return manager

    def verify(self, manager):
        need(sha(read_owned(SERVICE)[0]) == MANAGER, 'fresh manager identity')
        return manager['verify']()

    def notes_match(self, manager, meta, backups=False):
        for name, entry in meta['modules'].items():
            module = name.replace('-', '_')
            need(Path('/sys/module', module, 'initstate').read_text().strip() == 'live', 'old module remains live')
            path = self.out / (Path(entry['target']).name + '.before') if backups and entry['target'] in ORDER else Path(entry['target'])
            manager['loaded_matches'](path, module)
            need(sha(Path('/sys/module', module, 'notes/.note.gnu.build-id').read_bytes()) == OLD_NOTES[name], 'old resident exact note')

    def verify_partitions(self):
        for name, length, expected in [('boot', 100663296, BOOT), ('logdump', 67108864, LOGDUMP)]:
            fd = os.open('/dev/disk/by-partlabel/' + name, os.O_RDONLY | os.O_CLOEXEC)
            try:
                need(os.lseek(fd, 0, os.SEEK_END) == length, 'exact carrier length')
                os.lseek(fd, 0, os.SEEK_SET)
                digest, remaining = hashlib.sha256(), length
                while remaining:
                    raw = os.read(fd, min(1048576, remaining))
                    need(raw, 'short read-only carrier')
                    digest.update(raw)
                    remaining -= len(raw)
                need(digest.hexdigest() == expected, 'actual current carrier: ' + name)
            finally:
                os.close(fd)

    def registers(self, manager):
        return manager['live'].registers()

    def observe(self, manager):
        live, start = manager['live'], self.now()
        state = live.state()
        source = {key: (live.PSY / 'samurai-usb-input' / key).read_text().strip()
                  for key in ['online', 'usb_type', 'current_max', 'input_current_limit']}
        supply = live.PSY / 'mp2650-input'
        protection = Path('/sys/devices/platform/samurai-gauge-protection/protection_state').read_text()
        result = {'read_start': start, 'state': state, 'sample': manager['sample'](), 'source': source,
                  'notes': {name: sha(Path('/sys/module', name.replace('-', '_'), 'notes/.note.gnu.build-id').read_bytes()) for name in OLD_NOTES},
                  'openrc_started': Path('/run/openrc/started/samurai-charging').exists(),
                  'protection': {k: int(v, 0) for k, v in (x.split('=') for x in protection.split())},
                  'protection_health': (live.PSY / 'samurai-gauge-protection/health').read_text().strip(),
                  'limits': {'input_ua': int((supply / 'input_current_limit').read_text()),
                             'charge_ua': int((supply / 'constant_charge_current').read_text()),
                             'cv_pack_uv': int((supply / 'constant_charge_voltage').read_text())}}
        result['read_end'] = self.now()
        return result

    def stop(self, manager, old):
        need(sha(read_owned(SERVICE)[0]) == MANAGER, 'unchanged stop code')
        # The caller holds the service flock. Never call rc-service recursively.
        answer = manager['command'](old, 'stop')
        need(answer.get('managed') is True and answer.get('requested') == 'inhibit-charge', 'actual original synchronous stop')

    def backup(self, files, before):
        for target, (raw, mode) in files.items():
            need(mode == 0o600, 'exact original modes')
            self.write_new(self.out / (Path(target).name + '.before'), raw)
        self.log('before-private.json', before)
        self.log('files-before-private.json', {target: {'sha256': sha(raw), 'mode': '0600', 'bytes': len(raw)} for target, (raw, _) in files.items()})

    def replace(self, name, raw):
        need(name in ORDER and sha(raw) == NEW_FILES[name], 'only exact new cohort target')
        return atomic_replace(name, raw, self.request['transaction_id'], OLD_FILES[name], self.event)

    def event(self, value):
        self.events.append(value)
        if self.journal is not None:
            self.journal.write((json.dumps(value) + '\n').encode())
            self.journal.flush()
            os.fsync(self.journal.fileno())

    def write_new(self, path, raw):
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fchmod(stream.fileno(), 0o600)
            os.fsync(stream.fileno())
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)

    def log(self, name, value):
        self.write_new(self.out / name, encode(value))

    def finish(self, result):
        if self.out is None:
            return
        files, labels = {}, []
        for name in ORDER:
            try:
                raw, mode = self.read_owned(name)
                digest = sha(raw)
                label = 'old' if mode == 0o600 and digest == OLD_FILES[name] else 'new' if mode == 0o600 and digest == NEW_FILES[name] else 'unexpected'
                files[name] = {'sha256': digest, 'mode': oct(mode), 'classification': label,
                               'old_sha256': OLD_FILES[name], 'new_sha256': NEW_FILES[name]}
            except BaseException as error:
                label = 'unknown'
                files[name] = {'error': detail(error), 'classification': label,
                               'old_sha256': OLD_FILES[name], 'new_sha256': NEW_FILES[name]}
            labels.append(label)
        result['final_files'] = files
        temporary = {}
        for name in ORDER:
            path = Path(name).with_name('.' + Path(name).name + '.' + self.request['transaction_id'] + '.next')
            try:
                raw, mode = self.read_owned(path)
                temporary[name] = {'path': str(path), 'state': 'retained', 'sha256': sha(raw),
                                   'bytes': len(raw), 'mode': oct(mode), 'expected_new_sha256': NEW_FILES[name]}
            except FileNotFoundError:
                temporary[name] = {'path': str(path), 'state': 'absent'}
            except BaseException as error:
                temporary[name] = {'path': str(path), 'state': 'unknown', 'error': detail(error)}
        result['temporary_files'] = temporary
        if all(label == 'old' for label in labels):
            result['disk_state'] = 'all_old'
        elif all(label == 'new' for label in labels):
            result['disk_state'] = 'all_new_fsynced' if result['staged'] else 'all_new_known_durability_or_acceptance_unproved'
        elif set(labels) <= {'old', 'new'}:
            result['disk_state'] = 'partial_known'
        else:
            result['disk_state'] = 'unknown_inspect_before_boot'
        result['unknown_write_state'] = any(label in ['unknown', 'unexpected'] for label in labels)
        if result['staged'] and (result['disk_state'] != 'all_new_fsynced' or
                                any(row['state'] != 'absent' for row in temporary.values())):
            result.update(staged=False, phase='failed', status='final_readback_changed_inspect_same_worker')
        self.log('events-private.json', self.events)

    def publish_result(self, result):
        if self.out is not None:
            self.log('result.json', result)

    def close(self):
        errors = []
        if self.journal is not None:
            try:
                self.journal.close()
            except BaseException as error:
                errors.append(detail(error))
            self.journal = None
        if self.lock is not None:
            try:
                os.close(self.lock)
            except BaseException as error:
                errors.append(detail(error))
            self.lock = None
        need(not errors, 'cleanup errors: ' + repr(errors))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-stage', action='store_true')
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    need(not (args.check_only and args.execute_stage), 'choose check-only or execute')
    if not args.execute_stage:
        print(json.dumps({'check_only': True, 'device_accessed': False, 'cohort_delivery_sha256': COHORT,
                          'payload_sha256': PAYLOAD, 'required_version': VERSION, 'runtime_activation': False}))
        return 0
    need(not sys.flags.optimize, 'non-optimized original manager assertions required')
    os.umask(0o077)
    raw = sys.stdin.buffer.read(100001)
    need(len(raw) <= 100000, 'request byte bound')
    result = stage(json.loads(raw), Device(), execute=True)
    print(json.dumps(result), flush=True)
    return 0 if result['staged'] and not result.get('receipt_error') and not result.get('close_error') else 1

if __name__ == '__main__':
    raise SystemExit(main())
