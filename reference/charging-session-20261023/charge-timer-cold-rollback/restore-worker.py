"""Default inert. Current charger two-file cold rollback; no module/carrier activation."""
from pathlib import Path,PurePosixPath
from types import SimpleNamespace
import argparse,base64,copy,hashlib,io,json,math,os,re,runpy,stat,struct,sys,tarfile,time,uuid
sys.dont_write_bytecode=True
OLD_FILES={'/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-mp2650.ko': '97c16c3dc0b458fa4d2c686912ffdf805b899abfb846201767843a0348cbffdd', '/usr/share/samurai-charging/manifest.json': '5ef4eaef76896f1fda932d95d6c3e4e1117bcc451075ad7265dbe22204880c70'}
NEW_FILES={'/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-mp2650.ko': 'bef4dba73e1244fec4c89f2d5b47ac6b1483384c1f64aa1d589de792d2e97d6f', '/usr/share/samurai-charging/manifest.json': 'f15ecc205d42e42f54b53f0052c8ebb4b011bc395756848a59373ce283d46bb5'}
OLD_NOTES={'samurai-usb-input': '028ea63c24b0b46ec6edb03b9c3cbfc999c4b7a119034dc18ac70d1bcbf064e6', 'samurai-gauge-protection': 'bf148be50cb3a4c30bf3ab194f90163fbd47ce5dcbcaf1adb7d84392d242ecdd', 'samurai-mp2650': 'fe15a2fcb618dee0b161952cd66c32f2d5ecc9c8d50b0975242da5353c472016'}
NEW_NOTES={'samurai-usb-input': '028ea63c24b0b46ec6edb03b9c3cbfc999c4b7a119034dc18ac70d1bcbf064e6', 'samurai-gauge-protection': 'bf148be50cb3a4c30bf3ab194f90163fbd47ce5dcbcaf1adb7d84392d242ecdd', 'samurai-mp2650': '1df00d554b85aa45d4bbbc0d1a6a7a4cbd56ba4da45ae48d54bb8ae1f3434d08'}
NEW_MANIFEST={'release': '7.3.0-rc6-rmx1931-samurai-k363+', 'modules': {'samurai-mp2650': {'target': '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-mp2650.ko', 'sha256': 'bef4dba73e1244fec4c89f2d5b47ac6b1483384c1f64aa1d589de792d2e97d6f'}, 'samurai-usb-input': {'target': '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-usb-input.ko', 'sha256': '13f41e7cdbd1825982e2155bfb97e0105227179d1afa8da8a2795ba39f4299a4'}, 'samurai-gauge-protection': {'target': '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-gauge-protection.ko', 'sha256': 'f6bef8a239d5101dbb710f1dd5da9642bdc7ac5e4e568e2e1193de6233a31d7e'}}, 'default_input_cap_ua': 900000, 'default_charge_cap_ua': 250000, 'source_budget_enforced': True, 'installed_files': {'/usr/sbin/samurai-charging': '83469a88beab16cd190793ddf65e672438d0a97aaa812b63a47b4bbb4f22472f', '/etc/init.d/samurai-charging': 'bfed48ebbcaced5f017110564045eef500a88f12fefe7ebff6d1e74cabfe570a', '/usr/lib/samurai-charging/control-trial.py': 'c33cb2eec24031e72a5f1dda9b94c05607615e0b12a14ba3cecd6db56c820761', '/usr/lib/samurai-charging/live-session.py': '2199d7d413b2f4a5aeaa8270c20e967f5da711397c29e959e59463c1a5715f2b', '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-mp2650.ko': 'bef4dba73e1244fec4c89f2d5b47ac6b1483384c1f64aa1d589de792d2e97d6f', '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-usb-input.ko': '13f41e7cdbd1825982e2155bfb97e0105227179d1afa8da8a2795ba39f4299a4', '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-gauge-protection.ko': 'f6bef8a239d5101dbb710f1dd5da9642bdc7ac5e4e568e2e1193de6233a31d7e'}, 'adapter_revision': 'confirmed-stop-timer-02'}
RELEASE='7.3.0-rc6-rmx1931-samurai-k363+'
VERSION504='#504 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026'
BOOT='eddadec33fcd1d114c45af76cb9fc6d6b5f1de2c81c0e9fada099c5b884f6e06'
LOGDUMP504='4453d46202f4446810c8f72524a034a28acf3695f59eb12dbde8cf530e356d83'
ROOT='/root/charging-management-20261023'
SERVICE='/usr/sbin/samurai-charging'
MANAGER='83469a88beab16cd190793ddf65e672438d0a97aaa812b63a47b4bbb4f22472f'
LIVE_SHA='2199d7d413b2f4a5aeaa8270c20e967f5da711397c29e959e59463c1a5715f2b'
STARTUP_SHA='2a364e12d72229ef7b0ddfd7620d5ff434b97eaf93eb60899fd24a03b5b9a54a'
LOCK='/run/lock/samurai-charging.lock'
INSTANCE='/sys/devices/platform/samurai-gauge-protection'
MANIFEST='/usr/share/samurai-charging/manifest.json'
TARGET='/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-mp2650.ko'
ORDER=['/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-mp2650.ko', '/usr/share/samurai-charging/manifest.json']
ROLLBACK_PAYLOAD='c72589194965a9a49af66b6c0032e196dd1407cd2defed2c193c432be718f38c'
SOURCE_IDENTITY={'boot_id': '4e325db2-7579-461d-9e90-cf41662e4cf1', 'version': '#504 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026', 'serial_sha256': '950a1ee84085705e269305b43ebf643259e319a9e40f2edc9f17fbbd3d4785b9', 'compatible_sha256': 'df8c5be46e887b2f7cb9d61c9e001b26d8422173c0e8f7fdeb571c30e58c7970', 'rootfs_sha256': '282c597b3a71c08a3fa11147f4c0e1e4c3465faf862fdc32fdb9dd64503c466f'}
SOURCE_TX='irq-native-usb-pm-stage-timer-20261024-01'
SOURCE_REQUEST_SHA='7d9c3ff80cd363dc6892ac2593a2750325fce1da737b4e4aee5177bfbd3dd369'
SOURCE_COHORT='dea1c696f5ebaddde358a5745fbd07a8d1a9b4281b0b398a84ac48ded67b4c80'
FORWARD_PAYLOAD='9d26ed7969f9f022ad70877a60efb9dda46502c72de5a6b7a32651a9ccc3fc1f'
STAGE_WORKER='e016cc53bb1dede791b0f680488a112a8dbf9fc7850a50a22bc514613abc8a93'
STAGE_SUPERVISOR='5e427769fc4eb592d63454522f37d0cceceb02b9a8514fa39e26318ebf40e4f3'
STAGE_WRAPPER='e2dd738f9bd5e7aad888a40c06e516a39699ad63e26ef54b35bf7dce91300526'

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

def active(text):
    if not isinstance(text, str): return None
    values = re.findall(r'\[([^]]+)\]', text)
    return values[0] if len(values) == 1 else text.strip() if not values and len(text.split()) == 1 else None

def safe_electrical(data, now):
    s, r, lim, p = data['sample'], data['state']['registers'], data['limits'], data['protection']
    need(type(data['read_start']) in (int, float) and type(data['read_end']) in (int, float)
         and 0 <= data['read_end'] - data['read_start'] <= 3 and 0 <= now - data['read_end'] <= 1, 'fresh bounded observation')
    need(s.get('valid') == s.get('protection_ok') == 1 and s.get('shadow') == 0
         and type(s.get('age_ms')) is int and 0 <= s['age_ms'] <= 3000, 'fresh complete cell/temperature sample required')
    need(all(type(s.get(key)) is int and 2000000 <= s[key] <= 4600000 for key in ('cell1_uv', 'cell2_uv'))
         and type(s.get('pack_uv')) is int and 4000000 <= s['pack_uv'] <= 9200000
         and abs(s['cell1_uv'] + s['cell2_uv'] - s['pack_uv']) <= 200000, 'safe complete pack/cells')
    need(type(s.get('temp_decic')) is int and 160 <= s['temp_decic'] < 440, 'normal safe temperature')
    need(data['protection_health'] == 'Good' and p.get('id') == 0x2719
         and p.get('error') == p.get('safety') == p.get('pf') == 0, 'fresh independent normal protection')
    need(p.get('operation', 0) & 0x300 == 0x300 and not p['operation'] & ((1 << 20) | (1 << 16) | 0x7c00)
         and p.get('manufacturing', 0) & 0x18 == 0x18 and not p['manufacturing'] & 0x8006, 'sealed autonomous protection')
    need(set(r) == {'00', '01', '02', '03', '04', '05', '07', '08', '09', '0f', '13'}
         and all(type(v) is int and 0 <= v <= 255 for v in r.values()), 'complete nondestructive register set')
    need(type(lim['input_ua']) is type(lim['charge_ua']) is type(lim['cv_pack_uv']) is int
         and 0 <= lim['input_ua'] <= 900000 and 0 <= lim['charge_ua'] <= 250000,
         'actual configured limits within original hard caps')
    need((r['00'] & 0x7f) * 50000 == (r['0f'] & 0x7f) * 50000 == lim['input_ua']
         and (r['02'] & 0x7f) * 50000 == lim['charge_ua'], 'actual register/limit agreement')
    need(7425000 <= lim['cv_pack_uv'] <= 8725000
         and lim['cv_pack_uv'] == 2 * (3712500 + ((r['04'] & 0x7e) >> 1) * 12500), 'bounded inherited CV')
    need(data['state']['driver'] == 'samurai-mp2650' and data['state']['taint'] == '0', 'actual managed untainted charger')
    for name in ('error', 'stop_error', 'latched', 'fault', 'cycle_timeout', 'thermal_inhibit', 'gauge_charge_stop'):
        need(type(s.get(name)) is int, 'known fault history: ' + name)
    need(s['latched'] in (0, 1) and s['cycle_timeout'] in (0, 1), 'known existing latch/timeout')

def safe_stopped(data, now):
    safe_electrical(data, now)
    need(active(data['charge_behaviour']) == 'inhibit-charge'
         and data['state']['registers']['08'] & 0x18 == 8, 'physical INHIBIT required')

def idle(data):
    state = data['state']; need(len(state['camera_pm']) == 4 and all(x == 'suspended' for x in state['camera_pm'].values()), 'camera PM idle')
    value = json.loads(state['m2m'])
    need(not any(value.get(k) for k in ('users', 'running', 'fatal', 'pinned', 'orphans', 'first_error')), 'camera m2m idle')

def legacy_retained(before, after):
    need(before['notes'] == after['notes'] and before['state']['boot_id'] == after['state']['boot_id'], 'resident/boot unchanged')
    need(before['limits'] == after['limits'], 'configuration limits retained')
    for name, value in before['state']['registers'].items():
        if name == '08': need(after['state']['registers'][name] == (value & ~0x18) | 8, 'only INHIBIT configuration change')
        elif name != '13': need(after['state']['registers'][name] == value, 'other configuration unchanged: ' + name)
    for field in ('latched', 'cycle_timeout'):
        need(not before['sample'][field] or after['sample'][field] == 1, 'prior fault/timeout retained: ' + field)

def restore(request, device, execute=False):
    need(execute, 'explicit --execute-rollback required')
    result = dict(schema='samurai-charger-timer-cold-rollback-result-v1', transaction_id=request.get('transaction_id'),
        profile=request.get('profile'), terminal=True, restored=False, status='not_staged_original', runtime_pending=True,
        phase='request', stop_verified=False, stop_action=None, primary_error=None, disk_state='not_inspected',
        automatic_replay_or_rollback=False, module_or_carrier_action=False, physical_acceptance=False)
    phase = 'request'
    try:
        files = unpack(request)
        phase = 'begin'; device.begin(request)
        phase = 'source-stage'; result['source_proof'] = device.source_proof(request)
        phase = 'identity'; result['current_profile'] = validate_profile(request, device.current(request))
        phase = 'disk'; backups = {target: device.read_owned(target) for target in ORDER}
        for target, (raw, mode) in backups.items(): need(mode == 0o600 and sha(raw) == NEW_FILES[target], 'exact current new disk: ' + target)
        manager = device.manager(); device.verify_retained(manager)
        phase = 'pre-stop'; before = device.observe(manager)
        safe_electrical(before, device.now()); idle(before)
        need(before['notes'] == expected_profile(request)['notes'], 'actual profile notes before stop')
        device.backup(backups, before)
        phase = 'stop'
        device.check_window(request)
        if active(before['charge_behaviour']) == 'inhibit-charge' and before['state']['registers']['08'] & 0x18 == 8:
            result['stop_action'] = 'already_inhibited'
        else:
            result['stop_action'] = 'manager_stop_once'; device.stop(manager, json.loads(backups[MANIFEST][0]))
        stopped = device.observe(manager); safe_stopped(stopped, device.now()); retained(before, stopped); idle(stopped)
        result['stop_verified'] = True; device.log('stopped-private.json', stopped)
        for target in ORDER:
            phase = 'restore:' + Path(target).name
            device.check_window(request)
            validate_profile(request, device.current(request, carriers=False))
            current = device.observe(manager); safe_stopped(current, device.now()); retained(before, current); idle(current)
            device.replace(target, files[target])
        phase = 'final'
        device.check_window(request); validate_profile(request, device.current(request))
        device.verify_restored(files, manager)
        after = device.observe(manager); safe_stopped(after, device.now()); retained(before, after); idle(after)
        device.log('after-private.json', after)
        result.update(restored=True, phase='staged_original', status='staged_original/runtime_pending',
            disk_state='all_original_fsynced', actual_resident_notes=after['notes'],
            source_budget_observation=after.get('source'), existing_fault_history={key:after['sample'][key]
                for key in ('error','stop_error','latched','fault','cycle_timeout','thermal_inhibit','gauge_charge_stop')},
            old_modules_resident_verified=False, original_full_runtime_accepted=False)
    except BaseException as error:
        result.update(phase='failed',status='failed_preserved_no_replay',primary_error={'phase':phase,'error':detail(error)})
        if isinstance(error, AtomicFailure): result['primary_error']['atomic_stage'] = error.stage
    finally:
        for name, action in [('receipt_error',lambda:device.finish(result)),('close_error',device.close)]:
            try: action()
            except BaseException as error: result.update(restored=False,phase='failed',status='inspect_same_original_worker',**{name:detail(error)})
        try: device.publish(result)
        except BaseException as error: result.update(restored=False,phase='failed',status='inspect_same_original_worker',receipt_error=detail(error))
    return result

class BaseDevice:
    def __init__(self):
        self.out = self.lock = self.journal = None; self.events = []; self.request = None; self.carriers = None

    def now(self): return time.clock_gettime(time.CLOCK_BOOTTIME)

    def read_owned(self, path): return read_owned(path)

    def write_new(self, path, raw):
        with Path(path).open('xb') as file: file.write(raw); file.flush(); os.fsync(file.fileno())

    def log(self, name, value):
        self.write_new(self.out / name, encode(value))

    def event(self, value):
        value = dict(value, boottime_s=self.now()); self.events.append(value)
        self.journal.write(encode(value).replace(b'\n', b' ') + b'\n'); self.journal.flush(); os.fsync(self.journal.fileno())

    def check_window(self, request):
        need(self.identity() == request['identity'], 'current source identity unchanged')
        raw, mode = read_owned('/run/' + request['transaction_id'] + '-window-private.json')
        validate_lease(json.loads(raw), mode, request, self.now())

    def begin(self, request):
        import fcntl
        need(os.geteuid() == 0 and not sys.flags.optimize, 'root/nonoptimized')
        self.request = request; root = Path(ROOT) / request['transaction_id']
        info = root.lstat(); need(stat.S_ISDIR(info.st_mode) and not root.is_symlink() and info.st_uid == 0 and stat.S_IMODE(info.st_mode) == 0o700, 'unique protected transaction directory')
        need(Path(__file__).resolve() == root / 'restore-worker.py' and sha(read_owned(__file__)[0]) == request['worker_sha256'], 'actual worker path/source')
        self.out = root / 'device-rollback'; self.out.mkdir(mode=0o700, exist_ok=False)
        self.journal = (self.out / 'journal-private.jsonl').open('xb')
        fields = Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()
        self.log('process-private.json',dict(pid=os.getpid(),start_ticks=int(fields[19]),
            argv=[x.decode() for x in Path('/proc/self/cmdline').read_bytes().split(b'\0') if x],
            boot_id=request['identity']['boot_id'],transaction_id=request['transaction_id'],worker_sha256=request['worker_sha256']))
        self.log('request-private.json',{k:v for k,v in request.items() if k != 'payload_base64'})
        self.check_window(request)
        self.lock = os.open(LOCK, os.O_RDWR | os.O_NOFOLLOW)
        info = os.fstat(self.lock); need(stat.S_ISREG(info.st_mode) and info.st_uid == 0 and stat.S_IMODE(info.st_mode) == 0o600, 'original service lock')
        fcntl.flock(self.lock,fcntl.LOCK_EX | fcntl.LOCK_NB); self.check_window(request)
        client = Path('/sys/bus/i2c/devices/0-005c')
        need((client/'name').read_text().strip() == 'mp2650' and (client/'driver').resolve().name == 'samurai-mp2650'
             and (client/'of_node').resolve().as_posix().endswith('/soc@0/geniqup@8c0000/i2c@884000/charger@5c'), 'existing exact charger owner')

    def block_fact(self, name, length):
        import fcntl
        fd=os.open('/dev/disk/by-partlabel/'+name,os.O_RDONLY|os.O_CLOEXEC)
        try:
            need(stat.S_ISBLK(os.fstat(fd).st_mode) and struct.unpack('=Q',fcntl.ioctl(fd,0x80081272,bytes(8)))[0]==length,'complete read-only carrier')
            digest=hashlib.sha256(); remaining=length
            while remaining:
                raw=os.read(fd,min(1048576,remaining));need(raw,'short carrier');digest.update(raw);remaining-=len(raw)
            return dict(bytes=length,sha256=digest.hexdigest())
        finally: os.close(fd)

    def current(self, request, carriers=True):
        if carriers: self.carriers={name:self.block_fact(name,length) for name,length in [('boot',100663296),('logdump',67108864)]}
        need(self.carriers is not None,'initial complete carrier read required')
        notes={name:sha(Path('/sys/module',name.replace('-','_'),'notes/.note.gnu.build-id').read_bytes()) for name in OLD_NOTES}
        return dict(identity=self.identity(),release=os.uname().release,machine=os.uname().machine,
            taint=Path('/proc/sys/kernel/tainted').read_text().strip(),notes=notes,
            module_states={name:Path('/sys/module',name.replace('-','_'),'initstate').read_text().strip() for name in notes},**self.carriers)

    def manager(self):
        for path,digest in [(SERVICE,MANAGER),('/usr/lib/samurai-charging/live-session.py',LIVE_SHA),('/usr/local/sbin/samurai-usb',STARTUP_SHA)]: need(sha(read_owned(path)[0])==digest,'retained fixed code: '+path)
        value=runpy.run_path(SERVICE); need(sha(read_owned(SERVICE)[0])==MANAGER and value['live'].REGS==[0,1,2,3,4,5,7,8,9,15,19],'stable manager/no REG14')
        return value

    def verify_retained(self, manager):
        manifest=manager['verify'](); need(manifest==NEW_MANIFEST,'exact current new manifest/retained files')

    def observe(self, manager):
        start=self.now(); live=manager['live']; state=live.state()
        def observed(path):
            try:return Path(path).read_text().strip()
            except OSError as error:return {'errno':error.errno}
        supply=live.PSY/'mp2650-input'; source=live.PSY/'samurai-usb-input'
        protection=Path('/sys/devices/platform/samurai-gauge-protection/protection_state').read_text()
        result=dict(read_start=start,state=state,sample=manager['sample'](),
            notes={name:sha(Path('/sys/module',name.replace('-','_'),'notes/.note.gnu.build-id').read_bytes()) for name in OLD_NOTES},
            protection={k:int(v,0) for k,v in (x.split('=') for x in protection.split())},
            protection_health=(live.PSY/'samurai-gauge-protection/health').read_text().strip(),
            charge_behaviour=(supply/'charge_behaviour').read_text().strip(),
            source={key:observed(source/key) for key in ('online','usb_type','current_max','input_current_limit')},
            limits={key:int((supply/file).read_text()) for key,file in [('input_ua','input_current_limit'),('charge_ua','constant_charge_current'),('cv_pack_uv','constant_charge_voltage')]})
        result['read_end']=self.now();return result

    def stop(self, manager, meta):
        need(sha(read_owned(SERVICE)[0])==MANAGER,'exact normal manager stop')
        result=manager['command'](meta,'stop');need(result=={'managed':True,'requested':'inhibit-charge'},'synchronous stop result')

    def backup(self, files, before):
        for path,(raw,mode) in files.items(): self.write_new(self.out/(Path(path).name+'.before'),raw)
        self.log('before-private.json',before)
        self.log('files-before-private.json',{path:dict(sha256=sha(raw),mode=oct(mode),bytes=len(raw)) for path,(raw,mode) in files.items()})

    def replace(self, path, raw):
        need(path in ORDER and sha(raw)==OLD_FILES[path],'only original fixed file')
        return atomic_replace(path,raw,self.request['transaction_id'],NEW_FILES[path],self.event)

    def verify_restored(self, files, manager):
        for path,raw in files.items(): need(read_owned(path)==(raw,0o600),'old readback')
        need(manager['verify']()==json.loads(files[MANIFEST]),'old manifest/retained files reread; no loaded_matches')

    def finish(self, result):
        if self.out is None:return
        final={}; temporaries={}; labels=[]
        for target in ORDER:
            try:
                raw,mode=read_owned(target);digest=sha(raw)
                label='original' if digest==OLD_FILES[target] else 'new' if digest==NEW_FILES[target] else 'unexpected'
                final[target]=dict(sha256=digest,mode=oct(mode),classification=label)
            except BaseException as error:label='unknown';final[target]=dict(classification=label,error=detail(error))
            labels.append(label)
            temporary=Path(target).with_name('.'+Path(target).name+'.'+self.request['transaction_id']+'.next')
            try:raw,mode=read_owned(temporary);temporaries[target]=dict(path=str(temporary),state='retained',sha256=sha(raw),mode=oct(mode))
            except FileNotFoundError:temporaries[target]=dict(path=str(temporary),state='absent')
            except BaseException as error:temporaries[target]=dict(path=str(temporary),state='unknown',error=detail(error))
        result['final_files']=final;result['temporary_files']=temporaries
        result['unknown_write_state']=any(x in ('unknown','unexpected') for x in labels)
        if all(x=='original' for x in labels): result['disk_state']='all_original_fsynced' if result['restored'] else 'all_original_known_durability_or_acceptance_unproved'
        elif all(x=='new' for x in labels):result['disk_state']='all_new'
        elif set(labels)<={'original','new'}:result['disk_state']='partial_known'
        else:result['disk_state']='unknown_inspect_same_worker'
        if result['restored'] and (result['disk_state']!='all_original_fsynced' or any(x['state']!='absent' for x in temporaries.values())):
            result.update(restored=False,phase='failed',status='final_readback_changed_inspect_same_worker')
        self.log('events-private.json',self.events)

    def close(self):
        errors=[]
        for name in ('journal','lock'):
            value=getattr(self,name)
            if value is not None:
                try:value.close() if name=='journal' else os.close(value)
                except BaseException as error:errors.append(detail(error))
                setattr(self,name,None)
        need(not errors,'cleanup: '+repr(errors))

    def publish(self, result):
        if self.out is not None:self.log('result.json',result)

class Device(BaseDevice):
 def __init__(self):
  super().__init__();self.mac_fd=None

 def identity(self):
  need(self.request is not None,'explicit current request')
  need(os.uname().version==expected_profile(self.request)['version'] and os.uname().release==RELEASE and
   os.uname().machine=='aarch64','exact current profile kernel')
  compatible=Path('/sys/firmware/devicetree/base/compatible').read_bytes()
  need(b'realme,samurai' in compatible.split(b'\0'),'actual board')
  return dict(boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),version=os.uname().version,
   serial_sha256=sha(Path('/sys/devices/soc0/serial_number').read_bytes()),compatible_sha256=sha(compatible),
   rootfs_sha256=sha(read_owned('/etc/samurai-rootfs-release')[0]))

 def begin(self,request):
  super().begin(request)
  p=Path(INSTANCE);need((p/'driver').resolve().as_posix()=='/sys/bus/platform/drivers/samurai-gauge-protection','current protection driver')
  self.mac_fd=os.open(p/'mac_evidence',os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)
  need(self.cache_evidence()==request['current_cache'],'fresh current cache matches original-key capture')

 def cache_evidence(self):
  need(self.mac_fd is not None,'held current cache fd')
  p=Path(INSTANCE);held,current=os.fstat(self.mac_fd),(p/'mac_evidence').stat()
  need((held.st_dev,held.st_ino)==(current.st_dev,current.st_ino) and
   (p/'driver').resolve().as_posix()=='/sys/bus/platform/drivers/samurai-gauge-protection','same bound current cache fd')
  os.lseek(self.mac_fd,0,os.SEEK_SET);raw=os.read(self.mac_fd,16384)
  value=dict(sha256=sha(raw),raw_base64=base64.b64encode(raw).decode(),attribute_dev=held.st_dev,
   attribute_inode=held.st_ino,instance_inode=p.stat().st_ino)
  validate_cache(value);need(value==self.request['current_cache'],'current cache/instance continuously retained')
  return value

 def current(self,request,carriers=True):
  value=super().current(request,carriers);value['current_cache']=self.cache_evidence();return value

 def observe(self,manager):
  value=super().observe(manager);value['current_cache']=self.cache_evidence();return value

 def close(self):
  errors=[]
  if self.mac_fd is not None:
   try:os.close(self.mac_fd)
   except BaseException as error:errors.append(detail(error))
   finally:self.mac_fd=None
  try:super().close()
  except BaseException as error:errors.append(detail(error))
  need(not errors,'all owned cache/journal/lock close errors: '+repr(errors))

PROFILES=('staged_same_boot_old_charger','booted_504_new_charger')

def expected_profile(request):
    return dict(version=VERSION504,boot=BOOT,logdump=LOGDUMP504,
                notes=OLD_NOTES if request['profile']==PROFILES[0] else NEW_NOTES)

def validate_cache(value):
    need(isinstance(value,dict) and set(value)=={'sha256','raw_base64','attribute_dev','attribute_inode','instance_inode'},'complete current cache evidence')
    raw=base64.b64decode(value['raw_base64'],validate=True)
    need(0<len(raw)<16384 and raw.endswith(b'\n') and sha(raw)==value['sha256'],'complete same opaque cache bytes')
    header=dict(item.split('=',1) for item in raw.decode().splitlines()[0].split())
    need(header.get('schema')=='2' and header.get('diagnostic_profile')=='1' and
         (header.get('attempted'),header.get('terminal')) in [('0','0'),('1','1')],'f6 profile1 untouched or completed cache, never in progress')
    need(type(value['attribute_dev']) is int and value['attribute_dev']>=0 and
         all(type(value[k]) is int and value[k]>0 for k in ['attribute_inode','instance_inode']),'actual current kernfs identities')
    return raw

def unpack(request):
    need(set(request)=={'schema','transaction_id','profile','identity','source_identity','source_stage','current_cache',
         'payload_sha256','payload_base64','worker_sha256','lease_token'},'timer rollback request keys')
    need(request['schema']=='samurai-charger-timer-cold-rollback-request-v1' and
         re.fullmatch(r'charger-timer-cold-rollback-[a-z0-9-]{8,48}',request['transaction_id']),'explicit new timer rollback owner')
    need(request['profile'] in PROFILES and request['source_identity']==SOURCE_IDENTITY,'exact source identity and current profile')
    current=request['identity']
    need(set(current)==set(SOURCE_IDENTITY) and str(uuid.UUID(current['boot_id']))==current['boot_id'] and
         current['version']==VERSION504,'fresh current504 identity')
    need(all(current[k]==SOURCE_IDENTITY[k] for k in ['serial_sha256','compatible_sha256','rootfs_sha256']),'same actual board/rootfs')
    need(re.fullmatch('[0-9a-f]{48}',request['lease_token']) and re.fullmatch('[0-9a-f]{64}',request['worker_sha256']),'actual worker and unique lease')
    validate_cache(request['current_cache'])
    raw=base64.b64decode(request['payload_base64'],validate=True)
    need(request['payload_sha256']==ROLLBACK_PAYLOAD and len(raw)==51591 and sha(raw)==ROLLBACK_PAYLOAD,'exact c725 two-file inverse')
    files={}
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
        members=archive.getmembers();need(len(members)==2,'only charger and manifest')
        for member in members:
            target='/'+member.name
            need(target in OLD_FILES and target not in files and member.name==target.lstrip('/') and member.isfile() and
                 member.mode==0o600 and member.uid==member.gid==member.mtime==0 and member.uname==member.gname=='root' and
                 not member.pax_headers,'exact inverse member metadata')
            data=archive.extractfile(member).read();need(sha(data)==OLD_FILES[target],'original bytes');files[target]=data
    return files

def validate_profile(request,actual):
    profile=expected_profile(request);current=request['identity']
    need(actual['identity']==current and current['version']==VERSION504 and actual['release']==RELEASE and
         actual['machine']=='aarch64' and actual['taint']=='0','actual complete504 profile')
    need(actual['boot']==dict(bytes=100663296,sha256=BOOT) and actual['logdump']==dict(bytes=67108864,sha256=LOGDUMP504),'unchanged complete carriers')
    need(actual['notes']==profile['notes'] and set(actual['module_states'])==set(profile['notes']) and
         all(value=='live' for value in actual['module_states'].values()),'exact live charger/USB/protection tuple')
    need(actual['current_cache']==request['current_cache'],'same held current cache')
    if request['profile']==PROFILES[0]:need(current==SOURCE_IDENTITY,'original source boot for old resident')
    else:need(current['boot_id']!=SOURCE_IDENTITY['boot_id'],'new boot required for new charger resident')
    return dict(profile=request['profile'],resident_notes=profile['notes'],boot_sha256=BOOT,logdump_sha256=LOGDUMP504,current_version=VERSION504)

def source_paths(transaction):
    need(transaction==SOURCE_TX,'only the prepared current timer stage')
    root=ROOT+'/'+transaction
    names={'request':'request-private.json','stage_source':'stage-worker.py','wrapper':'worker.py','supervisor':'supervisor.py',
           'launch':'launch-private.json','supervisor_launch':'supervisor-launch-private.json','supervisor_process':'supervisor-process-private.json',
           'worker_process':'worker-process-private.json','worker_terminal':'worker-terminal-private.json',
           'stage_process':'device-stage/process-private.json','result':'device-stage/result.json','before':'device-stage/before-private.json',
           'stopped':'device-stage/stopped-private.json','after':'device-stage/after-private.json','files_before':'device-stage/files-before-private.json',
           'old_charger':'device-stage/samurai-mp2650.ko.before','old_manifest':'device-stage/manifest.json.before'}
    return {name:root+'/'+relative for name,relative in names.items()}

def process_observation(receipt):
    root=Path('/proc',str(receipt['pid']))
    try:
        fields=(root/'stat').read_text().rsplit(')',1)[1].split()
        ticks=int(fields[19])
        if ticks!=receipt['startticks']:return dict(state='pid_reused_source_ended',pid=receipt['pid'])
        return dict(state='zombie' if fields[0]=='Z' else 'live_original',pid=receipt['pid'],startticks=ticks)
    except FileNotFoundError:return dict(state='absent',pid=receipt['pid'])

def source_processes(request,records):
    if request['identity']['boot_id']!=SOURCE_IDENTITY['boot_id']:
        return {role:dict(state='source_boot_ended',source_boot_id=SOURCE_IDENTITY['boot_id'],current_boot_id=request['identity']['boot_id']) for role in ['worker','supervisor']}
    return {role:process_observation(records[role+'_process']) for role in ['worker','supervisor']}

def verify_source_records(request,raws,processes):
    projection=request['source_stage'];paths=source_paths(projection['transaction_id'])
    need(set(projection)=={'transaction_id','evidence'} and set(projection['evidence'])==set(raws)==set(paths),'all seventeen actual source records')
    for name,path in paths.items():
        need(projection['evidence'][name]==dict(path=path,sha256=sha(raws[name])),'exact source path/bytes '+name)
    need(sha(raws['request'])==SOURCE_REQUEST_SHA and sha(raws['stage_source'])==STAGE_WORKER and
         sha(raws['supervisor'])==STAGE_SUPERVISOR and sha(raws['wrapper'])==STAGE_WRAPPER,'fixed executed original request/code')
    binary={'stage_source','wrapper','supervisor','old_charger','old_manifest'}
    records={name:json.loads(raw) for name,raw in raws.items() if name not in binary}
    original=records['request'];result=records['result'];terminal=records['worker_terminal']
    need(original['identity']==SOURCE_IDENTITY and original['worker_sha256']==STAGE_WORKER,'actual prepared source identity')
    need(terminal['terminal'] is True and terminal['returncode']==0 and terminal['receipt_error'] is None and
         terminal['process']==records['worker_process'] and terminal['pid']==records['worker_process']['pid'],'original same-child successful terminal')
    worker,supervisor=records['worker_process'],records['supervisor_process']
    for role,receipt in [('worker',worker),('supervisor',supervisor)]:
        need(set(receipt)=={'pid','startticks','argv'} and type(receipt['pid']) is type(receipt['startticks']) is int and
             receipt['pid']>0 and receipt['startticks']>0,'actual source process identity')
        suffix=['-B',ROOT+'/'+SOURCE_TX+'/'+role+'.py']+(['--supervise',ROOT+'/'+SOURCE_TX] if role=='supervisor' else [])
        need(receipt['argv'][1:]==suffix and receipt['argv'][0] in ['/usr/sbin/python3','/usr/bin/python3'],'fixed source process argv')
    need(records['supervisor_launch']==supervisor and records['launch']==dict(boot_id=SOURCE_IDENTITY['boot_id'],worker_sha256=STAGE_WRAPPER),'original supervisor launch binding')
    stage_process=records['stage_process']
    need(stage_process['pid']==worker['pid'] and stage_process['start_ticks']==worker['startticks'] and
         stage_process['argv']==worker['argv'] and stage_process['boot_id']==SOURCE_IDENTITY['boot_id'] and
         stage_process['transaction_id']==SOURCE_TX,'actual stage ran inside the original child')
    need(result['request_sha256']==SOURCE_REQUEST_SHA and result['cohort_delivery_sha256']==SOURCE_COHORT and
         result['payload_sha256']==FORWARD_PAYLOAD and result['old_manifest_sha256']==OLD_FILES[MANIFEST] and
         result['new_manifest_sha256']==NEW_FILES[MANIFEST],'exact source stage transition')
    need(result['terminal'] and result['staged'] and result['stop_verified'] and result['disk_state']=='all_new_fsynced' and
         result['status']=='staged/runtime_pending' and result['primary_error'] is result['recovery_error'] is None and
         result['activation_attempted'] is result['new_module_loaded'] is result['capture_issued'] is False,'completed cold stage only')
    for name,key in [('old_charger',TARGET),('old_manifest',MANIFEST)]:need(sha(raws[name])==OLD_FILES[key],'actual original backup')
    expected={path:dict(sha256=OLD_FILES[path],mode='0600',bytes=len(raws['old_charger' if path==TARGET else 'old_manifest'])) for path in ORDER}
    need(records['files_before']==expected,'source backup identities/modes')
    # Run the exact original pure archive/snapshot guards against the saved
    # source time frame. No Device is constructed and __main__ is never run.
    ns={'__name__':'authenticated_source_guards'};exec(compile(raws['stage_source'],'retained-timer-stage','exec'),ns)
    files,new=ns['unpack'](original);ns['manifest_delta'](json.loads(raws['old_manifest']),new)
    before,stopped,after=(records[k] for k in ['before','stopped','after'])
    need(all(value['state']['boot_id']==SOURCE_IDENTITY['boot_id'] for value in [before,stopped,after]),'source snapshots belong to the actual source boot')
    ns['time']=SimpleNamespace(CLOCK_BOOTTIME=time.CLOCK_BOOTTIME,clock_gettime=lambda _:before['read_end']+.001)
    need(ns['healthy'](before,True)==result['before_healthy_mode'],'actual original healthy mode')
    ns['time']=SimpleNamespace(CLOCK_BOOTTIME=time.CLOCK_BOOTTIME,clock_gettime=lambda _:stopped['read_end']+.001)
    ns['stopped_snapshot'](before,stopped,stopped['read_end']+.001)
    ns['time']=SimpleNamespace(CLOCK_BOOTTIME=time.CLOCK_BOOTTIME,clock_gettime=lambda _:after['read_end']+.001)
    ns['stopped_snapshot'](stopped,after,after['read_end']+.001)
    need(before['identity']==dict(SOURCE_IDENTITY,guard_sha256=original['adoption']['guard_sha256']) and
         before['notes']==stopped['notes']==after['notes']==OLD_NOTES and result['resident_notes']==OLD_NOTES,'source identity and old resident preserved')
    need(set(processes)=={'worker','supervisor'},'actual source owner observations')
    if request['identity']['boot_id']==SOURCE_IDENTITY['boot_id']:
        for role in processes:
            need(processes[role]['state'] in ['absent','zombie','pid_reused_source_ended'] and processes[role]['pid']==records[role+'_process']['pid'],'no live original source owner')
    else:
        expected=dict(state='source_boot_ended',source_boot_id=SOURCE_IDENTITY['boot_id'],current_boot_id=request['identity']['boot_id'])
        need(processes=={'worker':expected,'supervisor':expected},'never attribute old PIDs in new boot')
    return dict(source_stage_terminal_verified=True,source_result_sha256=sha(raws['result']),source_boot_ended=request['identity']['boot_id']!=SOURCE_IDENTITY['boot_id'],
                original_snapshot_guards_replayed=True,source_process_observations=processes)

def retained(before,after):
    legacy_retained(before,after)
    need(before['current_cache']==after['current_cache'],'same protection instance/cache')
    if before['sample'].get('logical_full')==1 and before['sample'].get('online')==after['sample'].get('online')==1:
        need(after['sample'].get('logical_full')==1 and after['sample'].get('full_cause')==before['sample'].get('full_cause') and
             after['sample'].get('session_seconds')==0,'online Full/cause retained')

def device_source_proof(self,request):
    paths=source_paths(request['source_stage']['transaction_id']);raws={name:read_owned(path)[0] for name,path in paths.items()}
    original=json.loads(raws['request']);guard,mode=read_owned(original['adoption']['guard_path'])
    need(mode==0o600 and guard==(SOURCE_IDENTITY['boot_id']+'\n').encode() and sha(guard)==original['adoption']['guard_sha256'],'retained original guard')
    records={name:json.loads(raws[name]) for name in ['worker_process','supervisor_process']}
    result=verify_source_records(request,raws,source_processes(request,records));self.log('source-proof-private.json',result);return result

Device.source_proof=device_source_proof



def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execute-rollback',action='store_true');parser.add_argument('--check-only',action='store_true')
    args=parser.parse_args();need(not(args.execute_rollback and args.check_only),'choose inert check or execution')
    if not args.execute_rollback:
        print(json.dumps(dict(source_only=True,device_accessed=False,runtime_request_generated=False,
            profiles=list(PROFILES),payload_sha256=ROLLBACK_PAYLOAD)));return 0
    need(not sys.flags.optimize,'nonoptimized');os.umask(0o077)
    raw=sys.stdin.buffer.read(100001);need(len(raw)<=100000,'bounded request')
    result=restore(json.loads(raw),Device(),execute=True);print(json.dumps(result),flush=True)
    return 0 if result['restored'] else 1

if __name__=='__main__':raise SystemExit(main())
