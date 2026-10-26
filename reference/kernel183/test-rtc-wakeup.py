from pathlib import Path
import json, os, re, subprocess, time

os.umask(0o077)
out = Path('/var/lib/samurai/k183-rtc')
out.mkdir(mode=0o700)
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert os.uname().version.startswith('#183 ')
assert boot == Path('/var/lib/samurai/k183-runtime/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
(out / 'boot-id-private.txt').write_bytes(boot)
alarm = Path('/sys/class/rtc/rtc0/wakealarm')
assert not alarm.read_text().strip(), 'Existing RTC wake alarm must not be replaced'
assert Path('/sys/class/rtc/rtc0/device/power/wakeup').read_text().strip() == 'enabled'

def irq_count():
    row = next(l for l in Path('/proc/interrupts').read_text().splitlines() if l.endswith('pm8xxx_rtc_alarm'))
    return sum(int(v) for v in row.split()[1:9])

before = irq_count()
target = int(Path('/sys/class/rtc/rtc0/since_epoch').read_text()) + 5
start = time.monotonic()
alarm.write_text(str(target))
(out / 'armed-private.json').write_text(json.dumps(dict(alarm=target, irq_before=before)) + '\n')
try:
    deadline = start + 10
    while irq_count() == before and time.monotonic() < deadline:
        time.sleep(.1)
    after = irq_count()
    elapsed = time.monotonic() - start
    (out / 'rtc-after-private.txt').write_text(Path('/proc/driver/rtc').read_text())
    assert after == before + 1, (before, after, elapsed)
    assert 3 <= elapsed <= 7, elapsed
    assert not alarm.read_text().strip()
    report = dict(stage=183, kernel_build=183, awake_rtc_alarm_irq_delta=after-before,
                  alarm_delay_seconds=5, observed_elapsed_seconds=elapsed,
                  rtc_epoch_used_directly_without_setting_clock=True, existing_alarm_not_overwritten=True,
                  wakeup_enabled_unchanged=True, alarm_expired=True,
                  same_boot=boot == Path('/proc/sys/kernel/random/boot_id').read_bytes(),
                  taint=int(Path('/proc/sys/kernel/tainted').read_text()), system_suspend_not_yet_tested=True)
    assert report['same_boot'] and report['taint'] == 0
    (out / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report), flush=True)
finally:
    if alarm.read_text().strip() == str(target):
        alarm.write_text('0')
