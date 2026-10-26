"""Bounded local observation of physical USB removal/reconnection.

Only writes its own private logs. Never controls charger, USB, services, PM,
modules or protection state. Runs in a separate session so USB SSH may vanish.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import math
import os
import re
import runpy
import socket
import subprocess
import threading
import time
import traceback


class UIEvents:
    """Receive genuine kernel events without polling the gauge status."""
    def __init__(self, directory, start):
        self.start, self.events = start, []
        self.quit = threading.Event()
        self.sock = socket.socket(socket.AF_NETLINK, socket.SOCK_DGRAM, 15)
        self.sock.bind((os.getpid(), 1)); self.sock.settimeout(.2)
        self.log = (directory / 'upower-dbus-private.log').open('xb')
        self.process = subprocess.Popen(['dbus-monitor', '--system',
            "type='signal',interface='org.freedesktop.DBus.Properties',member='PropertiesChanged',path_namespace='/org/freedesktop/UPower'"],
            stdin=subprocess.DEVNULL, stdout=self.log, stderr=subprocess.STDOUT)
        self.thread = threading.Thread(target=self.receive)
        self.thread.start()

    def receive(self):
        while not self.quit.is_set():
            try: raw = self.sock.recv(65536)
            except socket.timeout: continue
            fields = dict(item.split('=', 1) for item in raw.decode(errors='replace').split(chr(0)) if '=' in item)
            if fields.get('SUBSYSTEM') == 'power_supply':
                self.events.append({'t': time.monotonic() - self.start, **fields})

    def stop(self):
        self.quit.set(); self.thread.join(timeout=2); self.sock.close()
        assert not self.thread.is_alive()
        if self.process.poll() is None: self.process.terminate()
        self.process.wait(timeout=5); self.log.close()


def kind(row):
    value = row['source'].get('usb_type', '')
    match = re.search(r'\[([^]]+)\]', value) if isinstance(value, str) else None
    return match[1] if match else 'Unknown'


def detached(row):
    sample, regs = row.get('telemetry', {}), row.get('registers', {})
    return bool(sample.get('valid') == 1 and sample.get('online') == 0
                and sample.get('desired_enable') == 0
                and not any(sample.get(k, -1) for k in ['error', 'stop_error', 'latched', 'source_inhibit'])
                and row['source'].get('online') == 0
                and regs.get('08', 0) & 0x18 == 8
                and not regs.get('13', 2) & 2)


def healthy(row):
    s, r, source = row.get('telemetry', {}), row.get('registers', {}), row['source']
    if not (s.get('valid') == s.get('online') == s.get('protection_ok') == s.get('desired_enable') == 1
            and s.get('shadow') == 0 and 0 <= s.get('age_ms', -1) <= 3000
            and not any(s.get(k, -1) for k in ['error', 'stop_error', 'latched', 'source_inhibit', 'fault'])
            and source.get('online') == 1 and row.get('udc_state') == 'configured'
            and r.get('08', 0) & 0x18 == 0x10):
        return False
    budget = s.get('budget_ua', -1)
    first = (r.get('00', 0) & 0x7f) * 50000
    second = (r.get('0f', 0) & 0x7f) * 50000
    if not (budget == source.get('current_max') and 50000 <= first == second <= min(900000, budget)
            and (r.get('02', 0) & 0x7f) * 50000 == 250000
            and 7425000 <= 2 * (3712500 + ((r.get('04', 0) & 0x7e) >> 1) * 12500) <= 8725000):
        return False
    if kind(row) == 'SDP':
        native = source.get('input_current_limit')
        return isinstance(native, int) and 50000 <= native <= 500000 and budget == native and first <= native
    return kind(row) in ['CDP', 'DCP', 'C']


def audit(data):
    rows = data['samples']
    off = [row for row in rows if detached(row)]
    tail = []
    for row in reversed(rows):
        if not healthy(row):
            break
        tail.append(row)
    tail.reverse()
    before = [row for row in rows if healthy(row) and (not off or row['t'] < off[0]['t'])]
    off_span = off[-1]['t'] - off[0]['t'] if off else 0
    tail_span = tail[-1]['t'] - tail[0]['t'] if tail else 0
    new_session = bool(off and tail and off[-1]['telemetry']['session_seconds'] == 0
                       and 0 <= tail[0]['telemetry']['session_seconds'] <= math.ceil(tail[0]['t'] - off[-1]['t']) + 2)
    after_kind = kind(tail[-1]) if tail else 'Unknown'
    source_limits = bool(tail and all(healthy(row) for row in tail))
    sdp = bool(source_limits and after_kind == 'SDP' and all(kind(row) == 'SDP' for row in tail))
    checks = {'same_boot': data['same_boot'], 'taint_zero': data['taint_before'] == data['taint_after'] == 0,
              'no_new_faults': not any(data['fault_delta'].values()),
              'camera_and_four_services_unchanged': data['camera_and_four_services_unchanged'],
              'healthy_baseline': len(before) >= 3, 'physical_detach_and_hardware_inhibit': len(off) >= 3 and off_span >= 2,
              'fresh_session_after_detach': new_session,
              'automatic_fresh_recovery': len(tail) >= 10 and tail_span >= 9,
              'recovered_input_within_real_allowance': source_limits,
              'installed_manifest_unchanged': data['manifest_before'] == data['manifest_after']}
    last = tail[-1] if tail else None
    return {'passed': all(checks.values()), 'checks': checks, 'samples': len(rows),
            'duration_seconds': data['duration_seconds'], 'detached_samples': len(off),
            'detached_span_seconds': off_span, 'recovered_samples': len(tail),
            'recovered_span_seconds': tail_span, 'source_before': kind(before[0]) if before else 'Unknown',
            'source_after': after_kind, 'physical_sdp_budget_accepted': sdp and all(checks.values()),
            'native_allowance_after_ua': last['source']['input_current_limit'] if last else None,
            'actual_input_after_ua': (last['registers']['00'] & 0x7f) * 50000 if last else None,
            'source_allowance_after_ua': last['telemetry']['budget_ua'] if last else None,
            'taint': data['taint_after'], 'configuration_or_service_writes': 0,
            'manifest_sha256': data['manifest_after'], 'terminal_reason': data['terminal_reason']}


def worker(directory):
    os.umask(0o077)
    directory = Path(directory)
    config = json.loads((directory / 'config.json').read_text())
    assert os.geteuid() == 0
    for name, digest in config['files'].items():
        assert hashlib.sha256((directory / name).read_bytes()).hexdigest() == digest
    boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
    assert boot == Path(config['guard']).read_bytes()
    spec = importlib.util.spec_from_file_location('charging_health', directory / 'health-helper.py')
    health = importlib.util.module_from_spec(spec); spec.loader.exec_module(health)
    service = runpy.run_path('/usr/sbin/samurai-charging')
    meta = service['verify']()
    for name, entry in meta['modules'].items():
        service['loaded_matches'](Path(entry['target']), name.replace('-', '_'))
    live = service['live']
    assert (live.CLIENT / 'driver').resolve().name == 'samurai-mp2650'
    manifest = Path('/usr/share/samurai-charging/manifest.json')
    manifest_before = hashlib.sha256(manifest.read_bytes()).hexdigest()
    assert manifest_before == config['manifest_sha256']
    before_camera, before_log = health.camera_state(), health.log_counts()
    taint_before = int(Path('/proc/sys/kernel/tainted').read_text()); assert taint_before == 0

    def status(phase, **values):
        temporary = directory / 'status-next.json'
        temporary.write_text(json.dumps({'phase': phase, 'pid': os.getpid(), **values}))
        temporary.replace(directory / 'status.json')

    start = time.monotonic(); seen_detach = False; stable_since = None
    start_realtime = time.time()
    ui = UIEvents(directory, start) if config.get('monitor_ui') else None
    baseline_count = 0; reason = 'deadline'; rows = []
    status('baseline')
    try:
        with (directory / 'samples-private.jsonl').open('x') as log:
            while time.monotonic() - start <= config['max_seconds']:
                row = {'t': time.monotonic() - start, 'source': {}}
                text = health.read(live.CLIENT / 'telemetry')
                try: row['telemetry'] = health.parse_telemetry(text)
                except (ValueError, TypeError, AttributeError): row['telemetry_error'] = text
                source = live.PSY / 'samurai-usb-input'
                for name in ['online', 'current_max', 'input_current_limit', 'usb_type']:
                    value = health.read(source / name)
                    row['source'][name] = int(value) if isinstance(value, str) and name != 'usb_type' else value
                try: row['registers'] = live.registers()
                except OSError as error: row['register_error'] = error.errno
                row['udc_state'] = health.read(next(Path('/sys/class/udc').iterdir()) / 'state')
                rows.append(row); log.write(json.dumps(row) + '\n'); log.flush(); os.fsync(log.fileno())
                if not seen_detach:
                    baseline_count = baseline_count + 1 if healthy(row) else 0
                    if baseline_count >= 3: status('armed', samples=len(rows), source=kind(row))
                if row['source'].get('online') == 0:
                    seen_detach = True; stable_since = None; status('detached', samples=len(rows))
                elif seen_detach:
                    if healthy(row):
                        if stable_since is None: stable_since = row['t']
                        status('reconnecting', samples=len(rows), source=kind(row))
                        if row['t'] - stable_since >= 15:
                            reason = 'reconnected_stable'; break
                    else: stable_since = None
                if (directory / 'cancel').exists(): reason = 'cancelled'; break
                time.sleep(1)
    finally:
        if ui is not None: ui.stop()
    final_log = health.log_counts()
    data = {'samples': rows, 'duration_seconds': time.monotonic() - start, 'terminal_reason': reason,
            'same_boot': boot == Path('/proc/sys/kernel/random/boot_id').read_bytes(),
            'taint_before': taint_before, 'taint_after': int(Path('/proc/sys/kernel/tainted').read_text()),
            'fault_delta': {key: final_log[key] - before_log[key] for key in before_log},
            'camera_and_four_services_unchanged': before_camera == health.camera_state(),
            'manifest_before': manifest_before, 'manifest_after': hashlib.sha256(manifest.read_bytes()).hexdigest()}
    if ui is not None:
        data.update(kernel_events=ui.events, upower_dbus_log=(directory / 'upower-dbus-private.log').read_text(), start_realtime=start_realtime)
    (directory / 'capture-private.json').write_text(json.dumps(data))
    result = audit(data)
    (directory / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    status('terminal', passed=result['passed'], reason=reason)
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    import sys
    path = Path(sys.argv[1])
    try:
        worker(path)
    except BaseException:
        (path / 'failure-private.txt').write_text(traceback.format_exc())
        (path / 'status.json').write_text(json.dumps({'phase': 'failed', 'pid': os.getpid()}))
        raise
