from pathlib import Path
import json, os, subprocess

os.umask(0o077)
out = Path('/var/lib/samurai/k177-runtime')
out.mkdir(mode=0o700)
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert os.uname().version.startswith('#176 ')
assert boot == Path('/var/lib/samurai/k176-runtime/boot-id-private.txt').read_bytes()
(out / 'boot-id-private.txt').write_bytes(boot)
idle = json.loads(Path('/var/lib/samurai/k177-suspend-idle/validation.json').read_text())
active = json.loads(Path('/var/lib/samurai/k177-suspend-active/validation.json').read_text())
assert idle['suspend_and_rtc_resume_passed']
assert active['suspend_and_rtc_resume_passed'] and active['active_duplex_survived']
assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
assert not Path('/sys/class/rtc/rtc0/wakealarm').read_text().strip()
assert not Path('/sys/kernel/tracing/instances/k177-pm').exists()
assert 'Realme X2 Pro' in Path('/proc/asound/cards').read_text()
for p in ['pcm0p', 'pcm1c']:
    assert Path('/proc/asound/card0/' + p + '/sub0/status').read_text().strip() == 'closed'
for a in ['1-0039', '1-003a']:
    assert 'powered=0 muted=1' in Path('/sys/bus/i2c/devices/' + a + '/status').read_text()
(out / 'dmesg-before-private.txt').write_bytes(subprocess.check_output(['dmesg']))
report = dict(stage=177, kernel_build=176, same_boot=True, idle_and_active_system_s2idle_passed=True,
              active_desktop_duplex_survived=True, rtc_alarm_cleared=True, pm_trace_instance_removed=True,
              card_present=True, pcm_and_amps_closed=True, taint=0, no_reboot_or_driver_rebind=True)
(out / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report), flush=True)
