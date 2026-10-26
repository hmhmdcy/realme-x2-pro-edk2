from pathlib import Path
import hashlib
import json
import os
import subprocess

out = Path('/var/lib/samurai/k137-before-rollback')
assert os.geteuid() == 0 and not out.exists()
assert os.uname().version.startswith('#137 ')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes() == Path('/var/lib/samurai/k137-first-runtime/boot-id-private.txt').read_bytes()
out.mkdir(mode=0o700)
def capture(args, name, check=True, timeout=15):
    with (out / name).open('w') as file:
        return subprocess.run(args, stdout=file, stderr=subprocess.STDOUT, check=check, timeout=timeout).returncode
capture(['dmesg'], 'dmesg-private.txt')
for name in ['phosh', 'phoc']:
    capture(['pgrep', '-x', name], name + '.txt', check=False)
for path, name in [('/proc/sys/kernel/random/boot_id', 'boot-id-private.txt'),
                   ('/proc/uptime', 'uptime.txt'), ('/proc/sys/kernel/tainted', 'taint.txt'),
                   ('/sys/kernel/debug/dri/1/state', 'drm-state-private.txt'),
                   ('/sys/kernel/debug/dri/1/encoder0', 'encoder-private.txt'),
                   ('/sys/kernel/debug/clk/clk_summary', 'clocks-private.txt'),
                   ('/sys/class/power_supply/bq28z610-0/uevent', 'gauge-private.txt'),
                   ('/sys/class/power_supply/mp2650-input/uevent', 'input-private.txt')]:
    capture(['cat', path], name, check=False)
(out / 'collection-scope.json').write_text(json.dumps(dict(read_only=True, display_or_gpu_workload_run=False,
    reboot_or_config_operation_replayed=False)) + '\n')
(out / 'SHA256SUMS').write_text('\n'.join(hashlib.sha256(p.read_bytes()).hexdigest() + '  ./' + p.name for p in sorted(out.iterdir()) if p.is_file()) + '\n')
subprocess.run(['tar', '-C', str(out), '-czf', '/tmp/k137-before-rollback-private.tar.gz', '.'], check=True, timeout=20)
print('K137_CURRENT_DISPLAY_FAILURE_SITE_SAVED_READONLY', flush=True)
