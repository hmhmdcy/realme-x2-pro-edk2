"""One RTC s2idle round with Bluetooth powered, unconnected, and nonconnectable."""
from pathlib import Path
import json
import os
import re
import subprocess
import sys
import time
import dbus

os.umask(0o077)
out = Path(sys.argv[1])
out.mkdir(mode=0o700)
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == Path('/var/lib/samurai/k204-runtime/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#183 ')
assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
assert Path('/sys/power/mem_sleep').read_text().strip() == '[s2idle]'
for p in Path('/proc/asound').glob('card*/pcm*/sub*/status'):
    assert p.read_text().strip() == 'closed'
for addr in ['1-0039', '1-003a']:
    assert 'powered=0 muted=1' in Path('/sys/bus/i2c/devices/' + addr + '/status').read_text()
(out / 'boot-id-private.txt').write_bytes(boot)
bus = dbus.SystemBus(private=True)
properties = dbus.Interface(bus.get_object('org.bluez', '/org/bluez/hci0'), 'org.freedesktop.DBus.Properties')
manager = dbus.Interface(bus.get_object('org.bluez', '/'), 'org.freedesktop.DBus.ObjectManager')


def bluetooth():
    p = properties.GetAll('org.bluez.Adapter1', timeout=8)
    assert p['Powered']
    assert all(not p[k] for k in ['Discovering', 'Pairable', 'Connectable', 'Discoverable'])
    objects = manager.GetManagedObjects(timeout=8)
    assert all(not v.get('org.bluez.Device1', {}).get('Connected', False) for v in objects.values())
    return {'powered': True, 'discovering': False, 'connected_devices': 0,
            'pairable': False, 'connectable': False, 'discoverable': False}


def stats():
    return {p.name: p.read_text().strip() for p in Path('/sys/power/suspend_stats').iterdir() if p.is_file()}


def irq():
    row = next(l for l in Path('/proc/interrupts').read_text().splitlines() if l.endswith('pm8xxx_rtc_alarm'))
    return sum(int(v) for v in row.split()[1:9])


def phase(value, **fields):
    with (out / 'phase-private.json').open('w') as f:
        json.dump(dict(phase=value, **fields), f, indent=2)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())


bt_before = bluetooth()
alarm = Path('/sys/class/rtc/rtc0/wakealarm')
assert not alarm.read_text().strip()
assert Path('/sys/class/rtc/rtc0/device/power/wakeup').read_text().strip() == 'enabled'
before_irq = irq()
target = int(Path('/sys/class/rtc/rtc0/since_epoch').read_text()) + 5
start = time.monotonic()
alarm.write_text(str(target))
try:
    while irq() == before_irq and time.monotonic() - start < 10:
        time.sleep(0.1)
    elapsed = time.monotonic() - start
    assert irq() - before_irq == 1 and 3 <= elapsed <= 7
    assert not alarm.read_text().strip()
    (out / 'rtc-preflight.json').write_text(json.dumps(dict(awake_rtc_irq_delta=1, elapsed_seconds=elapsed)) + '\n')
finally:
    if alarm.read_text().strip() == str(target):
        alarm.write_text('0')

trace = Path('/sys/kernel/tracing/instances/k204-bt-pm')
trace.mkdir()
names = ['suspend_resume', 'device_pm_callback_start', 'device_pm_callback_end',
         'wakeup_source_activate', 'wakeup_source_deactivate']
target = None
trace_saved = False
before = stats()
before_irq = irq()
before_log = subprocess.check_output(['dmesg'], text=True)
counter = Path('/sys/kernel/debug/bluetooth/hci0/ibs/pulse_rx_nuls')
before_counter = int(counter.read_text())
before_build_id = Path('/sys/module/hci_uart/notes/.note.gnu.build-id').read_bytes()
(out / 'dmesg-before-private.txt').write_text(before_log)
(out / 'stats-before-private.json').write_text(json.dumps(before, indent=2) + '\n')
try:
    (trace / 'buffer_size_kb').write_text('512')
    for name in names:
        (trace / 'events/power' / name / 'enable').write_text('1')
    (trace / 'tracing_on').write_text('1')
    phase('preflight-complete')
    time.sleep(2)
    bluetooth()
    assert not alarm.read_text().strip()
    target = int(Path('/sys/class/rtc/rtc0/since_epoch').read_text()) + 45
    alarm.write_text(str(target))
    assert alarm.read_text().strip() == str(target)
    phase('armed-before-suspend', target=target)
    os.sync()
    mono_start = time.monotonic()
    boot_start = time.clock_gettime(time.CLOCK_BOOTTIME)
    try:
        Path('/sys/power/state').write_text('mem')
        result = dict(returned=True, errno=0)
    except OSError as e:
        result = dict(returned=True, errno=e.errno, error=str(e))
    mono_elapsed = time.monotonic() - mono_start
    boot_elapsed = time.clock_gettime(time.CLOCK_BOOTTIME) - boot_start
    phase('returned-from-suspend', result=result)
    (trace / 'tracing_on').write_text('0')
    trace_text = (trace / 'trace').read_text()
    (out / 'pm-trace-private.txt').write_text(trace_text)
    trace_saved = True
    time.sleep(2)
    after = stats()
    after_log = subprocess.check_output(['dmesg'], text=True)
    (out / 'stats-after-private.json').write_text(json.dumps(after, indent=2) + '\n')
    (out / 'dmesg-after-private.txt').write_text(after_log)
    delta = {k: int(after[k]) - int(before[k]) for k in before
             if re.fullmatch(r'\d+', before[k]) and re.fullmatch(r'\d+', after[k])}
    assert after_log.startswith(before_log)
    extra = after_log[len(before_log):]
    faults = {key: extra.count(value) for key, value in {
        'warning': 'WARNING:', 'oops': 'Oops:', 'bluetooth_reassembly': 'Frame reassembly failed',
        'qca_setup': 'QCA Failed', 'asoc': 'ASoC error', 'irq_read': 'Failed to read IRQ status',
        'gpu': 'gpu fault:', 'dpu': 'Frame done timeout', 'ngd_resume': 'NGD resume failed',
        'tx_timeout': 'TX timed out', 'dma_prepare': 'unable to prepare channel'}.items()}
    bt_after = bluetooth()
    report = dict(stage=204, uart_rx_wake_enabled=Path('/sys/bus/platform/devices/c8c000.serial/power/wakeup').read_text().strip()=='enabled', slpi_offline_from_recorded_startup_failure=True, kernel_build=183, selected_mem_sleep='s2idle', sysfs_result=result,
        suspend_stats_delta=delta, alarm_delay_seconds=45, rtc_alarm_irq_delta=irq()-before_irq,
        monotonic_elapsed_seconds=mono_elapsed, boottime_elapsed_seconds=boot_elapsed,
        suspend_residency_seconds=boot_elapsed-mono_elapsed, fault_delta=faults,
        bluetooth_before=bt_before, bluetooth_after=bt_after,
        same_boot=boot == Path('/proc/sys/kernel/random/boot_id').read_bytes(),
        taint=int(Path('/proc/sys/kernel/tainted').read_text()),
        pulse_rx_nuls_before=before_counter, pulse_rx_nuls_after=int(counter.read_text()),
        same_loaded_module=before_build_id == Path('/sys/module/hci_uart/notes/.note.gnu.build-id').read_bytes(),
        no_reboot_or_driver_rebind=True, trace_isolated=True, post_resume_scan_pending=True)
    report['suspend_and_rtc_resume_passed'] = bool(result['errno'] == 0 and delta.get('success') == 1 and
        delta.get('fail') == 0 and report['suspend_residency_seconds'] >= 22 and
        report['rtc_alarm_irq_delta'] == 1 and report['same_boot'] and report['same_loaded_module'] and
        report['taint'] == 0 and not any(faults.values()))
    (out / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    phase('completed', passed=report['suspend_and_rtc_resume_passed'])
    print(json.dumps(report), flush=True)
    assert report['suspend_and_rtc_resume_passed']
finally:
    if target is not None and alarm.read_text().strip() == str(target):
        alarm.write_text('0')
    if trace.exists():
        (trace / 'tracing_on').write_text('0')
        if not trace_saved:
            (out / 'pm-trace-private.txt').write_text((trace / 'trace').read_text())
        for name in names:
            (trace / 'events/power' / name / 'enable').write_text('0')
        trace.rmdir()
    bus.close()
