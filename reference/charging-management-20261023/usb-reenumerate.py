"""One bounded gadget re-enumeration, with native budget acceptance and rollback.

This never sets the power-supply budget directly. Only the USB host's normal
SET_CONFIGURATION callback can authorize the higher SDP input limit.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import runpy
import subprocess
import sys
import time
import traceback


def worker(directory):
    os.umask(0o077)
    directory = Path(directory)
    config = json.loads((directory / 'config.json').read_text())
    assert os.geteuid() == 0
    boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
    assert boot == Path(config['guard']).read_bytes()
    manifest = Path('/usr/share/samurai-charging/manifest.json')
    assert hashlib.sha256(manifest.read_bytes()).hexdigest() == config['manifest_sha256']
    service = runpy.run_path('/usr/sbin/samurai-charging')
    meta = service['verify']()
    for name, entry in meta['modules'].items():
        service['loaded_matches'](Path(entry['target']), name.replace('-', '_'))
    live = service['live']
    spec = importlib.util.spec_from_file_location('health', directory / 'health.py')
    health = importlib.util.module_from_spec(spec); spec.loader.exec_module(health)
    spec = importlib.util.spec_from_file_location('events', directory / 'events.py')
    events = importlib.util.module_from_spec(spec); spec.loader.exec_module(events)
    g = Path('/sys/kernel/config/usb_gadget/samurai')
    udc, power = g / 'UDC', g / 'configs/c.1/MaxPower'
    binding = udc.read_text().strip()
    assert binding == 'a600000.usb' and int(power.read_text()) == 100
    assert (g / 'idVendor').read_text().strip() == '0x0525'
    assert (g / 'idProduct').read_text().strip() == '0xa4a1'
    source = Path('/sys/class/power_supply/samurai-usb-input')
    assert int((source / 'online').read_text()) == 1
    assert int((source / 'input_current_limit').read_text()) == 100000
    assert '[SDP]' in (source / 'usb_type').read_text()
    assert int(Path('/proc/sys/kernel/tainted').read_text()) == 0
    before_camera, before_log = health.camera_state(), health.log_counts()
    before_limits = {n: (live.PSY / 'mp2650-input' / n).read_text() for n in
                     ['constant_charge_current', 'constant_charge_voltage']}
    for path in [directory.parent / 'usb-hotplug-r4', directory.parent / 'usb-power500']:
        pid = int((path / 'worker.pid').read_text())
        cmdline = Path('/proc') / str(pid) / 'cmdline'
        assert not cmdline.exists() or str(path / 'worker.py').encode() not in cmdline.read_bytes().split(bytes([0]))

    def network():
        interface = (g / 'functions/ncm.usb0/ifname').read_text().strip()
        assert interface == 'usb0'
        subprocess.run(['ip', 'link', 'set', interface, 'up'], check=True, timeout=5)
        addresses = json.loads(subprocess.check_output(['ip', '-j', '-4', 'addr', 'show', 'dev', interface], text=True))
        if not any(a.get('local') == '169.254.42.1' and a.get('prefixlen') == 16
                   for link in addresses for a in link['addr_info']):
            subprocess.run(['ip', 'addr', 'add', '169.254.42.1/16', 'dev', interface], check=True, timeout=5)

    def configure(ma):
        udc.write_text('\n')
        assert not udc.read_text().strip()
        power.write_text(str(ma) + '\n')
        assert int(power.read_text()) == ma
        time.sleep(2)
        udc.write_text(binding + '\n')
        assert udc.read_text().strip() == binding
        network()

    start = time.monotonic(); realtime = time.time()
    ui = events.UIEvents(directory, start)
    rows, failure, recovery = [], None, None
    accepted = False
    try:
        configure(500)
        stable = None
        with (directory / 'samples-private.jsonl').open('x') as log:
            while time.monotonic() - start < 60:
                row = {'t': time.monotonic() - start,
                       'source': {n: health.read(source / n) for n in ['online', 'usb_type', 'current_max', 'input_current_limit']},
                       'telemetry': health.parse_telemetry(health.read(live.CLIENT / 'telemetry')),
                       'registers': live.registers(),
                       'udc': health.read(Path('/sys/class/udc') / binding / 'state')}
                battery = health.find_battery()
                row['battery'] = {n: health.read(battery / n) for n in ['status', 'current_now', 'capacity']}
                rows.append(row); log.write(json.dumps(row) + '\n'); log.flush()
                s, r = row['telemetry'], row['registers']
                good = (row['udc'] == 'configured' and row['source']['online'] == '1'
                        and row['source']['input_current_limit'] == row['source']['current_max'] == '500000'
                        and s['valid'] == s['protection_ok'] == s['desired_enable'] == 1
                        and s['budget_ua'] == 500000 and not any(s[k] for k in
                            ['error', 'stop_error', 'latched', 'source_inhibit', 'fault'])
                        and (r['00'] & 0x7f) == (r['0f'] & 0x7f) == 10)
                if good:
                    if stable is None: stable = row['t']
                    if row['t'] - stable >= 12:
                        accepted = True; break
                else: stable = None
                time.sleep(.5)
        if not accepted: raise RuntimeError('Host did not authorize a stable native 500mA configuration')
    except BaseException:
        failure = traceback.format_exc()
        try: configure(100)
        except BaseException: recovery = traceback.format_exc()
    finally:
        # Always leave a bound gadget, including an exception during descriptor update.
        if not udc.read_text().strip():
            try:
                power.write_text('100\n'); udc.write_text(binding + '\n'); network()
            except BaseException: recovery = traceback.format_exc()
        ui.stop()
    final_log = health.log_counts()
    camera_same = before_camera == health.camera_state()
    limits_same = before_limits == {n: (live.PSY / 'mp2650-input' / n).read_text() for n in before_limits}
    fault_delta = {k: final_log[k] - before_log[k] for k in before_log}
    upower = subprocess.check_output(['upower', '-d'], text=True, timeout=10)
    result = {'passed': accepted and not failure and not recovery and camera_same and limits_same
                       and not any(fault_delta.values()) and int(Path('/proc/sys/kernel/tainted').read_text()) == 0,
              'terminal': True, 'native_host_budget_accepted': accepted,
              'MaxPower_ma': int(power.read_text()),
              'native_allowance_ua': int((source / 'input_current_limit').read_text()),
              'same_boot': boot == Path('/proc/sys/kernel/random/boot_id').read_bytes(),
              'camera_and_four_services_unchanged': camera_same, 'charge_and_voltage_caps_unchanged': limits_same,
              'taint': int(Path('/proc/sys/kernel/tainted').read_text()), 'fault_delta': fault_delta,
              'duration_seconds': time.monotonic() - start, 'samples': len(rows),
              'physical_unplug_test': False, 'budget_property_writes': 0,
              'manifest_sha256': hashlib.sha256(manifest.read_bytes()).hexdigest()}
    (directory / 'capture-private.json').write_text(json.dumps({'result': result, 'samples': rows,
        'start_realtime': realtime, 'kernel_events': ui.events,
        'upower_dbus_log': (directory / 'upower-dbus-private.log').read_text(), 'upower_after': upower,
        'failure': failure, 'recovery': recovery}))
    (directory / 'result.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    worker(sys.argv[1])
