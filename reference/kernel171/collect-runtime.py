from pathlib import Path
import hashlib, json, os, re, subprocess, tarfile

os.umask(0o077)
out = Path('/var/lib/samurai/k171-runtime')
out.mkdir(mode=0o700)
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
(out / 'boot-id-private.txt').write_bytes(boot)
assert boot != Path('/var/lib/samurai/k171-preflash/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#168 ')

def capture(name, args):
    p = subprocess.run(args, shell=isinstance(args, str), capture_output=True)
    (out / (name + '-private.txt')).write_bytes(p.stdout + p.stderr)
    assert p.returncode == 0, (name, p.returncode)
    return p.stdout.decode(errors='replace')

log = capture('dmesg', ['dmesg'])
capture('kernel', ['uname', '-a'])
cards = capture('cards', ['cat', '/proc/asound/cards'])
capture('mixer', ['amixer', '-c', '0', 'contents'])
desktop = capture('desktop', 'pgrep -x phosh; pgrep -x phoc')
capture('amps', ['cat', '/sys/bus/i2c/devices/1-0039/status', '/sys/bus/i2c/devices/1-003a/status'])
hashes = dict((l.split()[1], l.split()[0]) for l in capture('partition-hashes', ['sha256sum', '/dev/sde11', '/dev/sde32', '/dev/sda2']).splitlines())
capture('nv-check', ['sha256sum', '-c', '/run/samurai-wifi/nv-source-hashes.txt'])
dt = Path('/sys/firmware/devicetree/base')
sd = (dt / 'soc@0/remoteproc@17300000/glink-edge/apr/service@4/dais/dai@16/qcom,sd-lines').read_bytes()
active_pins = (dt / 'soc@0/pinctrl@3100000/samurai-quat-audio-state/pins').read_bytes()
sleep_pins = (dt / 'soc@0/pinctrl@3100000/samurai-quat-sleep-state/pins').read_bytes()
(out / 'runtime-fdt-private.dtb').write_bytes(Path('/sys/firmware/fdt').read_bytes())
patterns = {'warnings': 'WARNING:', 'dma_prepare': 'unable to prepare channel', 'tx_timeout': 'TX timed out',
            'queue_full': 'Message buffer unavailable', 'resume_failed': 'NGD resume failed',
            'gpu_fault': 'gpu fault:', 'kernel_oops': 'Oops:'}
report = dict(stage=171, kernel_build=168, kernel_version=os.uname().version,
              new_boot_vs_preflash=boot != Path('/var/lib/samurai/k171-preflash/boot-id-private.txt').read_bytes(),
              same_boot_during_collection=boot == Path('/proc/sys/kernel/random/boot_id').read_bytes(),
              desktop_process_count=len(desktop.strip().splitlines()), soundcard_present='Realme X2 Pro' in cards,
              wcd_version_valid='Version:0x411' in log,
              speaker_sd_line=int.from_bytes(sd, 'big'),
              active_pins=active_pins.rstrip(b'\0').decode().split('\0'),
              sleep_pins=sleep_pins.rstrip(b'\0').decode().split('\0'),
              partition_hashes=hashes, nv_check_pass=True,
              taint=int(Path('/proc/sys/kernel/tainted').read_text()),
              faults={n: log.count(p) for n, p in patterns.items()},
              uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]))
(out / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
with tarfile.open('/tmp/k171-runtime-private.tar.gz', 'w:gz') as archive:
    archive.add(out, arcname=out.name)
print(json.dumps(report), flush=True)
assert report['same_boot_during_collection'] and report['desktop_process_count'] == 2 and report['soundcard_present'] and report['wcd_version_valid']
assert sd == b'\0\0\0\1' and active_pins == sleep_pins == b'gpio137\0gpio138\0gpio140\0'
assert hashes['/dev/sde11'] == '612a012426200d4997b33ee98edd18ea6e15a61d23901aa82cb61acd68c392f2'
assert hashes['/dev/sde32'] == 'd711ab4122eba4b0f2cc9d9792c89eb05c49957fb637b19aa595e878909921f6'
assert hashes['/dev/sda2'] == '7e085ef3264e212da7009099113b86ad1f6ec44176840f03f9b85d0e632412f3'
assert report['taint'] == 0 and all(v == 0 for v in report['faults'].values())
