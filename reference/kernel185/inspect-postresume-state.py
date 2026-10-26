"""Store raw Wi-Fi/DSP state privately and report only operational fields."""
from pathlib import Path
import json
import os
import re
import subprocess
import time
import dbus

os.umask(0o077)
out = Path('/var/lib/samurai/k185-postresume-inspection')
out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes() == Path('/var/lib/samurai/k185-reboot-runtime/boot-id-private.txt').read_bytes()
link = subprocess.check_output(['iw', 'dev', 'wlan0', 'link'], text=True)
(out / 'wifi-private.txt').write_text(link)
log = subprocess.check_output(['dmesg'], text=True)
(out / 'dmesg-private.txt').write_text(log)
before = Path('/var/lib/samurai/k185-scan-after-suspend/powered-suspend/dmesg-before-private.txt').read_text()
assert log.startswith(before)
delta = log[len(before):]
bus = dbus.SystemBus(private=True)
objects = dbus.Interface(bus.get_object('org.bluez', '/'), 'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
props = dbus.Interface(bus.get_object('org.bluez', '/org/bluez/hci0'), 'org.freedesktop.DBus.Properties').GetAll('org.bluez.Adapter1')
freq = re.search(r'freq:\s*(\d+)', link)
faults = {key: delta.count(value) for key, value in {
    'warning': 'WARNING:', 'oops': 'Oops:', 'bluetooth_reassembly': 'Frame reassembly failed',
    'gpu': 'gpu fault:', 'dpu': 'Frame done timeout', 'asoc': 'ASoC error',
    'wifi_key_delete': 'failed to remove peer key', 'wifi_resume_failure': 'failed to resume',
    'wifi_firmware_crash': 'firmware crashed'}.items()}
report = dict(stage=185, kernel_build=183, same_boot=True,
    taint=int(Path('/proc/sys/kernel/tainted').read_text()),
    wifi_connected='Connected to ' in link, wifi_frequency_mhz=int(freq[1]) if freq else None,
    bluetooth_powered=bool(props['Powered']), bluetooth_discovering=bool(props['Discovering']),
    connected_bluetooth_devices=sum(bool(v.get('org.bluez.Device1', {}).get('Connected')) for v in objects.values()),
    phosh_running=bool(subprocess.run(['pidof', 'phosh'], capture_output=True).stdout.strip()),
    remoteproc={(p / 'name').read_text().strip(): (p / 'state').read_text().strip()
                for p in Path('/sys/class/remoteproc').glob('remoteproc*')},
    post_resume_fault_delta=faults, pulse_rx_nuls=int(Path('/sys/kernel/debug/bluetooth/hci0/ibs/pulse_rx_nuls').read_text()),
    uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]), observed_monotonic=time.monotonic())
(out / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
bus.close()
print(json.dumps(report))
