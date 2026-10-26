#!/usr/bin/python3
"""Bounded read-only observation of the installed ordinary-charging stack.

No register/charge-property writes, control actions, service changes, alarms or
suspend requests. Run in a coordinated window; this is evidence, not a safety
controller or a substitute for physical unplug/SDP/temperature acceptance.
"""
from pathlib import Path
import errno
import hashlib
import json
import os
import runpy
import subprocess
import sys
import time

CLIENT = Path('/sys/bus/i2c/devices/0-005c')
PSY = Path('/sys/class/power_supply')
REQUIRED = {'shadow', 'valid', 'online', 'protection_ok', 'budget_ua', 'temp_decic',
            'pack_uv', 'cell1_uv', 'cell2_uv', 'fault', 'session_seconds',
            'desired_enable', 'error', 'stop_error', 'latched', 'source_inhibit', 'age_ms'}
FAULTS = ['WARNING:', 'Oops:', 'refcount_t: underflow', 'gpu fault:', 'NGD resume failed']


def parse_telemetry(text):
    values = {}
    for item in text.split():
        key, value = item.split('=')
        if key in values:
            raise ValueError('duplicate telemetry field: ' + key)
        values[key] = int(value)
    if not REQUIRED <= values.keys():
        raise ValueError('missing telemetry fields')
    return values


def classify(sample):
    """Describe cached driver data without authorizing any charging action."""
    if not REQUIRED <= sample.keys():
        return 'unavailable'
    if sample['shadow']:
        return 'shadow'
    if any(sample[k] for k in ['fault', 'stop_error', 'latched']):
        return 'fault'
    if sample['source_inhibit']:
        return 'waiting_source'
    if sample['error']:
        return 'fault'
    if not sample['valid'] or not sample['protection_ok']:
        return 'unavailable'
    if not sample['online']:
        return 'detached'
    if sample['age_ms'] < 0 or sample['age_ms'] > 3000:
        return 'stale'
    return 'managed' if sample['desired_enable'] else 'inhibited'


def read(path):
    try:
        return path.read_text().strip()
    except OSError as error:
        return {'errno': error.errno}


def camera_state():
    services = []
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        comm = read(proc / 'comm')
        if comm in ['phoc', 'phosh', 'pipewire', 'wireplumber']:
            try:
                services.append([comm, int(proc.name), proc.stat().st_uid])
            except FileNotFoundError:
                pass
    return {'pm': {name: read(Path('/sys/bus/platform/devices') / name / 'power/runtime_status')
                   for name in ['ac10000.icp', 'acb3000.camss', 'ac4a000.cci', 'ac4b000.cci']},
            'm2m': read(Path('/sys/bus/platform/devices/ac10000.icp/m2m_status')),
            'services': sorted(services)}


def log_counts():
    log = subprocess.check_output(['dmesg'], text=True)
    return {key: log.count(key) for key in FAULTS}


def native_allowance():
    value = read(PSY / 'samurai-usb-input/input_current_limit')
    return int(value) if isinstance(value, str) else value


def find_battery(supplies=PSY):
    # The real gauge registers as bq28z610-0. Identify its Battery class,
    # rather than guessing a bq27* filename; ambiguity is not silently hidden.
    candidates = [path for path in supplies.iterdir() if read(path / 'type') == 'Battery']
    return candidates[0] if len(candidates) == 1 else None


def observe(duration, interval):
    assert os.geteuid() == 0
    assert 0 <= duration <= 600 and 1 <= interval <= 60
    # Importing definitions does not execute the service's __main__ command.
    service = runpy.run_path('/usr/sbin/samurai-charging')
    meta = service['verify']()
    for name, entry in meta['modules'].items():
        service['loaded_matches'](Path(entry['target']), name.replace('-', '_'))
    assert (CLIENT / 'driver').resolve().name == 'samurai-mp2650'
    manifest_hash = hashlib.sha256(Path('/usr/share/samurai-charging/manifest.json').read_bytes()).hexdigest()
    before_boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
    before_camera, before_log = camera_state(), log_counts()
    before_native = native_allowance()
    before_taint = int(Path('/proc/sys/kernel/tainted').read_text())
    charger = PSY / 'mp2650-input'
    limits = {name: int((charger / name).read_text()) for name in
              ['input_current_limit', 'constant_charge_current', 'constant_charge_voltage']}
    battery = find_battery()
    rows = []
    start = time.monotonic()
    deadline = start + duration
    while True:
        row = {'elapsed_seconds': time.monotonic() - start,
               'boottime_seconds': time.clock_gettime(time.CLOCK_BOOTTIME)}
        value = read(CLIENT / 'telemetry')
        try:
            row['telemetry'] = parse_telemetry(value)
            row['state'] = classify(row['telemetry'])
        except (ValueError, TypeError, AttributeError) as error:
            row.update(state='unavailable', telemetry_error=str(error), telemetry_read=value)
        row['charger_status'] = read(charger / 'status')
        if battery is not None:
            row['battery'] = {name: read(battery / name) for name in ['capacity', 'current_now', 'temp', 'voltage_now']}
        rows.append(row)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(interval, remaining))
    final_limits = {name: int((charger / name).read_text()) for name in limits}
    final_log = log_counts()
    return {'scope': 'Read-only bounded observation; no control or PM transitions',
            'release': os.uname().release, 'manifest_sha256': manifest_hash,
            'installed_files_and_loaded_notes_verified': True,
            'duration_seconds': time.monotonic() - start,
            'same_boot': before_boot == Path('/proc/sys/kernel/random/boot_id').read_bytes(),
            'taint_before': before_taint, 'taint_after': int(Path('/proc/sys/kernel/tainted').read_text()),
            'limits_before': limits, 'limits_after': final_limits,
            'native_allowance_before': before_native, 'native_allowance_after': native_allowance(),
            'fault_delta': {key: final_log[key] - before_log[key] for key in FAULTS},
            'camera_and_four_services_unchanged': before_camera == camera_state(),
            'samples': rows}


def audit(data):
    """Keep expected idle/full/source states distinct; never infer net current."""
    rows = data['samples']
    counts = {state: sum(row['state'] == state for row in rows) for state in
              ['managed', 'inhibited', 'detached', 'waiting_source', 'fault', 'stale', 'unavailable', 'shadow']}
    regressions = 0
    previous = None
    for row in rows:
        sample = row.get('telemetry')
        if sample is None:
            previous = None
            continue
        if not sample['online'] and not sample['source_inhibit'] and sample['valid']:
            previous = None  # Only an observed, valid detach starts a new session.
            continue
        if sample['online'] and sample['valid']:
            if previous is not None and sample['session_seconds'] < previous:
                regressions += 1
            previous = sample['session_seconds']
    # This acceptance is specifically a continuously connected managed window.
    # Other observed states remain in the report and are not promoted to pass.
    passed = bool(rows and counts['managed'] == len(rows) and not regressions
                  and data['same_boot'] and data['taint_before'] == data['taint_after'] == 0
                  and data['limits_before'] == data['limits_after']
                  and data['native_allowance_before'] == data['native_allowance_after']
                  and isinstance(data['native_allowance_after'], int)
                  and not any(data['fault_delta'].values())
                  and data['camera_and_four_services_unchanged'])
    return {'passed': passed, 'scope': 'Continuously connected ordinary-charge observation only',
            'sample_count': len(rows), 'duration_seconds': data['duration_seconds'],
            'state_counts': counts, 'session_counter_regressions': regressions,
            'manifest_sha256': data['manifest_sha256'], 'same_boot': data['same_boot'],
            'taint': data['taint_after'], 'fault_delta': data['fault_delta'],
            'limits_unchanged': data['limits_before'] == data['limits_after'],
            'native_allowance_after': data['native_allowance_after'],
            'camera_and_four_services_unchanged': data['camera_and_four_services_unchanged'],
            'physical_sdp_unplug_temperature_or_long_endurance_accepted': False,
            'cross_reboot_session_persistence_accepted': False}


if __name__ == '__main__':
    seconds = float(sys.argv[1]) if len(sys.argv) > 1 else 120
    interval = float(sys.argv[2]) if len(sys.argv) > 2 else 10
    print(json.dumps(observe(seconds, interval)), flush=True)
