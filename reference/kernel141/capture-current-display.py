from pathlib import Path
import hashlib
import json
import os
import subprocess
import time

out = Path('/var/lib/samurai/k141-current140-display')
assert os.geteuid() == 0 and not out.exists()
assert os.uname().version.startswith('#140 ')
boot_path = Path('/proc/sys/kernel/random/boot_id')
boot = Path('/var/lib/samurai/k140-first-runtime/boot-id-private.txt').read_bytes()
assert boot_path.read_bytes() == boot
out.mkdir(mode=0o700)
(out / 'boot-id-private.txt').write_bytes(boot)

def capture(args, name, timeout=20):
    with (out / name).open('w') as file:
        return subprocess.run(args, stdout=file, stderr=subprocess.STDOUT, timeout=timeout).returncode

capture(['dmesg'], 'dmesg-current-private.txt')
capture(['cat', '/sys/kernel/debug/dri/1/state'], 'drm-current-private.txt')
capture(['cat', '/sys/kernel/debug/dri/1/encoder-0/status'], 'encoder-current-private.txt')
capture(['cat', '/sys/kernel/debug/dri/1/clients'], 'clients-current-private.txt')
capture(['cat', '/sys/kernel/debug/dri/1/gpu'], 'gpu-current-private.txt')
capture(['cat', '/home/cy122/.local/state/samurai-phosh-session.log'], 'desktop-session-private.txt')
capture(['su', '-s', '/bin/sh', 'cy122', '-c', 'env XDG_RUNTIME_DIR=/run/user/10000 WAYLAND_DISPLAY=wayland-0 wlr-randr'], 'outputs-current-private.txt')
capture(['pgrep', '-x', 'phosh'], 'phosh-private.txt')
capture(['pgrep', '-x', 'phoc'], 'phoc-private.txt')
for name in ['display', 'radio']:
    trace = Path('/sys/kernel/tracing/instances') / name
    for field in ['tracing_on', 'trace_clock', 'current_tracer', 'buffer_size_kb', 'events/enable']:
        capture(['cat', str(trace / field)], name + '-' + field.replace('/', '-') + '.txt')
    stats = {p.parent.name: p.read_text() for p in (trace / 'per_cpu').glob('cpu*/stats')}
    (out / (name + '-trace-stats-private.json')).write_text(json.dumps(stats, indent=2) + '\n')
    if name == 'display':
        capture(['cat', str(trace / 'trace')], 'display-trace-private.txt', timeout=25)
        capture(['cat', '/etc/init.d/samurai-display-trace'], 'display-service-private.txt')
        capture(['cat', '/usr/sbin/samurai-display-trace'], 'display-script-private.txt')
capture(['cat', '/proc/uptime', '/proc/sys/kernel/tainted'], 'state.txt')
assert boot_path.read_bytes() == boot
d = (out / 'dmesg-current-private.txt').read_text()
report = dict(stage=141, current_kernel=140, same_boot=True, capture_readonly=True,
    phosh_present=bool((out / 'phosh-private.txt').read_text().strip()),
    phoc_present=bool((out / 'phoc-private.txt').read_text().strip()),
    taint=int(Path('/proc/sys/kernel/tainted').read_text()),
    counts={name: d.count(pattern) for name, pattern in [('gpu_faults', 'gpu fault:'),
    ('dpu_timeouts', 'frame done timeout'), ('dsi_errors', 'dsi_err_worker'),
    ('warnings', 'WARNING:'), ('tx_dma_errors', 'unable to prepare channel')]},
    no_gpu_load_or_output_transition=True, goal_complete=False)
(out / 'current-validation.json').write_text(json.dumps(report, indent=2) + '\n')
(out / 'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest() + '  ./' + p.name + '\n'
    for p in sorted(out.iterdir()) if p.is_file()))
subprocess.run(['tar', '-C', str(out), '-czf', '/tmp/k141-current140-display-private.tar.gz', '.'], check=True, timeout=25)
print(json.dumps(report, indent=2))
