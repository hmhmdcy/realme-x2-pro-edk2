"""One current-IRQ disk-only USB stage. Default source only; no child or module operation."""
from pathlib import Path
import argparse,base64,copy,fcntl,hashlib,io,json,math,os,re,runpy,stat,sys,tarfile,time,uuid
sys.dont_write_bytecode=True
RELEASE='7.3.0-rc6-rmx1931-samurai-k363+'
VERSION='#502 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026'
ROOT='/root/charging-management-20261023'
SERVICE='/usr/sbin/samurai-charging'
SERVICE_SHA='61451ffea87cca466dbbb2f1a2c6e7c05d0eee517479e8b019d43b1869355aa4'
SOC_SERIAL='/sys/devices/soc0/serial_number'
LOCK='/run/lock/samurai-charging.lock'
INSTANCE='/sys/devices/platform/samurai-gauge-protection'
MANIFEST='/usr/share/samurai-charging/manifest.json'
MODULE_ROOT='/lib/modules/'+RELEASE+'/extra/samurai-charging/'
KO=MODULE_ROOT+'samurai-mp2650.ko'
USB=MODULE_ROOT+'samurai-usb-input.ko'
ORDER=[USB,MANIFEST]
OLD='18e8a1049a2c497fbc47ace50f8319aefccd63a9cd1ce5a7e9ef06916773b4e5'
USB_OLD='7cbf10c0f74609effb415c30145e58b0fbe554511ef55a96baeeaf367c94ff5f'
USB_NEW='d04608ad80a90288c32705bbfcfd3855738d7b09f207ae2aa4268f7c0a167037'
PROVIDERS=('samurai-usb-input','samurai-gauge-protection')
NOTES={'samurai-usb-input':'a845cd08aa415ca01ad4791b8c66047a927577e76439e632c73b6b4e2cff8c6d',
       'samurai-gauge-protection':'fc0d253d556b6ba656db263aaa50c37e3af2c7fe115b67e6b02641ae8b5733ec',
       'samurai-mp2650':'fe15a2fcb618dee0b161952cd66c32f2d5ecc9c8d50b0975242da5353c472016'}
MAC_CACHE_SHA='02c98143301bb5db896c6f535f490495428df8b8c6fd6ab3cdc69ca507a545a8'
CARRIERS={'boot':(100663296,'eddadec33fcd1d114c45af76cb9fc6d6b5f1de2c81c0e9fada099c5b884f6e06'),
          'logdump':(67108864,'ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1')}

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

def validate_lease(lease, mode, request, now):
    need(mode == 0o600 and set(lease) == {'transaction_id', 'boot_id', 'token', 'owner', 'exclusive',
         'camera_released', 'bluetooth_released', 'issued_boottime_s', 'expires_boottime_s'}, 'lease exact schema/mode')
    need(lease['transaction_id'] == request['transaction_id'] and lease['boot_id'] == request['identity']['boot_id'] and
         lease['token'] == request['lease_token'] and lease['owner'] == 'charging' and
         lease['exclusive'] is lease['camera_released'] is lease['bluetooth_released'] is True, 'explicit coordinated device window')
    issued, expires = lease['issued_boottime_s'], lease['expires_boottime_s']
    need(all(type(x) in [int, float] and math.isfinite(x) for x in [issued, expires]) and
         issued <= now < expires and 0 < expires - issued <= 120, 'live BOOTTIME lease <=120s')

class AtomicFailure(RuntimeError):
    def __init__(self, message, stage):
        super().__init__(message)
        self.stage = stage

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

class MutationUncertain(RuntimeError):
    """A mutating child may still be running. Never initiate another mutation."""

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

_r8_sample=_safe_sample
_r8_healthy=healthy
_r8_unchanged=unchanged

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

def unchanged(before, after):
    _r8_unchanged(before, after)
    need(before['state']['driver'] == after['state']['driver'] == 'samurai-mp2650', 'actual managed charger client')
    need(before['mac_evidence'] == after['mac_evidence'], 'consumed MAC report or bound instance changed')
    need(before['identity'] == after['identity'], 'same current boot/guard/board/rootfs')

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

def preflight(request, device, request_raw=None):
    result = {'schema': 'samurai-irq-native-usb-pm-preflight-v1', 'transaction_id': request.get('transaction_id'),
              'request_sha256': sha(request_raw if request_raw is not None else device.request_raw),
              'identity_match': False, 'eligible': False, 'healthy_state': None, 'snapshot': None,
              'reason': None, 'passed': False, 'read_only': True, 'directory_or_lease_created': False}
    try:
        files, new = unpack(request)
        device.open_readonly(request)
        result['identity'] = device.identity(request)
        old_raw, mode = device.read_owned(MANIFEST)
        need(sha(old_raw) == OLD and mode == 0o600, 'exact old manifest')
        old = json.loads(old_raw); manifest_delta(old, new)
        need(sha(device.read_owned(USB)[0]) == USB_OLD and device.read_owned(USB)[1] == 0o600, 'current USB disk identity')
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
        result.update(passed=True, identity_match=True, healthy_state=mode, eligible=True, reason=None)
    except Exception as error:
        result['reason'] = detail(error)
    finally:
        try: device.close()
        except Exception as error:
            result.update(passed=False, eligible=False, close_error=detail(error))
    return result

class SnapshotBase:
    def read_owned(self, name):
        p = Path(name)
        st = p.lstat()
        need(stat.S_ISREG(st.st_mode) and st.st_uid == 0 and not st.st_mode & 0o022,
             'regular root-owned protected file: ' + name)
        return p.read_bytes(), stat.S_IMODE(st.st_mode)
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
    def manager_command(self, manager, meta, action):
        # Caller already owns the actual service lock. A child rc-service would
        # deadlock on this lock; directly execute freshly loaded installed code.
        need(not self.uncertain, 'unknown child/module: no further manager mutation')
        actual = sha(self.read_owned(SERVICE)[0])
        need(actual == manager['_r8_code_sha256'], 'cannot start/stop with stale in-memory manager')
        self.events.append(['manager-command', actual, action])
        return manager['command'](meta, action)
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

class Device(SnapshotBase):
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
    def __init__(self, request_raw):
        self.request_raw=request_raw;self.request=None;self.out=None;self.lock=None;self.mac_fd=None
        self.mac_baseline=None;self.events=[];self.uncertain=False

    def begin(self, request):
        self.request=request;self.identity(request);self.check_window(request)
        root=Path(ROOT)/request['transaction_id'];info=root.lstat()
        need(stat.S_ISDIR(info.st_mode) and info.st_uid==0 and stat.S_IMODE(info.st_mode)==0o700 and not root.is_symlink(),'owned transaction directory')
        need(Path(__file__).resolve()==root/'stage-worker.py' and sha(Path(__file__).read_bytes())==request['worker_sha256'],'actual worker source/path')
        self.lock_existing(False);self.board_client();self.open_mac();self.verify_carriers()
        out=root/'device-stage';out.mkdir(mode=0o700,exist_ok=False);self.out=out
        self.write_new(self.out/'request-private.json',self.request_raw)
        self.log('process-private.json',dict(transaction_id=request['transaction_id'],boot_id=request['identity']['boot_id'],
                 pid=os.getpid(),start_ticks=int(Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]),
                 argv=[x.decode() for x in Path('/proc/self/cmdline').read_bytes().split(b'\0') if x]))
        self.check_window(request)

    def notes_match(self,manager,old,backups=False):
        for name,entry in old['modules'].items():
            need(self.module_state(name)=='live','original live module retained')
            path=self.out/(Path(entry['target']).name+'.before') if backups and entry['target'] in ORDER else Path(entry['target'])
            manager['loaded_matches'](path,name.replace('-','_'))
            need(sha(Path('/sys/module',name.replace('-','_'),'notes/.note.gnu.build-id').read_bytes())==NOTES[name],'original resident note')

    def manager_command(self,manager,meta,action):
        need(action=='stop','only the original synchronous INHIBIT action exists')
        return super().manager_command(manager,meta,action)

    def event(self,value):
        self.events.append(value)
        if self.out is not None:
            with (self.out/'events-private.jsonl').open('ab') as stream:
                stream.write((json.dumps(value)+'\n').encode());stream.flush();os.fsync(stream.fileno())

    def write_new(self,path,raw):
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'wb') as stream:
            stream.write(raw);stream.flush();os.fchmod(stream.fileno(),0o600);os.fsync(stream.fileno())
        fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)

    def log(self,name,value):
        if self.out is not None:self.write_new(self.out/name,encode(value))

    def backup(self,files,before):
        for name,(raw,mode) in files.items():
            need(mode==0o600,'exact original mode');self.write_new(self.out/(Path(name).name+'.before'),raw)
        self.log('before-private.json',before)
        self.log('files-before-private.json',{name:dict(sha256=sha(raw),mode='0600',bytes=len(raw)) for name,(raw,_) in files.items()})

    def replace(self,name,raw,restore=False):
        need(name in ORDER and sha(raw)==(OLD_FILES if restore else NEW_FILES)[name],'only exact fixed two-file bytes')
        current,mode=self.read_owned(name)
        need(mode==0o600 and sha(current) in (OLD_FILES[name],NEW_FILES[name]),'known protected old/new disk object')
        if restore and current==raw:
            self.event(dict(step='restore-already-original',target=name,sha256=sha(current)));return
        transaction=self.request['transaction_id']+('-restore' if restore else '')
        atomic_replace(name,raw,transaction,sha(current),self.event)

    def finish(self,result):
        if self.out is None:return
        final={}
        for name in ORDER:
            try:
                raw,mode=self.read_owned(name);digest=sha(raw)
                final[name]=dict(sha256=digest,mode=oct(mode),classification='old' if mode==0o600 and digest==OLD_FILES[name] else 'new' if mode==0o600 and digest==NEW_FILES[name] else 'unexpected')
            except BaseException as error:final[name]=dict(error=detail(error),classification='unknown')
        result['final_files']=final
        temporary={}
        for name in ORDER:
            for suffix in ('','-restore'):
                path=Path(name).with_name('.'+Path(name).name+'.'+self.request['transaction_id']+suffix+'.next')
                try:
                    raw,mode=read_owned(path);temporary[str(path)]=dict(state='retained',sha256=sha(raw),bytes=len(raw),mode=oct(mode))
                except FileNotFoundError:temporary[str(path)]=dict(state='absent')
                except BaseException as error:temporary[str(path)]=dict(state='unknown',error=detail(error))
        result['temporary_files']=temporary
        labels={row['classification'] for row in final.values()}
        result['disk_state']='all_new_fsynced' if labels=={'new'} and result['staged'] else 'all_old' if labels=={'old'} else 'partial_known' if labels<={'old','new'} else 'unknown_inspect_before_boot'
        if result['staged'] and result['disk_state']!='all_new_fsynced':result.update(staged=False,phase='failed',status='final_readback_changed')
        if result['staged'] and any(row['state']!='absent' for row in temporary.values()):result.update(staged=False,phase='failed',status='temporary_retained_or_unknown')
        self.log('events-private.json',self.events)

    def publish(self,result):
        if self.out is not None:self.log('result.json',result)

COHORT='89349ffc0adb7e0043505f0250b53eefd78cc917f0b953fb12bb4aeabe25da01'
NEW='34ead4cdb98c2d4b812662cdbe4c0964d5e705574b5d4ab85716b37975a8a39b'
PAYLOAD='f1162d2b5614327f0ce78c918cec62fd681d42cca99d8c03819cfa41086230bc'
OLD_FILES={USB:USB_OLD,MANIFEST:OLD}
NEW_FILES={USB:USB_NEW,MANIFEST:NEW}

def unpack(request):
    need(set(request)=={'schema','transaction_id','cohort_delivery_sha256','payload_sha256','payload_base64','worker_sha256','identity','adoption','lease_token'},'request keys')
    need(request['schema']=='samurai-irq-native-usb-pm-stage-request-v1' and re.fullmatch(r'irq-native-usb-pm-stage-[a-z0-9-]{8,48}',request['transaction_id']),'new stage schema/transaction')
    need(request['cohort_delivery_sha256']==COHORT and request['payload_sha256']==PAYLOAD,'fixed real cohort')
    i,a=request['identity'],request['adoption']
    need(set(i)=={'boot_id','version','serial_sha256','compatible_sha256','rootfs_sha256'} and str(uuid.UUID(i['boot_id']))==i['boot_id'] and i['version']==VERSION,'actual current502 identity')
    need(set(a)=={'transaction_id','guard_path','guard_sha256'} and re.fullmatch(r'usb-irq-protection-activate-[a-z0-9-]{8,48}',a['transaction_id']) and
         a['guard_path']=='/var/lib/samurai/'+a['transaction_id']+'-adopted/boot-id-private.txt','actual original IRQ adopted guard')
    for value in [request['worker_sha256'],a['guard_sha256'],i['serial_sha256'],i['compatible_sha256'],i['rootfs_sha256']]:need(isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value),'actual hash field')
    need(re.fullmatch('[0-9a-f]{48}',request['lease_token']),'unique lease token')
    raw=base64.b64decode(request['payload_base64'],validate=True);need(len(raw)==27163 and sha(raw)==PAYLOAD,'exact actual forward payload')
    files={}
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as tar:
        members=tar.getmembers();need(len(members)==2,'exact two files')
        for m in members:
            target='/'+m.name
            need(target in ORDER and target not in files and m.name==target.lstrip('/') and m.isfile() and m.mode==0o600 and m.uid==m.gid==0 and m.uname==m.gname=='root' and m.mtime==0 and not m.pax_headers,'fixed member metadata')
            content=tar.extractfile(m).read();need(sha(content)==NEW_FILES[target],'exact member bytes');files[target]=content
    return files,json.loads(files[MANIFEST])

def manifest_delta(old,new):
    expected=copy.deepcopy(old)
    need(old['release']==RELEASE and old['modules']['samurai-usb-input']=={'target':USB,'sha256':USB_OLD},'current IRQ USB identity')
    expected['adapter_revision']='usb-irq-native-pm-budget504-01'
    expected['modules']['samurai-usb-input']['sha256']=USB_NEW;expected['installed_files'][USB]=USB_NEW
    need(new==expected and old['installed_files'][SERVICE]==SERVICE_SHA and old['modules']['samurai-mp2650']['sha256']=='97c16c3dc0b458fa4d2c686912ffdf805b899abfb846201767843a0348cbffdd' and
         old['modules']['samurai-gauge-protection']['sha256']=='7848cfab264dde1f7f02b24b8022b951d4f3a604eba120b313bac23d0f4a3044','only fixed USB hash and cohort revision change')
    need(old['default_input_cap_ua']==900000 and old['default_charge_cap_ua']==250000 and old['source_budget_enforced'] is True,'retained limits policy')

def stopped_snapshot(before,after,now):
    safe_sample(after);source_limits(after);unchanged(before,after)
    need(before['notes']==after['notes']==NOTES and before['source']==after['source'] and before['limits']==after['limits'],'all old live notes/source/limits retained')
    br,ar=before['registers'],after['registers']
    need(set(br)==set(ar) and '14' not in br,'non-destructive register set')
    for key in br:
        if key=='08':need(ar[key]==((br[key]&~0x18)|8),'only INHIBIT control change')
        elif key!='13':need(ar[key]==br[key],'all other configuration retained')
    need(ar['13']&2 and after['sample']['desired_enable']==0,'stopped actual converter/source')
    s=after['sample']
    need(s.get('hold_requested')==s.get('full_holding')==0,'INHIBIT is not Full holding')
    if before['sample'].get('logical_full'):
        need(s.get('logical_full')==1 and s.get('full_cause')==before['sample']['full_cause'] and s.get('session_seconds')==0,'prior logical Full/cause retained while holding clears')
    elif s.get('logical_full'):
        need(s.get('full_cause') in (1,2,3) and s.get('session_seconds')==0,'newly observed genuine Full retained')
    else:need(s.get('full_cause')==0,'nonFull cause remains zero')

def rollback_gate(device,request,before,manager,old):
    # Only file restoration; never new AUTO/load/stop after the original stop.
    need(not device.uncertain,'unknown original process/module state')
    need(device.identity(request)==before['identity'],'same current boot/guard/board')
    device.notes_match(manager,old,backups=True)
    need(device.mac_evidence()==before['mac_evidence'],'same consumed MAC instance/cache')
    need(device.registers()['08']&0x18==8,'known physical INHIBIT before restoring disk')

def stage(request,device,execute=False):
    need(execute,'explicit --execute-stage only')
    result=dict(schema='samurai-irq-native-usb-pm-stage-result-v1',transaction_id=request.get('transaction_id'),request_sha256=sha(device.request_raw),
                cohort_delivery_sha256=COHORT,old_manifest_sha256=OLD,new_manifest_sha256=NEW,payload_sha256=PAYLOAD,
                staged=False,status='not_staged',phase='rejected',runtime_pending=True,terminal=True,stop_verified=False,
                primary_error=None,recovery_error=None,activation_attempted=False,new_module_loaded=False,capture_issued=False)
    phase='request';before=paused=backups=manager=old=None;write_attempted=False
    try:
        files,new=unpack(request);phase='begin';device.begin(request)
        phase='preflight';backups={name:device.read_owned(name) for name in ORDER}
        for name,(raw,mode) in backups.items():need(mode==0o600 and sha(raw)==OLD_FILES[name],'exact current18e8/7cb disk')
        old=json.loads(backups[MANIFEST][0]);manifest_delta(old,new)
        manager=device.manager(SERVICE_SHA);need(device.verify(manager)==old,'fresh original manager verify')
        device.notes_match(manager,old);before=device.observe(manager)
        result['before_healthy_mode']=healthy(before,True);unchanged(before,before);need(before['notes']==NOTES,'current97c/7848/7cb notes')
        device.backup(backups,before);device.check_window(request)
        phase='synchronous-stop';stopped(device,manager,old,result);result['stop_verified']=True
        phase='stopped-proof';paused=device.observe(manager);stopped_snapshot(before,paused,time.clock_gettime(time.CLOCK_BOOTTIME))
        device.log('stopped-private.json',paused)
        for name in ORDER:
            phase='replace-usb' if name==USB else 'replace-manifest'
            device.check_window(request);rollback_gate(device,request,before,manager,old)
            write_attempted=True;device.replace(name,files[name])
        phase='staged-proof';device.check_window(request);need(device.verify(manager)==new,'new disk manager verify only')
        device.notes_match(manager,old,backups=True);after=device.observe(manager)
        stopped_snapshot(paused,after,time.clock_gettime(time.CLOCK_BOOTTIME));device.log('after-private.json',after)
        device.check_window(request)
        result.update(staged=True,phase='staged',status='staged/runtime_pending',resident_notes=after['notes'],configuration='INHIBIT retained',
                      logical_full_retained=after['sample']['logical_full'],full_cause_retained=after['sample']['full_cause'])
    except BaseException as error:
        result.update(primary_error=dict(phase=phase,error=detail(error)),phase='failed',status='failed_inhibited_no_replay')
        if isinstance(error,AtomicFailure):result['primary_error']['atomic_stage']=error.stage
        if write_attempted and result['stop_verified']:
            try:
                rollback_gate(device,request,before,manager,old)
                for name in ORDER:
                    device.replace(name,backups[name][0],restore=True)
                need(device.verify(manager)==old,'exact old disk restored')
                rollback_gate(device,request,before,manager,old)
                result['restored_original_disk']=True;result['status']='failed_old_disk_restored_inhibited'
            except BaseException as recovery_error:result['recovery_error']=detail(recovery_error)
        if device.uncertain:result.update(terminal=False,status='unknown_original_worker_or_module_no_replay')
    finally:
        try:device.finish(result)
        except BaseException as error:result.update(staged=False,phase='failed',status='receipt_failure_inspect_same_worker',receipt_error=detail(error))
        try:device.close()
        except BaseException as error:result.update(staged=False,phase='failed',status='close_failure_inspect_same_worker',close_error=detail(error))
        try:device.publish(result)
        except BaseException as error:result.update(staged=False,phase='failed',status='receipt_failure_inspect_same_worker',receipt_error=detail(error))
    return result

def main():
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group()
    group.add_argument('--execute-stage',action='store_true');group.add_argument('--preflight',action='store_true');args=parser.parse_args()
    if not (args.execute_stage or args.preflight):
        print(json.dumps(dict(source_only=True,device_accessed=False,runtime_request_created=False)));return 0
    need(not sys.flags.optimize,'nonoptimized Python');os.umask(0o077)
    raw=sys.stdin.buffer.read(120001);need(0<len(raw)<=120000,'bounded explicit request')
    request=json.loads(raw);device=Device(raw)
    try:
        result=preflight(request,device,raw) if args.preflight else stage(request,device,True)
        print(json.dumps(result),flush=True)
    except BaseException:
        if not device.uncertain:raise
        while True:time.sleep(1)
    while device.uncertain:time.sleep(1)
    return 0 if (result.get('passed') if args.preflight else result['staged']) else 1

if __name__=='__main__':raise SystemExit(main())
