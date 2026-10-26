from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import time

out = Path('/var/lib/samurai/k142-settled-health')
boot_path = Path('/proc/sys/kernel/random/boot_id')
boot = Path('/var/lib/samurai/k142-first-runtime/boot-id-private.txt').read_bytes()
assert os.geteuid() == 0 and boot_path.read_bytes() == boot
assert os.uname().version.startswith('#140 ') and not out.exists()
out.mkdir(mode=0o700)
(out / 'boot-id-private.txt').write_bytes(boot)
def capture(args, name, check=False, timeout=20):
    with (out / name).open('w') as file:
        return subprocess.run(args, stdout=file, stderr=subprocess.STDOUT, check=check, timeout=timeout).returncode
def pids():
    return {name: subprocess.run(['pgrep', '-x', name], capture_output=True, text=True).stdout.strip().splitlines()
            for name in ['phosh', 'phoc']}
def counts(text):
    return {name: text.count(pattern) for name, pattern in [('gpu_faults', 'gpu fault:'),
        ('dpu_timeouts', 'frame done timeout'), ('dsi_errors', 'dsi_err_worker'),
        ('warnings', 'WARNING:'), ('tx_dma_errors', 'unable to prepare channel')]}
capture(['dmesg'], 'dmesg-before-private.txt', check=True)
before = counts((out / 'dmesg-before-private.txt').read_text())
samples = []
started = time.monotonic()
for index in range(8):
    assert boot_path.read_bytes() == boot
    row = dict(index=index, elapsed_seconds=round(time.monotonic() - started, 3),
               taint=int(Path('/proc/sys/kernel/tainted').read_text()), desktop_pids=pids())
    for supply in ['bq28z610-0', 'mp2650-input']:
        row[supply] = {}
        for prop in ['online', 'status', 'capacity', 'temp', 'voltage_now', 'current_now']:
            try:
                row[supply][prop] = (Path('/sys/class/power_supply') / supply / prop).read_text().strip()
            except OSError as exc:
                row[supply][prop] = dict(errno=exc.errno)
    row['crtc_active'] = 'active=1' in Path('/sys/kernel/debug/dri/1/state').read_text()
    samples.append(row)
    (out / 'samples-private.json').write_text(json.dumps(samples, indent=2) + '\n')
    if index < 7:
        time.sleep(4)
capture(['dmesg'], 'dmesg-final-private.txt', check=True)
after = counts((out / 'dmesg-final-private.txt').read_text())
capture(['rc-service', 'bluetooth', 'status'], 'bluez-status.txt')
capture(['iw', 'dev', 'wlan0', 'link'], 'wifi-link-private.txt')
capture(['cat', '/sys/kernel/debug/dri/1/state'], 'drm-final-private.txt')
capture(['cat', '/sys/kernel/debug/dri/1/encoder-0/status'], 'encoder-final-private.txt')
capture(['cat', '/home/cy122/.local/state/samurai-phosh-session.log'], 'phosh-session-private.txt')
report = dict(stage=142, current_kernel=140, passive_observation_only=True,
    samples=len(samples), elapsed_seconds=round(time.monotonic() - started, 3),
    same_boot=True, taint_values=sorted({s['taint'] for s in samples}), counts_before=before, counts_after=after,
    counters_unchanged=before == after,
    phosh_present_final=bool(samples[-1]['desktop_pids']['phosh']),
    phoc_present_final=bool(samples[-1]['desktop_pids']['phoc']),
    desktop_pids_unchanged=all(s['desktop_pids'] == samples[0]['desktop_pids'] for s in samples),
    normal_screen_or_gpu_load_triggered=False, charging_control_accepted=False,
    display_accepted=False, gpu_accepted=False, goal_complete=False)
(out / 'health-validation.json').write_text(json.dumps(report, indent=2) + '\n')
(out / 'SHA256SUMS').write_text('\n'.join(hashlib.sha256(p.read_bytes()).hexdigest() + '  ./' + p.name
    for p in sorted(out.iterdir()) if p.is_file()) + '\n')
subprocess.run(['tar', '-C', str(out), '-czf', '/tmp/k142-settled-health-private.tar.gz', '.'], check=True, timeout=20)
print(json.dumps(report, indent=2), flush=True)
