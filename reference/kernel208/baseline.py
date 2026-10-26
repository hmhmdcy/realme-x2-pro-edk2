from pathlib import Path
import dbus, hashlib, json, os, subprocess
os.umask(0o077)
root = Path('/var/lib/samurai')
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == (root / 'k207r2-runtime/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#183 ')
out = root / 'k208-baseline'; out.mkdir(mode=0o700)
(out / 'boot-id-private.txt').write_bytes(boot)
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha('/usr/sbin/samurai-tqftpserv') == 'b3bb82b9d090a5d06e9ba2ca24e3373ab1c1e7cc2a5c6b603e2acb02715487a1'
assert sha('/usr/sbin/samurai-wifi') == '854c9a8c787d68ccefc998064983f3aa67141fe94def27f4dde87925bd18f24f'
assert sha(Path('/usr/lib/modules') / os.uname().release / 'kernel/drivers/bluetooth/hci_uart.ko') == 'f6c5ed3538270480a72cf4bf8b1339103417941930b0d8ecb941fd11d16d7020'
bus = dbus.SystemBus(private=True)
props = dbus.Interface(bus.get_object('org.freedesktop.ModemManager1', '/org/freedesktop/ModemManager1/Modem/0'), 'org.freedesktop.DBus.Properties')
loc = props.GetAll('org.freedesktop.ModemManager1.Modem.Location')
assert int(loc['Enabled']) == 0 and not loc['SignalsLocation'] and int(loc['GpsRefreshRate']) == 30
assert not bus.name_has_owner('org.freedesktop.GeoClue2')
objects = dbus.Interface(bus.get_object('org.bluez', '/'), 'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
adapter = [v['org.bluez.Adapter1'] for v in objects.values() if 'org.bluez.Adapter1' in v]
assert len(adapter) == 1 and not adapter[0]['Powered'] and not adapter[0]['Discovering']
assert not any(v.get('org.bluez.Device1', {}).get('Connected', False) for v in objects.values())
bus.close()
remoteprocs = {(p / 'name').read_text().strip(): (p / 'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')}
log = subprocess.check_output(['dmesg']); (out / 'dmesg-private.txt').write_bytes(log)
faults = {k: log.count(v) for k, v in dict(warning=b'WARNING:', oops=b'Oops:', gpu=b'gpu fault:', slpi_fatal=b'fatal error received', bluetooth=b'Frame reassembly failed').items()}
assert not any(faults.values()) and Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
assert all(v == 'running' for v in remoteprocs.values())
report = dict(stage=208, same207_r2_boot_verified=True, taint=0, fault_counts=faults, remoteprocs=remoteprocs, gps_enabled=0, signals_location=False, gps_refresh_rate=30, bt_powered=False, bt_connections=0, production_tftp207_exact=True, bt185_restored=True, uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]))
(out / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
