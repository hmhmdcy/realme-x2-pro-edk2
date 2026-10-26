from pathlib import Path
import json, os, re, subprocess, time

os.umask(0o077)
out = Path('/var/lib/samurai/k177-suspend-idle')
out.mkdir(mode=0o700)
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert os.uname().version.startswith('#176 ')
assert boot == Path('/var/lib/samurai/k176-runtime/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
assert json.loads(Path('/var/lib/samurai/k177-rtc/validation.json').read_text())['awake_rtc_alarm_irq_delta'] == 1
assert Path('/sys/power/mem_sleep').read_text().strip() == '[s2idle]'
for p in ['pcm0p', 'pcm1c']:
    assert Path('/proc/asound/card0/' + p + '/sub0/status').read_text().strip() == 'closed'
for a in ['1-0039', '1-003a']:
    assert 'powered=0 muted=1' in Path('/sys/bus/i2c/devices/' + a + '/status').read_text()
(out / 'boot-id-private.txt').write_bytes(boot)
alarm = Path('/sys/class/rtc/rtc0/wakealarm')
assert not alarm.read_text().strip(), 'Existing RTC alarm must not be replaced'
assert Path('/sys/class/rtc/rtc0/device/power/wakeup').read_text().strip() == 'enabled'

def phase(value, **fields):
    with (out / 'phase-private.json').open('w') as f:
        json.dump(dict(phase=value, **fields), f, indent=2)
        f.write('\n'); f.flush(); os.fsync(f.fileno())

def stats():
    return {p.name: p.read_text().strip() for p in Path('/sys/power/suspend_stats').iterdir() if p.is_file()}

def irq_count():
    row = next(l for l in Path('/proc/interrupts').read_text().splitlines() if l.endswith('pm8xxx_rtc_alarm'))
    return sum(int(v) for v in row.split()[1:9])

def log():
    return subprocess.check_output(['dmesg'], text=True)

trace = Path('/sys/kernel/tracing/instances/k177-pm')
trace.mkdir()
trace_saved = False
target = None
before = stats(); before_log = log(); before_irq = irq_count()
(out / 'stats-before-private.json').write_text(json.dumps(before, indent=2) + '\n')
(out / 'dmesg-before-private.txt').write_text(before_log)
(out / 'wakeup-before-private.txt').write_text(Path('/sys/kernel/debug/wakeup_sources').read_text())
try:
    (trace / 'buffer_size_kb').write_text('512')
    for name in ['suspend_resume', 'device_pm_callback_start', 'device_pm_callback_end',
                 'wakeup_source_activate', 'wakeup_source_deactivate']:
        (trace / 'events/power' / name / 'enable').write_text('1')
    (trace / 'tracing_on').write_text('1')
    phase('preflight-complete')
    time.sleep(3)
    assert boot == Path('/proc/sys/kernel/random/boot_id').read_bytes()
    assert not alarm.read_text().strip()
    target = int(Path('/sys/class/rtc/rtc0/since_epoch').read_text()) + 15
    alarm.write_text(str(target))
    assert alarm.read_text().strip() == str(target)
    phase('armed-before-suspend', alarm=target, stats=before)
    os.sync()
    monotonic_start = time.monotonic()
    boot_start = time.clock_gettime(time.CLOCK_BOOTTIME)
    result = None
    try:
        Path('/sys/power/state').write_text('mem')
        result = dict(returned=True, errno=0)
    except OSError as e:
        result = dict(returned=True, errno=e.errno, error=str(e))
    monotonic_elapsed = time.monotonic() - monotonic_start
    boot_elapsed = time.clock_gettime(time.CLOCK_BOOTTIME) - boot_start
    phase('returned-from-suspend', result=result, monotonic_elapsed=monotonic_elapsed,
          boottime_elapsed=boot_elapsed)
    (trace / 'tracing_on').write_text('0')
    trace_text = (trace / 'trace').read_text()
    (out / 'pm-trace-private.txt').write_text(trace_text)
    trace_saved = True
    time.sleep(2)
    after = stats(); after_log = log()
    (out / 'stats-after-private.json').write_text(json.dumps(after, indent=2) + '\n')
    (out / 'dmesg-after-private.txt').write_text(after_log)
    (out / 'wakeup-after-private.txt').write_text(Path('/sys/kernel/debug/wakeup_sources').read_text())
    delta = {k: int(after[k]) - int(before[k]) for k in before if re.fullmatch(r'\d+', before[k]) and re.fullmatch(r'\d+', after[k])}
    patterns = {'warnings': 'WARNING:', 'oops': 'Oops:', 'ngd_error_interrupt': 'Error Interrupt received',
                'transfer_timeout': 'failed:-110', 'dma_prepare': 'unable to prepare channel',
                'tx_timeout': 'TX timed out', 'ngd_resume_failed': 'NGD resume failed',
                'asoc_error': 'ASoC error', 'mfd_bringup_error': 'Failed to bring up WCD934X:'}
    faults = {k: after_log.count(v) - before_log.count(v) for k, v in patterns.items()}
    residency = boot_elapsed - monotonic_elapsed
    report = dict(stage=177, kernel_build=176, requested_state='mem', selected_mem_sleep='s2idle',
                  sysfs_result=result, suspend_stats_delta=delta,
                  last_failed_device=after.get('last_failed_dev'), last_failed_errno=after.get('last_failed_errno'),
                  last_failed_step=after.get('last_failed_step'), alarm_delay_seconds=15,
                  rtc_alarm_irq_delta=irq_count()-before_irq,
                  monotonic_elapsed_seconds=monotonic_elapsed, boottime_elapsed_seconds=boot_elapsed,
                  suspend_residency_seconds=residency, fault_delta=faults,
                  same_boot=boot == Path('/proc/sys/kernel/random/boot_id').read_bytes(),
                  taint=int(Path('/proc/sys/kernel/tainted').read_text()),
                  card_present=Path('/proc/asound/cards').read_text().count('Realme X2 Pro') == 1,
                  pm_trace_captured=True, trace_isolated_from_existing_display_and_radio_instances=True,
                  no_reboot_or_driver_rebind=True, post_resume_acoustic_validation_pending=True)
    report['suspend_and_rtc_resume_passed'] = bool(result['errno'] == 0 and delta.get('success') == 1 and
                                                delta.get('fail') == 0 and residency >= 5 and
                                                report['rtc_alarm_irq_delta'] == 1 and report['same_boot'] and
                                                report['taint'] == 0 and not any(faults.values()))
    (out / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    phase('completed', passed=report['suspend_and_rtc_resume_passed'])
    print(json.dumps(report), flush=True)
finally:
    if target is not None and alarm.read_text().strip() == str(target):
        alarm.write_text('0')
    if trace.exists():
        (trace / 'tracing_on').write_text('0')
        if not trace_saved:
            (out / 'pm-trace-private.txt').write_text((trace / 'trace').read_text())
        for name in ['suspend_resume', 'device_pm_callback_start', 'device_pm_callback_end',
                     'wakeup_source_activate', 'wakeup_source_deactivate']:
            (trace / 'events/power' / name / 'enable').write_text('0')
        trace.rmdir()
