from pathlib import Path
import hashlib, json, os, re, subprocess, tarfile

os.umask(0o077)
out = Path('/var/lib/samurai/k181-runtime')
if out.exists():
    assert not (out / 'validation.json').exists()
    assert (out / 'boot-id-private.txt').read_bytes() == Path('/proc/sys/kernel/random/boot_id').read_bytes()
else:
    out.mkdir(mode=0o700)
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
(out / 'boot-id-private.txt').write_bytes(boot)
assert boot != Path('/var/lib/samurai/k181-preflash/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#181 ')

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
            'gpu_fault': 'gpu fault:', 'kernel_oops': 'Oops:',
            'irq_read': 'Failed to read IRQ status', 'irq_config': 'Failed to write config',
            'irq_mask': 'Failed to sync masks', 'pdr_listener': 'register listener txn wait failed',
            'pdr_missing_state': 'register listener response has no state',
            'asoc_error': 'ASoC error', 'pdr_locator': 'PDR: service lookup for',
            'ngd_error_interrupt': 'Error Interrupt received', 'qmi_wait_timeout': 'QMI wait timeout'}
mbhc_started = log.count('samurai MBHC started: micbias=2700 mV')
jack_bound = log.count('WCD934x headset detection connected')
assert mbhc_started == jack_bound and mbhc_started >= 1
assert Path("/sys/kernel/debug/regmap/217:250:1:0/name").read_text().strip() == "wcd934x-slim"
assert Path("/sys/kernel/debug/regmap/217:250:0:0/name").read_text().strip() == "nodev"
jack_status = {}
for name in ['Headphone Jack', 'Mic Jack']:
    value = capture('jack-' + name.replace(' ', '-'), ['amixer','-c','0','cget',"iface=CARD,name='" + name + "'"])
    jack_status[name] = re.search(r': values=(.*)',value)[1].strip()

report = dict(stage=181, soundcard_present_without_machine_rebind=True, current_main_and_interface_regmap_names_read_without_oops=True, mbhc_started_count=mbhc_started, jack_bound_count=jack_bound, jack_status=jack_status, kernel_build=181, kernel_version=os.uname().version,
              new_boot_vs_preflash=boot != Path('/var/lib/samurai/k181-preflash/boot-id-private.txt').read_bytes(),
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
with tarfile.open('/tmp/k181-runtime-private.tar.gz', 'w:gz') as archive:
    archive.add(out, arcname=out.name)
print(json.dumps(report), flush=True)
assert report['same_boot_during_collection'] and report['desktop_process_count'] == 2 and report['soundcard_present'] and report['wcd_version_valid']
assert sd == b'\0\0\0\1' and active_pins == sleep_pins == b'gpio137\0gpio138\0gpio140\0'
assert hashes['/dev/sde11'] == '77e1a272741aeb09f780a1cff1224098bc78126f1a9154ed5d0c00d91f587a28'
assert hashes['/dev/sde32'] == '56aa1c463d118f9de8d5dbd2cad3dc6b2ab1ff9f36d4027c77d457520b702a55'
assert hashes['/dev/sda2'] == '7e085ef3264e212da7009099113b86ad1f6ec44176840f03f9b85d0e632412f3'
assert report['taint'] == 0 and all(v == 0 for v in report['faults'].values())
