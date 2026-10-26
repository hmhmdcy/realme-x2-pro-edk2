"""One bounded read-only physical USB/UI capture. Import is inert."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import math
import os
import re
import signal
import socket
import subprocess
import threading
import time
import uuid


def online(row): return row.get('source_online') == row.get('acok_online') == 1
def offline(row): return row.get('source_online') == row.get('acok_online') == 0


def timely(row, previous):
    a, b = row.get('t_start'), row.get('t_end')
    return (isinstance(a, (int, float)) and isinstance(b, (int, float))
            and math.isfinite(a) and math.isfinite(b) and 0 <= a <= b <= a + 2
            and (previous is None or previous < b and 0 <= a - previous <= 2.5))


def baseline_ok(row):
    s = row.get('telemetry', {})
    return (online(row) and all(s.get(k) == 1 for k in ['valid', 'online', 'protection_ok'])
            and s.get('shadow') == 0 and 0 <= s.get('age_ms', -1) <= 3000
            and all(s.get(k) == 0 for k in ['error', 'stop_error', 'latched', 'source_inhibit', 'fault']))


class Cycle:
    def __init__(self):
        self.baseline = self.off_count = self.on_count = 0
        self.ready_at = self.off_begin = self.on_begin = self.settle_at = None
        self.action_seen = self.off_confirmed = self.complete = False
        self.off_span = self.on_span = 0
        self.previous = None

    def feed(self, row):
        continuous = timely(row, self.previous)
        now = row['t_end']
        self.previous = now
        if not continuous:
            self.baseline = self.on_count = 0
            if not self.action_seen: self.ready_at = None
            if not self.off_confirmed:
                self.off_count = 0; self.off_begin = None; self.off_span = 0
            self.on_begin = self.settle_at = None; self.on_span = 0
            return 'sample_gap'
        if self.ready_at is None:
            self.baseline = self.baseline + 1 if baseline_ok(row) else 0
            if self.baseline >= 3: self.ready_at = now
            return 'ready' if self.ready_at is not None else 'baseline'
        if not self.off_confirmed:
            if not self.action_seen and not baseline_ok(row):
                if row.get('source_online') == 0 or row.get('acok_online') == 0:
                    self.action_seen = True
                else:
                    self.ready_at = None; self.baseline = 0
                    return 'baseline'
            if offline(row):
                self.action_seen = True
                if not self.off_count: self.off_begin = now
                self.off_count += 1; self.off_span = now - self.off_begin
                if self.off_count >= 3 and self.off_span >= 2: self.off_confirmed = True
                return 'offline' if self.off_confirmed else 'disconnecting'
            self.off_count = 0; self.off_begin = None
            return 'awaiting_complete_offline' if self.action_seen else 'ready'
        if online(row):
            if not self.on_count: self.on_begin = now
            self.on_count += 1; self.on_span = now - self.on_begin
            if self.on_count >= 3 and self.on_span >= 2 and self.settle_at is None: self.settle_at = now
            self.complete = self.settle_at is not None and now - self.settle_at >= 25
            return 'complete' if self.complete else 'settling' if self.settle_at is not None else 'reconnecting'
        self.on_count = 0; self.on_begin = self.settle_at = None; self.on_span = 0
        self.complete = False
        return 'offline_or_transition'

    def evidence(self):
        return {'ready_at': self.ready_at, 'offline_confirmed': self.off_confirmed,
                'offline_begin': self.off_begin, 'online_begin': self.on_begin,
                'offline_samples': self.off_count, 'online_samples': self.on_count,
                'offline_span': self.off_span, 'online_span': self.on_span,
                'settling_complete': self.complete}


def run(c, io, auditor):
    if not c.get('execute') or not c.get('window_confirmed'):
        raise ValueError('explicit execute and root-coordinated window required')
    if not re.fullmatch(r'charging-icon-[a-z0-9][a-z0-9-]{0,40}', c['transaction']):
        raise ValueError('new transaction name required')
    if not 50 <= c['max_seconds'] <= 600:
        raise ValueError('bounded deadline must be 50..600 seconds')
    io.create_new(c)
    start = io.clock_pair(); base = (start['m0'] + start['m1']) / 2
    cycle = Cycle(); rows = []; reason = 'deadline'; error = None; capture_errors = []
    monitor = {'started': False, 'errors': []}
    io.save('config.json', c); io.save('clock-start.json', start)
    try:
        io.check_identity(c)
        io.discover_battery()
        io.start_events(base)
        while io.boottime() - start['boot'] < c['max_seconds']:
            if not io.events_alive(): raise RuntimeError('UI monitor stopped unexpectedly')
            row = io.sample(base); rows.append(row); io.append_sample(row)
            phase = cycle.feed(row)
            remaining = max(0, c['max_seconds'] - (io.boottime() - start['boot']))
            io.status({'phase': phase, 'active': True, 'terminal': False,
                       'tick': len(rows), 't': row['t_end'], 'deadline_t': c['max_seconds'],
                       'remaining_boottime_seconds': remaining,
                       'ready_for_user_action': phase == 'ready' and not cycle.action_seen
                           and remaining >= 45,
                       'ready_at': cycle.ready_at})
            if remaining <= 0: break
            if cycle.complete: reason = 'cycle_complete'; break
            io.sleep(1)
    except BaseException as failure:
        reason = 'exception'; error = {'type': type(failure).__name__, 'message': str(failure)}
    finally:
        try: monitor = io.stop_events()
        except Exception as failure: monitor = {'started': False, 'errors': [str(failure)]}
        end = io.clock_pair()
        io.save('clock-end.json', end)
        try: io.check_identity(c); same = True
        except Exception as failure:
            same = False; capture_errors.append('final identity: ' + str(failure))
        try: events = io.event_data()
        except Exception as failure:
            events = {}; capture_errors.append('reading retained event logs: ' + str(failure))
        raw = {'schema': 'charging-icon-capture-v1', 'transaction': c['transaction'],
               'clock_start': start, 'clock_end': end, 'samples': rows, 'cycle': cycle.evidence(),
               'duration_seconds': (end['m0'] + end['m1']) / 2 - base, 'terminal_reason': reason,
               'elapsed_boottime_seconds': end['boot'] - start['boot'],
               'exception': error, 'monitor': monitor, 'identity_unchanged': same,
               'capture_errors': capture_errors, **events}
        io.save('capture-private.json', raw)
        try: result = auditor(raw)
        except Exception as failure:
            result = {'physical_cycle_passed': False, 'terminal_reason': reason,
                      'sample_count': len(rows), 'audit_error': str(failure)}
        io.save('result.json', result)
        io.status({'phase': 'terminal', 'active': False, 'terminal': True,
                   'tick': len(rows), 'ready_for_user_action': False, 'reason': reason,
                   'physical_cycle_passed': result['physical_cycle_passed']})
    return result


class UIEvents:
    """Original hotplug NETLINK/dbus-monitor path, with durable raw events."""
    def __init__(self, directory, base):
        self.base = base; self.errors = []; self.quit = threading.Event()
        self.raw = self.log = self.sock = self.process = self.thread = None
        try:
            self.raw = (directory / 'kernel-events-private.jsonl').open('x')
            self.log = (directory / 'upower-dbus-private.log').open('xb')
            self.sock = socket.socket(socket.AF_NETLINK, socket.SOCK_DGRAM, 15)
            self.sock.bind((os.getpid(), 1)); self.sock.settimeout(.2)
            self.process = subprocess.Popen(['dbus-monitor', '--system', "type='signal',interface='org.freedesktop.DBus.Properties',member='PropertiesChanged',path_namespace='/org/freedesktop/UPower'"], stdin=subprocess.DEVNULL, stdout=self.log, stderr=subprocess.STDOUT)
            self.thread = threading.Thread(target=self.receive, daemon=True); self.thread.start()
        except BaseException:
            self.stop(); raise

    def receive(self):
        try:
            while not self.quit.is_set():
                try: raw, _, flags, _ = self.sock.recvmsg(65536)
                except socket.timeout: continue
                if flags & socket.MSG_TRUNC: self.errors.append('truncated netlink packet')
                fields = dict(item.split('=', 1) for item in raw.decode(errors='replace').split(chr(0)) if '=' in item)
                if fields.get('SUBSYSTEM') == 'power_supply':
                    self.raw.write(json.dumps({'t': time.monotonic() - self.base, **fields}) + '\n'); self.raw.flush()
        except OSError as error:
            if not self.quit.is_set(): self.errors.append('netlink errno=' + str(error.errno))

    def alive(self): return self.thread.is_alive() and self.process.poll() is None

    def stop(self):
        def cleanup(label, action):
            try: return action()
            except Exception as failure: self.errors.append(label + ': ' + str(failure))
        self.quit.set()
        if self.thread and self.thread.ident is not None:
            cleanup('netlink join', lambda: self.thread.join(timeout=2))
            if self.thread.is_alive(): self.errors.append('netlink thread did not stop')
        if self.sock: cleanup('netlink close', self.sock.close)
        if self.process:
            if self.process.poll() is None: cleanup('dbus terminate', self.process.terminate)
            try: self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.errors.append('dbus-monitor required forced cleanup')
                cleanup('dbus kill', self.process.kill)
                cleanup('dbus final wait', lambda: self.process.wait(timeout=3))
            except Exception as failure: self.errors.append('dbus wait: ' + str(failure))
        if self.raw: cleanup('kernel log close', self.raw.close)
        if self.log: cleanup('dbus log close', self.log.close)
        return {'started': self.thread is not None and self.thread.ident is not None,
                'errors': self.errors, 'dbus_returncode': self.process.returncode if self.process else None}


class RealIO:
    def __init__(self): self.out = self.ui = None; self.battery = None
    def create_new(self, c):
        self.out = Path(c['output_root']) / c['transaction']; self.out.mkdir(mode=0o700)
    def discover_battery(self):
        parent = Path('/sys/bus/i2c/devices/5-0055').resolve()
        batteries = [p for p in Path('/sys/class/power_supply').iterdir() if (p / 'type').read_text().strip() == 'Battery' and p.resolve().parent.parent == parent]
        if len(batteries) != 1: raise ValueError('actual gauge Battery missing or ambiguous')
        self.battery = batteries[0]
    def monotonic(self): return time.monotonic()
    def boottime(self): return time.clock_gettime(time.CLOCK_BOOTTIME)
    def clock_pair(self):
        a = time.monotonic(); real = time.time(); b = time.monotonic()
        return {'m0': a, 'real': real, 'm1': b, 'boot': self.boottime()}
    def check_identity(self, c):
        if Path('/proc/sys/kernel/random/boot_id').read_text().strip() != c['boot_id'] or hashlib.sha256(Path('/usr/share/samurai-charging/manifest.json').read_bytes()).hexdigest() != c['manifest_sha256']:
            raise ValueError('boot or manifest differs from adopted identity')
        if Path('/sys/bus/i2c/devices/0-005c/driver').resolve().name != 'samurai-mp2650' or Path('/proc/sys/kernel/tainted').read_text().strip() != '0':
            raise ValueError('charger driver or taint differs')
    def save(self, name, data):
        path = self.out / name; temporary = path.with_suffix('.next')
        with temporary.open('w') as stream:
            json.dump(data, stream); stream.flush(); os.fsync(stream.fileno())
        temporary.replace(path)
    def append_sample(self, row):
        with (self.out / 'samples-private.jsonl').open('a') as stream:
            stream.write(json.dumps(row) + '\n'); stream.flush(); os.fsync(stream.fileno())
    def status(self, data):
        # PID + kernel start_ticks avoid treating stale status/PID reuse as live.
        stat = Path('/proc/self/stat').read_text(); start_ticks = int(stat[stat.rindex(')') + 2:].split()[19])
        self.save('status.json', {'pid': os.getpid(), 'start_ticks': start_ticks, 'realtime': time.time(), **data})
    def start_events(self, base): self.ui = UIEvents(self.out, base)
    def events_alive(self): return self.ui.alive()
    def stop_events(self): return self.ui.stop() if self.ui else {'started': False, 'errors': ['monitor not started']}
    def event_data(self):
        path = self.out / 'kernel-events-private.jsonl'
        log = self.out / 'upower-dbus-private.log'
        events = []; errors = []
        if path.exists():
            for index, line in enumerate(path.read_text().splitlines()):
                try: events.append(json.loads(line))
                except ValueError: errors.append('malformed retained kernel line ' + str(index))
        return {'battery_name': self.battery.name if self.battery else '',
                'kernel_events': events, 'event_read_errors': errors,
                'dbus_log': log.read_text(errors='replace') if log.exists() else ''}
    @staticmethod
    def read(path, numeric=False):
        try:
            text = Path(path).read_text().strip(); return int(text) if numeric else text
        except (OSError, ValueError) as error: return {'errno': getattr(error, 'errno', None), 'error': type(error).__name__}
    def sample(self, base):
        start = time.monotonic() - base; ps = Path('/sys/class/power_supply')
        text = self.read('/sys/bus/i2c/devices/0-005c/telemetry')
        try: telemetry = {k: int(v) for k, v in (field.split('=') for field in text.split())}
        except (ValueError, AttributeError): telemetry = {'parse_error': text}
        source = self.read(ps / 'samurai-usb-input/online', True)
        acok = self.read(ps / 'mp2650-input/online', True)
        battery = {'status': self.read(self.battery / 'status'), 'current_now_ua': self.read(self.battery / 'current_now', True)}
        fresh = (telemetry.get('valid') == telemetry.get('online') == 1 and source == acok == 1
                 and 0 <= telemetry.get('age_ms', -1) <= 3000)
        return {'t_start': start, 't_end': time.monotonic() - base, 'source_online': source,
                'acok_online': acok, 'telemetry': telemetry, 'flags_fresh': fresh, 'battery': battery}
    def sleep(self, seconds): time.sleep(seconds)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true'); parser.add_argument('--window-confirmed', action='store_true')
    for name in ['transaction', 'output-root', 'boot-id', 'manifest-sha256']: parser.add_argument('--' + name, required=True)
    parser.add_argument('--max-seconds', type=int, default=300)
    c = vars(parser.parse_args(argv))
    if not c['execute'] or not c['window_confirmed']: raise ValueError('explicit execution/window required')
    if str(uuid.UUID(c['boot_id'])) != c['boot_id'] or not re.fullmatch(r'[a-f0-9]{64}', c['manifest_sha256']) or not Path(c['output_root']).is_absolute(): raise ValueError('invalid adopted identity/output root')
    spec = importlib.util.spec_from_file_location('icon_audit', Path(__file__).with_name('audit.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    os.umask(0o077)
    def interrupt(signum, frame): raise InterruptedError('capture cancelled by signal ' + str(signum))
    signal.signal(signal.SIGTERM, interrupt); signal.signal(signal.SIGINT, interrupt)
    result = run(c, RealIO(), module.audit)
    print(json.dumps({key: result[key] for key in ['physical_cycle_passed', 'terminal_reason', 'sample_count']}))
    return 0 if result['physical_cycle_passed'] else 1


if __name__ == '__main__': raise SystemExit(main())
