from pathlib import Path
import hashlib, json, re, subprocess, tarfile

out = Path('/var/lib/samurai/k166-baseline')
out.mkdir(mode=0o700, exist_ok=False)
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
(out / 'boot-id-private.txt').write_bytes(boot)
def capture(name, command):
    p = subprocess.run(command, shell=True, capture_output=True)
    (out / (name + '-private.txt')).write_bytes(p.stdout + p.stderr)
    return p.stdout.decode(errors='replace')
version = capture('uname', 'uname -v')
assert version.startswith('#163 ')
dmesg = capture('dmesg', 'dmesg')
capture('mixer', 'amixer -c 0 contents')
capture('audio-state', 'cat /proc/asound/cards /proc/asound/pcm /proc/asound/card0/pcm0p/sub0/status /proc/asound/card0/pcm1c/sub0/status; cat /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status; for p in /sys/bus/platform/devices/qcom,slim-ngd.1/power/*; do echo "$p"; cat "$p" 2>/dev/null; done')
capture('routes', 'cat /usr/share/alsa/ucm2/conf.d/Realme_X2_Pro/*.conf; su -s /bin/sh cy122 -c "XDG_RUNTIME_DIR=/run/user/10000 pactl list short sinks; XDG_RUNTIME_DIR=/run/user/10000 pactl list short sources"')
capture('remoteproc', 'for p in /sys/class/remoteproc/remoteproc*; do cat "$p/name" "$p/state"; done')
capture('desktop', 'pgrep -x phosh; pgrep -x phoc')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes() == boot
report = dict(stage=166, baseline_kernel=163, taint=int(Path('/proc/sys/kernel/tainted').read_text()),
              uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]),
              same_boot_during_capture=True, faults={key:len(re.findall(pattern,dmesg)) for key,pattern in {
                  'warnings':r'WARNING:', 'dma_prepare':r'unable to prepare channel',
                  'tx_timeout':r'TX timed out', 'queue_exhaustion':r'Message buffer unavailable',
                  'suspend_rejected':r'NGD suspend rejected', 'wake_failed':r'HW wakeup attempt during SSR'}.items()})
(out / 'validation.json').write_text(json.dumps(report, indent=2)+'\n')
with tarfile.open('/tmp/k166-baseline-private.tar.gz', 'w:gz') as archive:
    archive.add(out, arcname=out.name)
print(json.dumps(report))
