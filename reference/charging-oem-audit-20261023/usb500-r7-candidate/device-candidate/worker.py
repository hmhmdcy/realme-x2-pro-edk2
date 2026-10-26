#!/usr/bin/python3
"""Offline candidate: one volatile r7 USB500 diagnostic, always restore100.
No device/network action on import. No launcher or installed-file updates.
"""
from pathlib import Path
from datetime import datetime
import fcntl
import importlib.util
import json
import os
import signal
import stat
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
BASE_SHA = 'cef5c0f585e4f77db77c93652a7d30c0edf1903e7586f21e7fb89a62a3129902'
HEALTH_SHA = 'a41942f21773c97b22d0b3760b1e256650f8e5506ee6cd0883db7145a39f4b4f'
TX = 'usb500-r7-diagnostic-v1'
PREFIX = '/root/charging-management-20261023/' + TX + '-'
WINDOW = '/run/samurai-usb500-r7-window.json'
GADGET = '/sys/kernel/config/usb_gadget/samurai'
BINDING = 'a600000.usb'


def library(name, file, digest):
    import hashlib
    path = HERE / file
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise RuntimeError('frozen helper mismatch: ' + file)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


r6 = library('usb500_r7_base', 'r7-base.py', BASE_SHA)
health = library('usb500_health', 'health.py', HEALTH_SHA)
need, detail = r6.need, r6.detail


def configure(io, ma, deadline):
    """Old actual configure() ordering, journaled and single-write bounded.
    Skip unbind only when readback already proves unbound after a prior error.
    """
    need(ma in (100, 500), 'only diagnostic100/500')
    tag = str(ma)
    state = io.gadget_state()
    if state['binding']:
        io.write('UDC', '\n', tag + ':unbind', deadline)
        need(io.gadget_state()['binding'] == '', 'unbind readback')
    io.write('MaxPower', tag + '\n', tag + ':power', deadline)
    state = io.gadget_state()
    need(state == {'binding': '', 'power_ma': ma}, 'unbound descriptor readback')
    io.pause(2)
    need(io.gadget_state() == state, 'descriptor changed before bind')
    io.write('UDC', BINDING + '\n', tag + ':bind', deadline)
    need(io.gadget_state() == {'binding': BINDING, 'power_ma': ma}, 'bound descriptor readback')
    io.network(deadline)
    io.event('configured-local', power_ma=ma)  # not host authorization


def accepted(row, ma):
    status = health.classify(row['sample'])
    need(status in ('managed', 'full_holding'), 'health=' + status)
    r6.healthy(row, allow_full=True)  # exact Full, current budget + both physical inputs
    source = row['source']
    need(row['udc'] == 'configured' and source['online'] == '1' and '[SDP]' in source['usb_type'], 'configured native SDP')
    need(source['input_current_limit'] == source['current_max'] == str(ma * 1000), 'native host callback allowance')
    need(row['limits']['source_budget_ua'] == int(source['current_max']) == row['sample']['budget_ua'], 'effective source budget and fresh sample agree')
    need(row['limits']['native_ua'] == row['limits']['input_ua'] == ma * 1000, 'exact source and physical input limit')
    return status


def stable(io, ma, deadline):
    since = None
    previous = None
    count = 0
    while io.now() < deadline:
        row = io.snapshot()
        count += 1
        io.event('sample', power_ma=ma, observation=row)
        observed = io.now()
        if observed >= deadline:
            break
        if previous is not None and observed-previous > 2:
            since = None  # a read stall is not continuous healthy evidence
        previous = observed
        sample = row['sample']
        need(not any(sample.get(k, 1) for k in ('fault', 'stop_error', 'latched', 'cycle_timeout')), 'hard fault/old timeout observed')
        try:
            state = accepted(row, ma)
        except RuntimeError:
            since = None
        else:
            if since is None:
                since = observed
            if observed - since >= 12:
                return row, state, count
        io.pause(.5)
    raise RuntimeError('no continuous12s native%d healthy configuration' % ma)


def transaction(config, io):
    result = {'transaction': TX, 'passed': False, 'diagnostic_completed': False, 'terminal': True,
              'host_trigger_nonce': config.get('host_trigger_nonce'), 'configured500_local': False,
              'native500_accepted': False, 'restore100_verified': False,
              'descriptor100_bound': False,
              'primary_error': None, 'recovery_error': None, 'final_error': None,
              'mutating_state_unknown': False, 'power_supply_budget_writes': 0}
    before = environment = None
    phase = 'preflight'
    try:
        io.begin(config)
        before = io.preflight()
        accepted(before, 100)
        need(before['limits']['charge_ua'] == 250000 and io.gadget_state() == {'binding': BINDING, 'power_ma': 100}, 'original100/250 setup')
        environment = io.environment()
        io.event('before', observation=before, environment=environment)
        phase = 'attempt500'
        deadline = io.now() + 45
        configure(io, 500, deadline)
        result['configured500_local'] = True
        _, state, count = stable(io, 500, deadline)
        result.update(native500_accepted=True, accepted500_state=state, samples500=count)
    except Exception as error:
        result['primary_error'] = {'phase': phase, 'error': detail(error)}
    finally:
        if io.touched:
            if io.uncertain:
                result['recovery_error'] = 'unknown sysfs/child state; no next mutation, original worker quarantined'
            else:
                try:
                    io.restoring = True
                    io.event('restore100-start')
                    deadline = io.now() + 30
                    configure(io, 100, deadline)  # one restore, on either500 outcome
                    after, state, count = stable(io, 100, deadline)
                    r6.unchanged(before, after)
                    need(after['limits']['charge_ua'] == before['limits']['charge_ua']
                         and after['limits']['cv_uv'] == before['limits']['cv_uv'], 'charge/CV caps unchanged')
                    need(io.environment() == environment, 'camera/log counters/installed identities changed')
                    result.update(restore100_verified=True, restored_state=state, samples100=count)
                except Exception as error:
                    result['recovery_error'] = detail(error)
        try:
            if io.started and not io.uncertain:
                result['final_gadget'] = io.gadget_state()
                result['descriptor100_bound'] = result['final_gadget'] == {'binding': BINDING, 'power_ma': 100}
                result['final_observation'] = io.snapshot()
                if result['restore100_verified']:
                    accepted(result['final_observation'], 100)
                    r6.unchanged(before, result['final_observation'])
                    need(all(result['final_observation']['limits'][k] == before['limits'][k]
                             for k in ('charge_ua', 'cv_uv')), 'final charge/CV caps unchanged')
        except Exception as error:
            result['final_error'] = detail(error)
            result['restore100_verified'] = False
        result['mutating_state_unknown'] = io.uncertain
        result['terminal'] = not io.uncertain
        result['diagnostic_completed'] = (result['configured500_local'] and result['restore100_verified']
                                          and not result['final_error'] and not io.uncertain)
        result['passed'] = (result['native500_accepted'] and result['diagnostic_completed']
                            and not result['primary_error'] and not result['recovery_error'])
        try:
            io.finish(result)
        finally:
            io.close()
    return result


def ipv6_ready(links):
    # The peer is the original-key-verified r7-postboot observation, not a
    # guessed EUI64 or a new address to add. Reject incomplete DAD state.
    for link in links:
        for address in link.get('addr_info', []):
            if (address.get('local') == 'fe80::62:bcff:fe28:a101'
                    and address.get('prefixlen') == 64 and address.get('scope') == 'link'
                    and not any(address.get(k, False) for k in ('tentative', 'dadfailed'))
                    and not set(address.get('flags', [])).intersection(('tentative', 'dadfailed'))):
                return True
    return False


class Diagnostic(r6.Device):
    def __init__(self, directory):
        super().__init__()
        self.directory = Path(directory)
        self.started = self.touched = self.restoring = False
        self.manager_current = None
        self.config = None
        self.journal_errors = []

    def now(self):
        return time.monotonic()

    def pause(self, seconds):
        time.sleep(seconds)

    def check_window(self, config, cleanup=False):
        if cleanup:
            need(self.touched and self.restoring and self.lock is not None, 'only original touched/locked transaction may restore100')
        need(Path('/proc/sys/kernel/random/boot_id').read_text().strip() == config['identity']['boot_id']
             == Path(r6.GUARD).read_text().strip(), 'same explicit boot/guard')
        lease, mode = self.read_owned(WINDOW)
        lease = json.loads(lease)
        need(mode == 0o600 and lease['transaction'] == TX and lease['owner'] == 'charging'
             and lease['camera_released'] is True and lease['bluetooth_released'] is True
             and lease['exclusive'] is True and lease['token'] == config['window_token']
             and lease['host_trigger_nonce'] == config['host_trigger_nonce']
             and lease['boot_id'] == config['identity']['boot_id'], 'new coordinated window record')
        now = time.clock_gettime(time.CLOCK_BOOTTIME)
        if not cleanup:
            need(now < lease['expires_boottime_s'] <= now + 180, 'fresh bounded lease')

    def begin(self, config):
        self.config = config
        need(set(config) == {'transaction', 'guard', 'manifest_sha256', 'identity', 'window_token',
                             'host_trigger_nonce', 'host_ready', 'host_trigger_utc', 'worker_sha256'}, 'new diagnostic request schema')
        nonce = config['host_trigger_nonce']
        need(isinstance(nonce, str) and len(nonce) == 48 and all(x in '0123456789abcdef' for x in nonce), 'new host trigger nonce')
        need(config['transaction'] == TX and config['guard'] == r6.GUARD and config['manifest_sha256'] == r6.NEW, 'only actual r7 transaction')
        need(str(self.directory) == PREFIX + nonce and not self.directory.is_symlink(), 'unique dedicated directory')
        st = self.directory.stat()
        need(st.st_uid == 0 and stat.S_ISDIR(st.st_mode) and stat.S_IMODE(st.st_mode) == 0o700, 'private staged directory')
        need(not sys.flags.optimize and os.geteuid() == 0 and os.uname().release == r6.RELEASE, 'root/exact ABI/assertions')
        compat = Path('/sys/firmware/devicetree/base/compatible').read_bytes()
        serial = Path(r6.SOC_SERIAL).read_bytes()
        need(b'realme,samurai' in compat.split(b'\0') and serial.strip()
             and r6.sha(compat) == config['identity']['compatible_sha256']
             and r6.sha(serial) == config['identity']['serial_sha256'], 'fixed hardware identity')
        need(Path('/sys/bus/i2c/devices/0-005c/name').read_text().strip() == 'mp2650'
             and Path('/sys/bus/i2c/devices/0-005c/of_node').resolve().as_posix().endswith('/soc@0/geniqup@8c0000/i2c@884000/charger@5c'), 'real MP client/DT')
        need(r6.sha(self.read_owned(str(HERE / 'worker.py'))[0]) == config['worker_sha256'], 'reviewed worker hash')
        ready = config['host_ready']
        ready_time = datetime.fromisoformat(ready['armed_utc'])
        trigger_time = datetime.fromisoformat(config['host_trigger_utc'])
        need(ready_time.utcoffset() is not None and trigger_time.utcoffset() is not None
             and 0 <= (trigger_time-ready_time).total_seconds() <= 10, 'host ready/trigger timestamps on the same host clock')
        need(ready['armed'] is True and 1 <= ready['target_port'] <= 15 and ready['remaining_seconds_at_trigger'] >= 90
             and ready['decoder_sha256'] == '9fe2ffb2792bf5feb7113167056bec4466fced9dc1b591bffbcbe8373b5e7716'
             and ready['collector_sha256'] == '31c0f8e99f8ba4878b489f9b8dda34e5a688bb1e6b44415ce40a88c17fcfb6f5'
             and ready['host_worker_pid'] > 0 and isinstance(ready['capture_id'], str) and ready['capture_id'].endswith(nonce)
             and config['host_trigger_utc'], 'actual new host-ready gate; root must confirm live host worker')
        self.check_window(config)
        self.lock = os.open('/run/lock/samurai-charging.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        need(os.fstat(self.lock).st_uid == 0 and stat.S_ISREG(os.fstat(self.lock).st_mode)
             and not os.fstat(self.lock).st_mode & 0o022, 'original service lock')
        fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with (self.directory / 'execution-started-private.json').open('x') as stream:
            json.dump({'nonce': nonce, 'pid': os.getpid(), 'host_ready': ready, 'host_trigger_utc': config['host_trigger_utc']}, stream)
            stream.flush(); os.fsync(stream.fileno())
        self.out = self.directory
        self.started = True
        with (self.out / 'worker.pid').open('x') as stream:
            stream.write(str(os.getpid())); stream.flush(); os.fsync(stream.fileno())
        self.event('worker-anchor', host_trigger_utc=config['host_trigger_utc'], host_ready=ready)

    def event(self, event, **fields):
        if self.started:
            row = {'event': event, 'host_trigger_nonce': self.config['host_trigger_nonce'],
                   'realtime_ns': time.time_ns(), 'monotonic_ns': time.monotonic_ns(),
                   'boottime_ns': time.clock_gettime_ns(time.CLOCK_BOOTTIME), **fields}
            try:
                with (self.out / 'phases-private.jsonl').open('a') as stream:
                    stream.write(json.dumps(row) + '\n'); stream.flush(); os.fsync(stream.fileno())
            except OSError as error:
                self.journal_errors.append(detail(error))
                if not self.restoring:
                    raise  # no unjournaled forward500; cleanup100 must still run

    def preflight(self):
        need(r6.sha(self.read_owned(r6.MANIFEST)[0]) == r6.NEW, 'actual installed r7 manifest')
        self.manager_current = self.manager(r6.HASHES[r6.SERVICE])
        meta = self.verify(self.manager_current)
        self.notes_match(self.manager_current, meta)
        need(Path(GADGET, 'idVendor').read_text().strip() == '0x0525'
             and Path(GADGET, 'idProduct').read_text().strip() == '0xa4a1', 'same NCM gadget')
        return self.snapshot()

    def snapshot(self):
        row = self.observe(self.manager_current)
        source = self.manager_current['live'].PSY / 'samurai-usb-input'
        row['source'] = {n: (source / n).read_text().strip() for n in ['online', 'usb_type', 'current_max', 'input_current_limit']}
        row['udc'] = Path('/sys/class/udc', BINDING, 'state').read_text().strip()
        return row

    def environment(self):
        return {'camera': health.camera_state(), 'fault_count_snapshot': health.log_counts(),
                'manifest_sha256': r6.sha(self.read_owned(r6.MANIFEST)[0]),
                'service_sha256': r6.sha(self.read_owned(r6.SERVICE)[0])}

    def gadget_state(self):
        try:
            state = {'binding': Path(GADGET, 'UDC').read_text().strip(),
                     'power_ma': int(Path(GADGET, 'configs/c.1/MaxPower').read_text())}
            need(state['binding'] in ('', BINDING) and state['power_ma'] in (100, 500), 'unrecognized gadget state')
            return state
        except Exception as error:
            self.uncertain = True
            raise r6.MutationUncertain('cannot establish current sysfs state: ' + detail(error)) from error

    def write(self, field, value, stage, deadline):
        need(not self.uncertain and (self.restoring or self.now() < deadline), 'no mutation with unknown/expired forward phase')
        self.check_window(self.config, cleanup=self.restoring)
        if self.restoring:
            need(stage.startswith('100:') and not (field == 'MaxPower' and value != '100\n'), 'cleanup only restores100')
        paths = {'UDC': GADGET + '/UDC', 'MaxPower': GADGET + '/configs/c.1/MaxPower'}
        need((field == 'UDC' and value in ('\n', BINDING + '\n'))
             or (field == 'MaxPower' and value in ('100\n', '500\n')), 'only two volatile gadget targets')
        code = 'from pathlib import Path; import sys; Path(sys.argv[1]).write_text(sys.argv[2])'
        self.event('sysfs-write-before', stage=stage, field=field, value=value)
        self.touched = True
        self.child = subprocess.Popen([sys.executable, '-c', code, paths[field], value], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            stdout, stderr = self.child.communicate(timeout=3 if self.restoring else max(.001, min(3, deadline-self.now())))
        except subprocess.TimeoutExpired:
            self.uncertain = True
            self.event('sysfs-write-unknown', stage=stage, child_pid=self.child.pid)
            raise r6.MutationUncertain('sysfs child still pending at ' + stage)
        except BaseException:
            if self.child.poll() is None:
                self.uncertain = True
            raise
        self.event('sysfs-write-after', stage=stage, returncode=self.child.returncode, stderr=stderr)
        need(self.child.returncode == 0, 'completed sysfs write failed: ' + stage)

    def net_command(self, args, deadline):
        need(not self.uncertain and self.now() < deadline, 'network helper deadline/state')
        self.event('network-before', args=args)
        self.child = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            stdout, stderr = self.child.communicate(timeout=min(3, deadline-self.now()))
        except subprocess.TimeoutExpired:
            self.uncertain = True  # until the owned child is positively reaped
            try:
                self.child.kill()
            except OSError as error:
                self.event('network-kill-error', error=detail(error), child_pid=self.child.pid)
            try:
                self.child.communicate(timeout=1)
            except subprocess.TimeoutExpired:
                self.uncertain = True
                self.event('network-child-unknown', child_pid=self.child.pid)
                raise r6.MutationUncertain('network helper cannot be reaped')
            self.uncertain = False
            self.event('network-timeout-reaped', child_pid=self.child.pid)
            raise RuntimeError('network helper timed out and was reaped')
        self.event('network-after', returncode=self.child.returncode, stderr=stderr)
        need(self.child.returncode == 0, 'network helper failed: ' + repr(args))
        return stdout

    def network(self, deadline):
        # Existing observed Linux usb0 link-local peer. No host IPv4 privilege,
        # static address injection, interface/address fallback or sysctl write.
        need(Path(GADGET, 'functions/ncm.usb0/ifname').read_text().strip() == 'usb0', 'original NCM usb0')
        self.net_command(['ip', 'link', 'set', 'usb0', 'up'], deadline)
        ready_deadline = min(deadline, self.now() + 3)
        while self.now() < ready_deadline:
            links = json.loads(self.net_command(['ip', '-j', '-6', 'addr', 'show', 'dev', 'usb0'], ready_deadline))
            if ipv6_ready(links):
                return
            self.pause(min(.2, max(0, ready_deadline-self.now())))
        raise RuntimeError('observed original IPv6 peer not ready; no address/IPv4 fallback')

    def finish(self, result):
        if self.started:
            result['pending_child_pid'] = self.child.pid if self.uncertain and self.child else None
            self.event('result', result=result)
            result['journal_errors'] = self.journal_errors
            if self.journal_errors:
                result['passed'] = result['diagnostic_completed'] = False
            try:
                self.log('result.json', result)
            except OSError as error:
                self.journal_errors.append(detail(error))
                result['passed'] = result['diagnostic_completed'] = False


if __name__ == '__main__':
    need(len(sys.argv) == 3 and sys.argv[1] == '--worker', 'explicit --worker NEW_DIRECTORY required')
    os.umask(0o077)
    def terminate(signum, frame):
        raise RuntimeError('explicit worker termination signal')
    signal.signal(signal.SIGTERM, terminate)
    device = Diagnostic(sys.argv[2])
    config = json.loads(device.read_owned(str(device.directory / 'config-private.json'))[0])
    try:
        result = transaction(config, device)
    except BaseException:
        if device.uncertain:
            print(json.dumps({'terminal': False, 'mutating_state_unknown': True, 'fatal': 'logging/cleanup failed; retain worker and lock'}), flush=True)
            while True:
                time.sleep(1)
        raise
    print(json.dumps(result), flush=True)
    if device.uncertain:
        while True:
            time.sleep(1)  # retain the original service lock; no implicit retry
    raise SystemExit(0 if result['diagnostic_completed'] else 1)
