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
