"""Default inert. The retained stage filename/argv executes one MAC observation only."""
from pathlib import Path
import argparse, contextlib, errno, hashlib, json, math, os, re, stat, sys, time, uuid

sys.dont_write_bytecode = True
RELEASE = '7.3.0-rc6-rmx1931-samurai-k363+'
VERSION = '#502 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026'
MANIFEST = '5fca8e5a0795325bd780b7965579068c7edc35fa7da12bac357bb30bbde69417'
KO = '7848cfab264dde1f7f02b24b8022b951d4f3a604eba120b313bac23d0f4a3044'
NOTE = 'fc0d253d556b6ba656db263aaa50c37e3af2c7fe115b67e6b02641ae8b5733ec'
MODULE = '/sys/module/samurai_gauge_protection'
INSTANCE = '/sys/devices/platform/samurai-gauge-protection'
LOCK = '/run/lock/samurai-charging.lock'
ROOT = '/root/charging-management-20261023'
sha = lambda raw: hashlib.sha256(raw).hexdigest()

def need(ok, message):
    if not ok: raise ValueError(message)

def error_detail(error):
    return {'type': type(error).__name__, 'errno': getattr(error, 'errno', None), 'message': str(error)}

def save(path, raw):
    with Path(path).open('xb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    fd = os.open(Path(path).parent, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)

def encode(value): return (json.dumps(value, indent=2) + '\n').encode()

def validate_request(request):
    need(set(request) == {'schema', 'transaction_id', 'identity', 'adoption', 'worker_sha256', 'lease_token'}, 'request keys')
    need(request['schema'] == 'samurai-protection-capture-request-v1' and
         re.fullmatch(r'protection-capture-[a-z0-9-]{8,48}', request['transaction_id']), 'capture request/transaction')
    i, a = request['identity'], request['adoption']
    need(set(i) == {'boot_id', 'version', 'serial_sha256', 'compatible_sha256', 'rootfs_sha256'} and
         str(uuid.UUID(i['boot_id'])) == i['boot_id'] and i['version'] == VERSION, 'actual cohort new boot')
    need(set(a) == {'transaction_id', 'guard_path', 'guard_sha256', 'postboot_raw_sha256', 'fresh_validation_sha256'}, 'adoption keys')
    need(re.fullmatch(r'usb-irq-protection-activate-[a-z0-9-]{8,48}', a['transaction_id']) and
         a['guard_path'] == '/var/lib/samurai/' + a['transaction_id'] + '-adopted/boot-id-private.txt', 'actual IRQ adoption guard')
    for value in [i['serial_sha256'], i['compatible_sha256'], i['rootfs_sha256'], request['worker_sha256'],
                  a['guard_sha256'], a['postboot_raw_sha256'], a['fresh_validation_sha256']]:
        need(re.fullmatch('[0-9a-f]{64}', value), 'bound source/identity hash')
    need(a['guard_sha256'] == sha((i['boot_id'] + '\n').encode()) and re.fullmatch('[0-9a-f]{48}', request['lease_token']), 'guard/token')

def cached_header(raw):
    need(0 < len(raw) < 4096 and raw.endswith(b'\n'), 'complete bounded cached output required')
    tokens = raw.splitlines()[0].decode('ascii').split(' ')
    pairs = [token.split('=') for token in tokens]
    need(all(len(pair) == 2 for pair in pairs) and len({p[0] for p in pairs}) == len(pairs), 'cached header fields')
    fields = dict(pairs)
    need(fields.get('schema') == '1' and fields.get('attempted') in ('0', '1'), 'cached attempt/schema')
    return fields

def capture(request, device):
    """Actual algorithm; Device supplies only OS/file/clock/flock boundaries."""
    validate_request(request)
    result = {'schema': 'samurai-protection-capture-worker-v1', 'transaction_id': request['transaction_id'],
              'request_sha256': device.request_sha256, 'terminal': False, 'capture_write_attempted': False,
              'write_return': None, 'write_error': None, 'errors': [], 'identity_before': None, 'identity_after': None,
              'started_ns': device.now(), 'write_started_ns': None, 'write_ended_ns': None,
              'raw_before_sha256': None, 'raw_after_sha256': None, 'compatibility_verified': False,
              'TCA_classification': 'UNVERIFIED', 'charging_controls_written': False}
    try:
        device.begin(request)  # Exclusive intent precedes any capture; failure is never replayed.
        with device.locked():
            try:
                device.open_instance()
                result['identity_before'] = device.identity(request)
                device.check_window(request)
                raw = device.cache()
                device.raw('cache-before-private.txt', raw)
                result['raw_before_sha256'] = sha(raw)
                need(cached_header(raw)['attempted'] == '0', 'provider instance already attempted; never rearm')
                # Revalidate the held attribute fds and identity immediately before the sole store.
                need(device.identity(request) == result['identity_before'], 'identity/instance changed before store')
                device.check_window(request)
                result['capture_write_attempted'] = True
                result['write_started_ns'] = device.now()
                try:
                    result['write_return'] = device.store_capture()
                    need(result['write_return'] == 8, 'short capture store')
                except BaseException as error:
                    result['write_error'] = error_detail(error)
                finally:
                    result['write_ended_ns'] = device.now()
            finally:
                # Even failed/rejected stores retain the cache exactly as returned; no second store.
                try:
                    raw = device.cache()
                    device.raw('cache-after-private.txt', raw)
                    result['raw_after_sha256'] = sha(raw)
                    result['cache_after_read_ns'] = device.now()
                except BaseException as error:
                    result['errors'].append({'phase': 'cache_after', **error_detail(error)})
                try: result['identity_after'] = device.identity(request)
                except BaseException as error: result['errors'].append({'phase': 'identity_after', **error_detail(error)})
    except BaseException as error:
        result['errors'].append({'phase': 'capture', **error_detail(error)})
    finally:
        try: device.close()
        except BaseException as error: result['errors'].append({'phase': 'close', **error_detail(error)})
        result['ended_ns'] = device.now()
        result['terminal'] = True
        result['identity_match'] = bool(result['identity_before'] is not None and result['identity_before'] == result['identity_after'])
        result['observation_retained'] = result['raw_after_sha256'] is not None
        result['worker_complete'] = bool(result['capture_write_attempted'] and result['identity_match'] and
                                         result['observation_retained'] and not result['errors'])
        device.publish(result)
    return result

class Device:
    def __init__(self, request_raw):
        self.request_raw = request_raw; self.request_sha256 = sha(request_raw)
        self.out = None; self.fds = {}; self.instance = None

    def now(self): return time.clock_gettime_ns(time.CLOCK_BOOTTIME)

    def raw(self, name, raw): save(self.out / name, raw)

    def begin(self, request):
        need(os.geteuid() == 0 and not sys.flags.optimize, 'root non-optimized worker required')
        root = Path(ROOT) / request['transaction_id']
        info = root.lstat()
        need(stat.S_ISDIR(info.st_mode) and info.st_uid == 0 and stat.S_IMODE(info.st_mode) == 0o700 and not root.is_symlink(), 'owned transport directory')
        need(Path(__file__).resolve() == root / 'stage-worker.py' and sha(Path(__file__).read_bytes()) == request['worker_sha256'], 'actual worker source/path')
        out = root / 'device-stage'; out.mkdir(mode=0o700)  # exclusive one-shot intent
        self.out = out
        fields = Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()
        argv = [x.decode() for x in Path('/proc/self/cmdline').read_bytes().split(b'\0') if x]
        self.raw('process-private.json', encode({'transaction_id': request['transaction_id'], 'boot_id': request['identity']['boot_id'],
                 'pid': os.getpid(), 'start_ticks': int(fields[19]), 'argv': argv, 'worker_sha256': request['worker_sha256']}))
        self.raw('request-private.json', self.request_raw)
        self.raw('capture-intent-private.json', encode({'request_sha256': self.request_sha256, 'capture_store_count_max': 1,
                 'no_replay': True, 'started_ns': self.now()}))

    @contextlib.contextmanager
    def locked(self):
        import fcntl
        fd = os.open(LOCK, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            info = os.fstat(fd)
            need(stat.S_ISREG(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022, 'original charging lock')
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield
        finally: os.close(fd)

    def open_instance(self):
        need(Path(INSTANCE, 'driver').resolve().as_posix() == '/sys/bus/platform/drivers/samurai-gauge-protection', 'actual protection driver')
        for name, flag in [('mac_evidence', os.O_RDONLY), ('mac_evidence_capture', os.O_WRONLY)]:
            self.fds[name] = os.open(Path(INSTANCE, name), flag | os.O_CLOEXEC | os.O_NOFOLLOW)
        self.instance = Path(INSTANCE).stat().st_ino

    def identity(self, request):
        i, a = request['identity'], request['adoption']
        boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        comp = Path('/sys/firmware/devicetree/base/compatible').read_bytes()
        values = {'boot_id': boot, 'version': os.uname().version,
                  'serial_sha256': sha(Path('/sys/devices/soc0/serial_number').read_bytes()),
                  'compatible_sha256': sha(comp), 'rootfs_sha256': sha(Path('/etc/samurai-rootfs-release').read_bytes())}
        need(values == i and os.uname().release == RELEASE and b'realme,samurai' in comp.split(b'\0'), 'current identity differs')
        guard = Path(a['guard_path']).read_bytes()
        need(guard == (boot + '\n').encode() and sha(guard) == a['guard_sha256'], 'current adopted guard differs')
        proof = Path(a['guard_path']).parent.joinpath('fresh-validation-private.json').read_bytes()
        need(sha(proof) == a['fresh_validation_sha256'], 'actual IRQ adoption fresh proof differs')
        need(sha(Path('/usr/share/samurai-charging/manifest.json').read_bytes()) == MANIFEST, 'new manifest required')
        need(sha(Path('/lib/modules', RELEASE, 'extra/samurai-charging/samurai-gauge-protection.ko').read_bytes()) == KO and
             sha(Path(MODULE, 'notes/.note.gnu.build-id').read_bytes()) == NOTE and
             Path(MODULE, 'initstate').read_text().strip() == 'live', 'new disk/resident protection required')
        need(Path(INSTANCE, 'driver').resolve().as_posix() == '/sys/bus/platform/drivers/samurai-gauge-protection' and
             Path(INSTANCE).stat().st_ino == self.instance, 'same bound platform instance required')
        attrs = {}
        for name, fd in self.fds.items():
            held, current = os.fstat(fd), Path(INSTANCE, name).stat()
            need((held.st_dev, held.st_ino) == (current.st_dev, current.st_ino), 'same held kernfs attributes required')
            attrs[name] = [held.st_dev, held.st_ino]
        need(len(attrs) == 2, 'both original attribute descriptors required')
        return {**values, 'guard_sha256': sha(guard), 'manifest_sha256': MANIFEST,
                'protection_ko_sha256': KO, 'loaded_note_sha256': NOTE, 'instance_inode': self.instance, 'attributes': attrs}

    def check_window(self, request):
        lease = json.loads(Path('/run', request['transaction_id'] + '-window-private.json').read_bytes())
        now = self.now() / 1e9
        need(lease['transaction_id'] == request['transaction_id'] and lease['boot_id'] == request['identity']['boot_id'] and
             lease['token'] == request['lease_token'] and lease['owner'] == 'charging' and
             all(lease[k] is True for k in ('exclusive', 'camera_released', 'bluetooth_released')), 'current coordinated lease')
        start, end = lease['issued_boottime_s'], lease['expires_boottime_s']
        need(type(start) in (int, float) and type(end) in (int, float) and math.isfinite(start) and math.isfinite(end) and
             0 <= start <= now < end <= start + 120, 'bounded unexpired capture lease')

    def cache(self):
        fd = self.fds['mac_evidence']; os.lseek(fd, 0, os.SEEK_SET)
        raw = os.read(fd, 4096)
        need(0 < len(raw) < 4096 and raw.endswith(b'\n'), 'complete cached report')
        return raw

    def store_capture(self): return os.write(self.fds['mac_evidence_capture'], b'capture\n')

    def close(self):
        errors = []
        for name, fd in list(self.fds.items()):
            try: os.close(fd)
            except OSError as error: errors.append(error_detail(error))
        self.fds = {}
        need(not errors, 'held attribute close errors: ' + repr(errors))

    def publish(self, result):
        if self.out is not None: self.raw('result.json', encode(result))

def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--execute-stage', action='store_true')
    args = parser.parse_args()
    if not args.execute_stage:
        print(json.dumps({'source_only': True, 'device_accessed': False, 'runtime_request_created': False})); return 0
    need(not sys.flags.optimize, 'non-optimized worker required'); os.umask(0o077)
    raw = sys.stdin.buffer.read(16001); need(len(raw) <= 16000, 'bounded request')
    result = capture(json.loads(raw), Device(raw)); print(json.dumps(result), flush=True)
    # Protocol/bus error is evidence, not a transport failure. No policy acceptance is made.
    return 0 if result['worker_complete'] else 1

if __name__ == '__main__': raise SystemExit(main())
