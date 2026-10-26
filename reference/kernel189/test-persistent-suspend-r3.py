"""One RTC s2idle round with the default persistent SSC service left running."""
from pathlib import Path
import dbus
import json
import os
import re
import subprocess
import time

os.umask(0o077)
out = Path('/var/lib/samurai/k189-ssc-pm-r3')
assert not out.exists()
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == Path('/var/lib/samurai/k189r2-reboot-runtime/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#183 ')
assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
assert Path('/sys/power/mem_sleep').read_text().strip() == '[s2idle]'
assert Path('/sys/class/remoteproc/remoteproc0/state').read_text().strip() == 'running'
assert Path('/sys/devices/platform/sensor-power/state').read_text().strip() == 'vdd=1 vddio=1'
for path in Path('/proc/asound').glob('card*/pcm*/sub*/status'):
    assert path.read_text().strip() == 'closed'
for addr in ['1-0039', '1-003a']:
    assert 'powered=0 muted=1' in Path('/sys/bus/i2c/devices/' + addr + '/status').read_text()
for service in ['samurai-ssc', 'iio-sensor-proxy']:
    assert subprocess.run(['rc-service', service, 'status'], capture_output=True).returncode == 0
out.mkdir(mode=0o700)
(out / 'boot-id-private.txt').write_bytes(boot)
owner = Path('/run/samurai-ssc/state.json').read_bytes()
proxy_pid = subprocess.check_output(['pidof', 'iio-sensor-proxy']).strip()
bus = dbus.SystemBus(private=True)
bt = dbus.Interface(bus.get_object('org.bluez', '/org/bluez/hci0'), 'org.freedesktop.DBus.Properties')
adapter = bt.GetAll('org.bluez.Adapter1')
assert not adapter['Powered'] and not adapter['Discovering']
objects = dbus.Interface(bus.get_object('org.bluez', '/'), 'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
assert all(not v.get('org.bluez.Device1', {}).get('Connected', False) for v in objects.values())


def stats():
    return {p.name: p.read_text().strip() for p in Path('/sys/power/suspend_stats').iterdir() if p.is_file()}


def irq():
    row = next(l for l in Path('/proc/interrupts').read_text().splitlines() if l.endswith('pm8xxx_rtc_alarm'))
    return sum(int(v) for v in row.split()[1:9])


def phase(name, **fields):
    with (out / 'phase-private.json').open('w') as stream:
        json.dump(dict(phase=name, **fields), stream)
        stream.flush(); os.fsync(stream.fileno())


alarm = Path('/sys/class/rtc/rtc0/wakealarm')
assert not alarm.read_text().strip()
assert Path('/sys/class/rtc/rtc0/device/power/wakeup').read_text().strip() == 'enabled'
trace = Path('/sys/kernel/tracing/instances/k189-ssc-pm-r3')
names = ['suspend_resume', 'device_pm_callback_start', 'device_pm_callback_end',
         'wakeup_source_activate', 'wakeup_source_deactivate']
target = None
try:
    before_irq = irq()
    target = int(Path('/sys/class/rtc/rtc0/since_epoch').read_text()) + 5
    alarm.write_text(str(target))
    start = time.monotonic()
    while irq() == before_irq and time.monotonic() - start < 10:
        time.sleep(.1)
    elapsed = time.monotonic() - start
    assert irq() - before_irq == 1 and 3 <= elapsed <= 7
    assert not alarm.read_text().strip()
    (out / 'rtc-preflight.json').write_text(json.dumps(dict(irq_delta=1, elapsed_seconds=elapsed)) + '\n')
    assert not trace.exists()
    trace.mkdir()
    (trace / 'buffer_size_kb').write_text('1024')
    for name in names:
        (trace / 'events/power' / name / 'enable').write_text('1')
    (trace / 'tracing_on').write_text('1')
    before = stats(); before_irq = irq()
    (out / 'stats-before-private.json').write_text(json.dumps(before, indent=2) + '\n')
    (out / 'irq-before-private.txt').write_text(str(before_irq) + '\n')
    log_before = subprocess.check_output(['dmesg'], text=True)
    (out / 'dmesg-before-private.txt').write_text(log_before)
    target = int(Path('/sys/class/rtc/rtc0/since_epoch').read_text()) + 45
    alarm.write_text(str(target))
    assert alarm.read_text().strip() == str(target)
    phase('armed-before-suspend', writes_to_mem_requested=1, alarm_target=target)
    os.sync()
    mono = time.monotonic(); boottime = time.clock_gettime(time.CLOCK_BOOTTIME)
    try:
        Path('/sys/power/state').write_text('mem')
        error = 0
    except OSError as failure:
        error = failure.errno
    mono_elapsed = time.monotonic() - mono
    boot_elapsed = time.clock_gettime(time.CLOCK_BOOTTIME) - boottime
    phase('returned-from-suspend', errno=error, monotonic_elapsed_seconds=mono_elapsed,
          boottime_elapsed_seconds=boot_elapsed, suspend_residency_seconds=boot_elapsed-mono_elapsed)
    (trace / 'tracing_on').write_text('0')
    trace_text = (trace / 'trace').read_text()
    (out / 'pm-trace-private.txt').write_text(trace_text)
    trace_stats = {p.parent.name: p.read_text() for p in (trace / 'per_cpu').glob('cpu*/stats')}
    (out / 'trace-stats-private.json').write_text(json.dumps(trace_stats, indent=2) + '\n')
    after = stats()
    delta = {k: int(after[k]) - int(before[k]) for k in before
             if re.fullmatch(r'\d+', before[k]) and re.fullmatch(r'\d+', after[k])}
    callbacks = re.findall(r'device_pm_callback_end: (.*?) err=(-?\d+)', trace_text)
    overruns = [int(re.search(r'^overrun:\s*(\d+)', value, re.M)[1]) for value in trace_stats.values()]
    assert all(v == 0 for v in overruns)
    # Measure the real association delay instead of assuming two seconds suffices.
    wifi_start = time.monotonic(); wifi_delay = None
    while time.monotonic() - wifi_start < 35:
        link = subprocess.run(['iw', 'dev', 'wlan0', 'link'], capture_output=True).stdout
        if b'freq: 5180' in link:
            wifi_delay = time.monotonic() - wifi_start
            break
        time.sleep(.5)
    (out / 'wifi-after-private.txt').write_bytes(link)
    assert Path('/run/samurai-ssc/state.json').read_bytes() == owner
    assert subprocess.check_output(['pidof', 'iio-sensor-proxy']).strip() == proxy_pid
    subprocess.run(['samurai-ssc', 'status'], check=True, stdout=subprocess.DEVNULL)
    env = dict(os.environ, LD_LIBRARY_PATH='/usr/lib/samurai/ssc', LIBSSC_LIGHT_DATA_TYPE='wise_light')
    streams = {}
    for sensor, label in [('accelerometer','Accelerometer'), ('gyroscope','Gyroscope'),
                          ('magnetometer','Magnetometer'), ('light','Light')]:
        p = subprocess.run(['ssccli', '--debug', '--sensor', sensor, '--timeout','2'],
                           capture_output=True, env=env, timeout=20)
        raw = (p.stdout + p.stderr).decode(errors='replace')
        (out / (sensor + '-after-private.txt')).write_bytes(p.stdout + p.stderr)
        streams[sensor] = dict(exit=p.returncode, samples=raw.count(label + ' sensor measurement:'),
            disabled=(label + ' sensor disabled').lower() in raw.lower())
    props = dbus.Interface(bus.get_object('net.hadess.SensorProxy', '/net/hadess/SensorProxy'), 'org.freedesktop.DBus.Properties').GetAll('net.hadess.SensorProxy')
    assert all(props[k] for k in ['HasAccelerometer','HasAmbientLight','HasProximity'])
    log_after = subprocess.check_output(['dmesg'], text=True)
    (out / 'dmesg-after-private.txt').write_text(log_after)
    assert log_after.startswith(log_before)
    extra = log_after[len(log_before):]
    faults = {key:extra.count(value) for key,value in dict(warning='WARNING:',oops='Oops:',
        scm='Assign memory protection call failed',fastrpc='probe with driver qcom,fastrpc failed',
        slpi_start='2400000.remoteproc: start timed out',slpi_stop='2400000.remoteproc: timed out on wait',
        asoc='ASoC error',gpu='gpu fault:',bluetooth='Frame reassembly failed',
        irq='Failed to read IRQ status',ngd='NGD resume failed',dma='unable to prepare channel').items()}
    subprocess.run(['sha256sum','-c','/var/lib/samurai/k189-deploy/source-manifest-private.sha256'], check=True, stdout=subprocess.DEVNULL)
    report = dict(stage=189,kernel_build=183,sysfs_errno=error,suspend_stats_delta=delta,
        alarm_delay_seconds=45,rtc_alarm_irq_delta=irq()-before_irq,
        monotonic_elapsed_seconds=mono_elapsed,boottime_elapsed_seconds=boot_elapsed,
        suspend_residency_seconds=boot_elapsed-mono_elapsed,
        same_boot=boot==Path('/proc/sys/kernel/random/boot_id').read_bytes(),
        taint=int(Path('/proc/sys/kernel/tainted').read_text()),
        persistent_ssc_and_proxy_identity_preserved=True,callback_events=len(callbacks),
        callback_errors=sum(int(err)!=0 for _,err in callbacks),trace_overrun_total=sum(overruns),
        sensor_related_callback_events=sum(any(x in name for x in ['2400000.remoteproc','sensor-power','fastrpc']) for name,_ in callbacks),
        post_resume_streams=streams,fault_delta=faults,source_archive_unchanged=True,
        wifi_frequency_mhz=5180 if wifi_delay is not None else None,
        wifi_association_observation_delay_seconds=wifi_delay,
        no_reboot_or_driver_rebind=True,bluetooth_left_powered_off=True)
    report['suspend_and_sensor_resume_passed'] = bool(error==0 and delta.get('success')==1 and delta.get('fail')==0
        and report['suspend_residency_seconds']>=22 and report['rtc_alarm_irq_delta']==1
        and report['same_boot'] and report['taint']==0 and not any(faults.values())
        and callbacks and report['callback_errors']==0 and all(s['exit']==0 and s['samples']>0 and s['disabled'] for s in streams.values()))
    (out / 'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    phase('completed',passed=report['suspend_and_sensor_resume_passed'])
    print(json.dumps(report),flush=True)
    assert report['suspend_and_sensor_resume_passed']
finally:
    if target is not None and alarm.read_text().strip()==str(target):
        alarm.write_text('0')
    if trace.exists():
        (trace / 'tracing_on').write_text('0')
        if not (out / 'pm-trace-private.txt').exists():
            (out / 'pm-trace-private.txt').write_text((trace / 'trace').read_text())
        for name in names:
            (trace / 'events/power' / name / 'enable').write_text('0')
        trace.rmdir()
    bus.close()
