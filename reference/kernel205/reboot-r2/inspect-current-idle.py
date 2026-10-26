"""Fresh read-only health and deployment snapshot; never start GNSS or BT."""
from pathlib import Path
import configparser, dbus, hashlib, json, os, subprocess

assert Path('/proc/sys/kernel/random/boot_id').read_bytes() == Path('/var/lib/samurai/k205r2-runtime/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#183 ')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
module = Path('/usr/lib/modules') / os.uname().release / 'kernel/drivers/bluetooth/hci_uart.ko'
assert sha(module) == 'ee14310674722fda61529a113cc8e90ae3c247e5c36a5a2c95544aed7741b480'
assert sha('/usr/sbin/samurai-bluetooth') == 'ae46b800ed036f0527c6a0434c7da03c8a722abf74a34b420cbe44e1913ef762'
bus = dbus.SystemBus(private=True)
bt = dbus.Interface(bus.get_object('org.bluez', '/'), 'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
adapters = [v['org.bluez.Adapter1'] for v in bt.values() if 'org.bluez.Adapter1' in v]
assert len(adapters) == 1
assert not adapters[0]['Powered'] and not adapters[0]['Discovering']
assert not any(v.get('org.bluez.Device1', {}).get('Connected', False) for v in bt.values())
mm = dbus.Interface(bus.get_object('org.freedesktop.ModemManager1', '/org/freedesktop/ModemManager1'), 'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
modems = [v for v in mm.values() if 'org.freedesktop.ModemManager1.Modem' in v]
assert len(modems) == 1
loc = modems[0]['org.freedesktop.ModemManager1.Modem.Location']
assert int(loc['Enabled']) == 0
cfg = configparser.ConfigParser(interpolation=None)
cfg.read('/var/lib/samurai/k205-bt-policy/main.conf-before-private')
auto = cfg.get('Policy', 'AutoEnable', fallback='unspecified')
remoteprocs = {p.joinpath('name').read_text().strip(): p.joinpath('state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')}
dmesg = subprocess.check_output(['dmesg'])
faults = {k: dmesg.count(v) for k, v in dict(warning=b'WARNING:', oops=b'Oops:', gpu=b'gpu fault:', slpi_fatal=b'fatal error received', bluetooth=b'Frame reassembly failed').items()}
result = dict(stage=205, fresh_same_r2_boot_verified=True, uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]), taint=int(Path('/proc/sys/kernel/tainted').read_text()), fault_counts=faults, remoteprocs=remoteprocs, bt_powered=False, bt_discovering=False, bt_connections=0, gnss_enabled=0, signals_location=bool(loc['SignalsLocation']), gps_refresh_rate=int(loc['GpsRefreshRate']), temporary_diagnostic_module_still_installed=True, temporary_helper_has_no_trace_hook=True, original_bluez_autoenable=auto, read_only=True)
bus.close()
print(json.dumps(result))
