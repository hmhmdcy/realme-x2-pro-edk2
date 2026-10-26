#!/usr/bin/python3
"""Stage only the reviewed USB FLOAT module and manifest; import is inert."""
from pathlib import Path
import base64
import copy
import ctypes as C
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

RELEASE = '7.3.0-rc6-rmx1931-samurai-k363+'
ROOT = '/root/charging-management-20261023'
USB = '/lib/modules/' + RELEASE + '/extra/samurai-charging/samurai-usb-input.ko'
MANIFEST = '/usr/share/samurai-charging/manifest.json'
SERVICE = '/usr/sbin/samurai-charging'
GUARD = '/var/lib/samurai/k449-adopted/boot-id-private.txt'
WINDOW = '/run/samurai-charging-source-stage-r7-window.json'
LOCK = '/run/lock/samurai-charging.lock'
OLD = '944f2d91f66c5642bbcb130c3ef59e022ca6652e599401908f8528a29d34202d'
NEW = '5638db4c183ec502ed1df4facfe91111d1956754bb2338a5ddaf8838e9552c68'
PAYLOAD = '4222242fe16c37beccf2000495c745feec06c4ecaa901c65e1fd6bf5f3685978'
OLD_USB = 'c77724ba582f66905ca08d1b185926a540691bd559614d20fa574d4b35492e3e'
NEW_USB = '7d4e0f948b993a6e0cc9459bac4ade2db2fe7b88ce7b7d462ea34bcb933c4f70'
MANAGER = '61451ffea87cca466dbbb2f1a2c6e7c05d0eee517479e8b019d43b1869355aa4'
UNCHANGED = {'samurai-mp2650': 'fac827cfd3d1d847cb1db82f0a29e451652bd16a996b20666be2d9b330889cb6',
             'samurai-gauge-protection': '75b97e0d6b906ec600171ce68adec6f25a91556758f76bbf3d563cf831e783c7'}
FILES = {USB: NEW_USB, MANIFEST: NEW}
OLD_FILES = {USB: OLD_USB, MANIFEST: OLD}
FLOAT = {'0x1307': 0x21, '0x1308': 0x10, '0x1310': 0x10, '0x1506': 8,
         '0x1509': 0x23, '0x150b': 0x2b, '0x150d': 6}


def sha(raw): return hashlib.sha256(raw).hexdigest()
def need(ok, message):
    if not ok: raise RuntimeError(message)
def detail(error): return type(error).__name__ + ': ' + str(error)


class UnknownWriteState(RuntimeError):
    """Target could not be proved old or new. No further replacement allowed."""


class AtomicWriteFailure(RuntimeError):
    """A synchronous file operation failed, but target bytes/mode are known."""


def read_owned(path):
    path = Path(path); st = path.lstat()
    need(stat.S_ISREG(st.st_mode) and st.st_uid == 0 and not st.st_mode & 0o022,
         'regular root-owned protected file: ' + str(path))
    return path.read_bytes(), stat.S_IMODE(st.st_mode)


def atomic_replace(path, raw, transaction, allowed_hashes, ops=os):
    """Actual temp-write/fsync/rename/dir-fsync boundary, with readback on error."""
    path = Path(path); temporary = path.with_name('.' + path.name + '.' + transaction + '.next')
    old, mode = read_owned(path)
    need(mode == 0o600 and sha(old) in allowed_hashes, 'target identity changed before atomic replacement')
    created = False; descriptor = directory = None; cleanup = []
    try:
        descriptor = ops.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        created = True; offset = 0
        while offset < len(raw):
            count = ops.write(descriptor, raw[offset:])
            if not isinstance(count, int) or not 0 < count <= len(raw) - offset:
                raise OSError(errno.EIO, 'short/invalid regular-file write')
            offset += count
        ops.fchmod(descriptor, 0o600); ops.fsync(descriptor); ops.close(descriptor); descriptor = None
        ops.replace(temporary, path)
        directory = ops.open(path.parent, os.O_DIRECTORY | os.O_RDONLY)
        ops.fsync(directory); ops.close(directory); directory = None
        actual, mode = read_owned(path)
        need(actual == raw and mode == 0o600, 'new file bytes/mode readback differs')
        return {'sha256': sha(actual), 'mode': '0o600', 'file_and_directory_fsynced': True}
    except BaseException as failure:
        # No asynchronous child exists. Classify the actual target before any
        # recovery; an unexpected/read-unavailable target must never be erased.
        try:
            current, current_mode = read_owned(path)
            known = current_mode == 0o600 and sha(current) in set(allowed_hashes) | {sha(raw)}
        except BaseException:
            known = False
        if not known:
            raise UnknownWriteState(detail(failure) + '; target identity unproved') from failure
        raise AtomicWriteFailure(detail(failure) + '; current target sha256=' + sha(current)) from failure
    finally:
        for fd in [descriptor, directory]:
            if fd is not None:
                try: ops.close(fd)
                except OSError as error: cleanup.append(detail(error))
        if created:
            try: ops.unlink(temporary)
            except FileNotFoundError: pass
            except OSError as error: cleanup.append(detail(error))
        # A leftover exclusive temporary prevents replay; never remove an
        # unowned pre-existing temp. Cleanup failure is independently visible.
        if cleanup and sys.exc_info()[0] is None:
            raise AtomicWriteFailure('temporary/descriptor cleanup: ' + repr(cleanup))
        if cleanup and sys.exc_info()[1] is not None:
            active = sys.exc_info()[1]
            active.args = (str(active) + '; cleanup=' + repr(cleanup),)


def unpack(request):
    need(set(request) == {'transaction', 'guard', 'identity', 'window_token', 'old_manifest_sha256',
                         'new_manifest_sha256', 'payload_sha256', 'payload_base64'}, 'exact r7 request schema')
    need(re.fullmatch(r'source-stage-r7-[a-z0-9][a-z0-9-]{0,32}', request['transaction']), 'new r7 transaction name')
    need(request['guard'] == GUARD, 'original adopted boot guard')
    need((request['old_manifest_sha256'], request['new_manifest_sha256'], request['payload_sha256']) ==
         (OLD, NEW, PAYLOAD), 'exact reviewed r6/r7 payload identity')
    identity = request['identity']
    need(set(identity) == {'boot_id', 'serial_sha256', 'compatible_sha256'}, 'exact SoC identity schema')
    need(str(uuid.UUID(identity['boot_id'])) == identity['boot_id'], 'explicit adopted boot UUID')
    for key in ['serial_sha256', 'compatible_sha256']:
        need(re.fullmatch(r'[a-f0-9]{64}', identity[key]), 'explicit adopted SoC digest')
    need(re.fullmatch(r'[a-f0-9]{48}', request['window_token']), 'unique private 24-byte lease token')
    raw = base64.b64decode(request['payload_base64'], validate=True)
    need(len(raw) == 23617 and sha(raw) == PAYLOAD, 'exact frozen r7 payload bytes')
    files = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as archive:
        members = archive.getmembers(); need(len(members) == 2, 'exactly two tar members')
        for entry in members:
            target = '/' + entry.name
            need(target in FILES and target not in files and entry.name == target.lstrip('/'), 'exact tar member path')
            need(entry.isfile() and entry.uid == entry.gid == 0 and entry.mode == 0o600
                 and entry.uname == entry.gname == 'root' and entry.mtime == 0, 'exact tar member type/owner/mode/time')
            content = archive.extractfile(entry).read()
            need(sha(content) == FILES[target], 'exact tar member bytes: ' + target); files[target] = content
    return files, json.loads(files[MANIFEST])


def manifest_delta(old, new):
    expected = copy.deepcopy(old); expected['adapter_revision'] = 'r7'
    expected['modules']['samurai-usb-input']['sha256'] = NEW_USB
    expected['installed_files'][USB] = NEW_USB
    need(expected == new, 'only USB hash and r7 revision may differ')
    need(old['release'] == RELEASE and old['modules']['samurai-usb-input'] == {'target': USB, 'sha256': OLD_USB}, 'old USB/ABI identity')
    need(old['installed_files'][SERVICE] == MANAGER, 'unchanged exact manager 614')
    for name, digest in UNCHANGED.items(): need(old['modules'][name]['sha256'] == digest, 'unchanged resident module: ' + name)
    need(old['default_input_cap_ua'] == 900000 and old['default_charge_cap_ua'] == 250000
         and old['source_budget_enforced'] is True, 'unchanged limits and source authority')


def safe_float(data, now):
    s = data['sample']; zero = ['shadow', 'valid', 'protection_ok', 'budget_ua', 'temp_decic', 'pack_uv',
        'cell1_uv', 'cell2_uv', 'flags', 'fault', 'desired_enable', 'stop_error', 'latched', 'thermal_inhibit',
        'cycle_timeout', 'gauge_current_ua', 'logical_full', 'full_holding', 'hold_requested', 'full_cause',
        'sw_full_count', 'recharge_count', 'gauge_charge_stop']
    need(all(s.get(k) == 0 for k in zero) and s.get('online') == s.get('source_inhibit') == 1
         and s.get('error') == -errno.ENODATA and s.get('age_ms') == -1
         and 0 <= s.get('session_seconds', -1) < 36000, 'exact known stopped source-FLOAT placeholders; no cached fault/stop/latch')
    need(data['pmic_before'] == data['pmic_after'] == FLOAT, 'exact current physical FLOAT signature')
    source = {'online': 1, 'current_max_errno': errno.ENODATA, 'native_ua': 100000, 'usb_type': '[Unknown] SDP DCP CDP C'}
    need(data['source_before'] == data['source_after'] == source, 'exact current old-provider FLOAT/native-100 state')
    need(data['registers']['08'] & 0x18 == 8 and data['registers']['13'] & 2, 'physical INHIBIT plus ACOK readback')
    need(data['native_retained'] == 'Y', 'resident DWC3 native provider retained')
    need(data['protection_health'] == 'Good' and data['protection_present'] == 1, 'independent fresh protection Good/present')
    p = data['protection_state']
    need(p.get('id') == 0x2719 and p.get('safety') == p.get('pf') == p.get('error') == 0
         and p.get('operation', 0) & 0x300 == 0x300
         and not p.get('operation', 0) & ((1 << 20) | (1 << 16) | 0x7c00)
         and p.get('manufacturing', 0) & 0x18 == 0x18
         and not p.get('manufacturing', 0) & 0x8006, 'fresh factory sealed autonomous protection state')
    g = data['gauge']
    need(0 <= g.get('flags', -1) <= 0xffff and not g['flags'] & 0xc000
         and -20 <= g.get('temp_decic', -999) < 530 and 4000000 <= g.get('pack_uv', 0) <= 9200000,
         'fresh independent standard gauge, no TCA/OCA and in absolute operating range')
    need(0 <= data['read_end_boottime'] - data['read_start_boottime'] <= 3
         and 0 <= now - data['read_end_boottime'] <= 1, 'fresh bounded observation; placeholders are not cached Good')
    need(data['state']['taint'] == '0' and data['state']['driver'] == 'samurai-mp2650', 'taint zero and real managed charger')


def unchanged(before, after):
    for key in ['boot_id', 'release', 'camera_pm', 'm2m', 'services']:
        need(before['state'][key] == after['state'][key], 'environment changed: ' + key)
    need(before['notes'] == after['notes'], 'resident three build-id notes changed')
    need(before['openrc_started'] is after['openrc_started'] is True, 'OpenRC started marker preserved')


def stage(request, device, execute=False):
    need(execute, 'explicit --execute-r7-stage required')
    result = {'schema': 'samurai-source-stage-r7-result-v1', 'transaction': request.get('transaction'),
              'phase': 'rejected', 'staged': False, 'runtime_pending': True, 'terminal': True,
              'primary_error': None, 'stop_error': None, 'recovery_error': None,
              'unknown_write_state': False, 'disk_state': 'not_changed', 'stop_verified': False,
              'activation': 'root-coordinated normal reboot required; no runtime activation attempted'}
    phase = 'request'; backup = manager = old = before = None; attempted = False
    try:
        files, new = unpack(request)
        phase = 'begin'; device.begin(request)
        phase = 'preflight'; backup = {name: device.read_owned(name) for name in FILES}
        for name, (raw, mode) in backup.items(): need(mode == 0o600 and sha(raw) == OLD_FILES[name], 'exact old bytes/mode: ' + name)
        old = json.loads(backup[MANIFEST][0]); manifest_delta(old, new)
        manager = device.manager(); need(device.verify(manager) == old, 'fresh actual manager.verify r6')
        device.notes_match(manager, old)
        before = device.observe(manager); safe_float(before, device.now()); unchanged(before, before)
        device.backup(backup, before)
        phase = 'synchronous-stop'; device.check_window(request)
        try:
            device.stop(manager, old)
            need(device.registers(manager)['08'] & 0x18 == 8, 'direct old manager.stop synchronous hardware INHIBIT')
            result['stop_verified'] = True
        except BaseException as error:
            result['stop_error'] = detail(error); raise
        phase = 'stopped-proof'; paused = device.observe(manager); safe_float(paused, device.now()); unchanged(before, paused)
        device.log('stopped-private.json', paused)
        for name in [USB, MANIFEST]:
            phase = 'replace-usb' if name == USB else 'replace-manifest'; device.check_window(request)
            attempted = True; device.replace(name, files[name], {OLD_FILES[name]})
        phase = 'staged-proof'; device.check_window(request)
        need(device.verify(manager) == new, 'fresh unchanged manager verifies new disk manifest')
        device.notes_match(manager, old, use_backup=True)
        after = device.observe(manager); safe_float(after, device.now()); unchanged(before, after)
        for name in FILES:
            raw, mode = device.read_owned(name); need(sha(raw) == FILES[name] and mode == 0o600, 'new disk bytes/mode')
        device.log('after-private.json', after)
        result.update(phase='staged', staged=True, disk_state='r7_files_staged',
                      old_manifest_sha256=OLD, new_manifest_sha256=NEW,
                      resident_usb_sha256=OLD_USB, resident_usb_note_sha256=after['notes']['samurai-usb-input'],
                      resident_provider_still_r6=True, manager_sha256=MANAGER,
                      source_float_runtime_fixed=False, configuration='INHIBIT retained')
    except BaseException as error:
        result['phase'] = 'rejected' if phase in ['request', 'begin', 'preflight'] else 'failed'
        result['primary_error'] = {'phase': phase, 'error': detail(error)}
        result['unknown_write_state'] = isinstance(error, UnknownWriteState)
        if attempted and not result['unknown_write_state']:
            try:
                device.check_window(request)  # no recovery under a changed/expired owner or boot
                device.known_files()         # prove both targets before restoring either
                for name in [USB, MANIFEST]:
                    device.replace(name, backup[name][0], {OLD_FILES[name], FILES[name]})
                need(device.verify(manager) == old, 'actual manager verifies exact restored old pair')
                device.notes_match(manager, old)
                need(device.registers(manager)['08'] & 0x18 == 8, 'INHIBIT retained after disk restoration')
                result['disk_state'] = 'r6_pair_restored_inhibited'
            except BaseException as recovery:
                result['recovery_error'] = detail(recovery)
                result['unknown_write_state'] |= isinstance(recovery, UnknownWriteState)
                result['disk_state'] = 'recovery_failed_inspect_before_boot'
        elif attempted:
            result['disk_state'] = 'unknown_inspect_before_boot_no_rollback'
    finally:
        try: device.finish(result)
        except BaseException as error: result['receipt_error'] = detail(error)
        try: device.close()
        except BaseException as error: result['close_error'] = detail(error)
    return result


class Device:
    """Only fixed read boundaries, original stop, and the exact two disk files."""
    def __init__(self): self.out = None; self.lock = None; self.events = []; self.transaction = None
    def now(self): return time.clock_gettime(time.CLOCK_BOOTTIME)
    def read_owned(self, name): return read_owned(name)
    def check_window(self, request):
        need(Path('/proc/sys/kernel/random/boot_id').read_text().strip() == request['identity']['boot_id']
             == Path(GUARD).read_text().strip(), 'same explicit boot and original guard')
        base = Path('/sys/firmware/devicetree/base'); compatible = (base / 'compatible').read_bytes()
        serial = Path('/sys/devices/soc0/serial_number').read_bytes()
        need(serial.strip() and sha(serial) == request['identity']['serial_sha256']
             and sha(compatible) == request['identity']['compatible_sha256']
             and b'realme,samurai' in compatible.split(b'\0'), 'exact adopted SoC serial/compatible identity')
        raw, mode = self.read_owned(WINDOW); lease = json.loads(raw); now = self.now()
        need(mode == 0o600 and lease['transaction'] == request['transaction'] and lease['owner'] == 'charging'
             and lease['token'] == request['window_token'] and lease['boot_id'] == request['identity']['boot_id']
             and lease['camera_released'] is lease['bluetooth_released'] is lease['exclusive'] is True,
             'explicit exclusive camera and Bluetooth handback lease')
        issued, expires = lease['issued_boottime_s'], lease['expires_boottime_s']
        need(all(type(x) in [int, float] and math.isfinite(x) for x in [issued, expires])
             and issued <= now < expires and 0 < expires - issued <= 120, 'live explicit lease at most 120 BOOTTIME seconds')
    def begin(self, request):
        import fcntl
        need(os.geteuid() == 0 and os.uname().release == RELEASE and not sys.flags.optimize, 'root/exact ABI/assertions enabled')
        need(Path('/sys/bus/i2c/devices/0-005c/name').read_text().strip() == 'mp2650', 'real charger client')
        need(Path('/sys/bus/i2c/devices/0-005c/of_node').resolve().as_posix().endswith('/soc@0/geniqup@8c0000/i2c@884000/charger@5c'), 'real charger node')
        self.check_window(request)
        self.lock = os.open(LOCK, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        st = os.fstat(self.lock)
        need(st.st_uid == 0 and stat.S_ISREG(st.st_mode) and not st.st_mode & 0o022, 'original service lock identity')
        fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        out = Path(ROOT) / request['transaction']; out.mkdir(mode=0o700)
        self.out = out; self.transaction = request['transaction']; self.check_window(request)
        self.log('request-private.json', {k: v for k, v in request.items() if k != 'payload_base64'})
    def manager(self):
        need(sha(self.read_owned(SERVICE)[0]) == MANAGER, 'exact installed manager 614 before load')
        manager = runpy.run_path(SERVICE)
        need(sha(self.read_owned(SERVICE)[0]) == MANAGER, 'exact installed manager 614 after fresh load')
        self.events.append(['fresh-manager', MANAGER]); return manager
    def verify(self, manager):
        need(sha(self.read_owned(SERVICE)[0]) == MANAGER, 'no stale/changed manager code')
        return manager['verify']()
    def notes_match(self, manager, meta, use_backup=False):
        for name, entry in meta['modules'].items():
            need(Path('/sys/module', name.replace('-', '_'), 'initstate').read_text().strip() == 'live', 'known resident module: ' + name)
            path = self.out / 'usb-before.ko' if use_backup and name == 'samurai-usb-input' else Path(entry['target'])
            manager['loaded_matches'](path, name.replace('-', '_'))
    def registers(self, manager):
        need(0x14 not in manager['live'].REGS, 'never consume clear-on-read fault register')
        return manager['live'].registers()
    def stop(self, manager, old):
        need(sha(self.read_owned(SERVICE)[0]) == MANAGER, 'fresh stop manager identity')
        self.events.append(['direct-manager-command', MANAGER, 'stop'])
        answer = manager['command'](old, 'stop')
        need(answer.get('managed') is True and answer.get('requested') == 'inhibit-charge', 'old synchronous managed stop')
    def pmic(self):
        root = Path('/sys/kernel/debug/regmap/0-02')
        need((root / 'name').read_text().strip() == 'pmic-spmi' and (root / 'range').read_text() == '0-ffff\n', 'fixed PMIC read view')
        fd = os.open(root / 'registers', os.O_RDONLY | os.O_CLOEXEC)
        try:
            result = {}
            for name in FLOAT:
                reg = int(name, 16); raw = os.pread(fd, 9, reg * 9)
                match = re.fullmatch(rb'([0-9a-f]{4}): ([0-9a-f]{2})\n', raw)
                need(match and int(match[1], 16) == reg, 'fixed read-only PMIC address')
                result[name] = int(match[2], 16)
            return result
        finally: os.close(fd)
    def source(self, live):
        p = live.PSY / 'samurai-usb-input'
        try: (p / 'current_max').read_text(); maximum_errno = None
        except OSError as error: maximum_errno = error.errno
        return dict(online=int((p / 'online').read_text()), current_max_errno=maximum_errno,
                    native_ua=int((p / 'input_current_limit').read_text()), usb_type=(p / 'usb_type').read_text().strip())
    def gauge(self, live):
        need(Path('/sys/bus/i2c/devices/5-0055/name').read_text().strip() == 'bq28z610'
             and Path('/sys/bus/i2c/devices/5-0055/driver').resolve().name == 'bq27xxx-battery', 'original gauge driver')
        libc = C.CDLL(None, use_errno=True); fd = os.open('/dev/i2c-5', os.O_RDWR | os.O_CLOEXEC)
        try:
            words = {}
            for reg in [0x06, 0x08, 0x0a]:
                tx = C.create_string_buffer(bytes([reg])); rx = C.create_string_buffer(2)
                messages = (live.Msg * 2)(live.Msg(0x55, 0, 1, C.cast(tx, C.c_void_p)), live.Msg(0x55, 1, 2, C.cast(rx, C.c_void_p)))
                ret = libc.ioctl(fd, 0x0707, C.byref(live.Transfer(messages, 2)))
                if ret != 2: raise OSError(C.get_errno() if ret < 0 else errno.EIO, 'fixed standard gauge word')
                words[reg] = int.from_bytes(rx.raw, 'little')
            return {'temp_decic': words[6] - 2731, 'pack_uv': words[8] * 1000, 'flags': words[0x0a]}
        finally: os.close(fd)
    def observe(self, manager):
        live = manager['live']; start = self.now(); source = self.source(live); pmic = self.pmic()
        health = (live.PSY / 'samurai-gauge-protection/health').read_text().strip()
        present = int((live.PSY / 'samurai-gauge-protection/present').read_text())
        raw = Path('/sys/devices/platform/samurai-gauge-protection/protection_state').read_text()
        protection = {k: int(v, 0) for k, v in (item.split('=') for item in raw.split())}
        gauge = self.gauge(live); state = live.state()
        notes = {name: sha(Path('/sys/module', name.replace('-', '_'), 'notes/.note.gnu.build-id').read_bytes())
                 for name in ['samurai-usb-input', *UNCHANGED]}
        need('14' not in state['registers'], 'no new REG14 read')
        result = dict(read_start_boottime=start, sample=manager['sample'](), source_before=source,
                      pmic_before=pmic, protection_health=health, protection_present=present,
                      protection_state=protection, gauge=gauge, state=state, registers=state['registers'], notes=notes,
                      native_retained=Path('/sys/module/samurai_usb_input/parameters/native_retained').read_text().strip(),
                      openrc_started=Path('/run/openrc/started/samurai-charging').exists(),
                      source_after=self.source(live), pmic_after=self.pmic())
        result['read_end_boottime'] = self.now(); return result
    def backup(self, files, before):
        for name, saved in [(USB, 'usb-before.ko'), (MANIFEST, 'manifest-before.json')]:
            raw, mode = files[name]; need(mode == 0o600, 'backup exact old mode')
            path = self.out / saved
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(raw); stream.flush(); os.fchmod(stream.fileno(), mode); os.fsync(stream.fileno())
        self.log('before-private.json', {'observation': before, 'files': {n: {'sha256': sha(v[0]), 'mode': oct(v[1])} for n, v in files.items()}})
        fd = os.open(self.out, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)
    def replace(self, name, raw, allowed):
        need(name in FILES and sha(raw) in {FILES[name], OLD_FILES[name]}, 'only exact old/new two-file pair')
        self.events.append(['replace', name, sha(raw)])
        return atomic_replace(name, raw, self.transaction, allowed)
    def known_files(self):
        for name in FILES:
            try: raw, mode = self.read_owned(name)
            except BaseException as error: raise UnknownWriteState('cannot classify both targets: ' + detail(error)) from error
            if mode != 0o600 or sha(raw) not in {FILES[name], OLD_FILES[name]}: raise UnknownWriteState('unexpected target: ' + name)
    def log(self, name, value):
        if self.out is None: return
        with (self.out / name).open('x') as stream:
            json.dump(value, stream, indent=2); stream.flush(); os.fsync(stream.fileno())
    def finish(self, result):
        if self.out is None: return
        final = {}
        for name in FILES:
            try:
                raw, mode = self.read_owned(name); final[name] = {'sha256': sha(raw), 'mode': oct(mode)}
            except BaseException as error: final[name] = {'error': detail(error)}
        result['final_files'] = final; self.log('events-private.json', self.events); self.log('result.json', result)
    def close(self):
        if self.lock is not None: os.close(self.lock); self.lock = None


def main():
    need(sys.argv[1:] == ['--execute-r7-stage'], 'explicit --execute-r7-stage required')
    os.umask(0o077)
    result = stage(json.loads(sys.stdin.buffer.read()), Device(), execute=True)
    print(json.dumps(result), flush=True)
    return 0 if result['staged'] and not result.get('receipt_error') and not result.get('close_error') else 1


if __name__ == '__main__': raise SystemExit(main())
