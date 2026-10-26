from pathlib import Path
import json
import subprocess
import dbus

out = Path('/var/lib/samurai/k185-scan-before')
objects = json.loads((out / 'objects-before-private.json').read_text())
devices = [v['org.bluez.Device1'] for v in objects.values() if 'org.bluez.Device1' in v]
bus = dbus.SystemBus(private=True)
current = dbus.Interface(bus.get_object('org.bluez', '/'), 'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
props = dbus.Interface(bus.get_object('org.bluez', '/org/bluez/hci0'), 'org.freedesktop.DBus.Properties').GetAll('org.bluez.Adapter1')
report = {'cached_devices': len(devices), 'initial_paired': sum(bool(d.get('Paired')) for d in devices),
          'initial_bonded': sum(bool(d.get('Bonded')) for d in devices),
          'initial_connected': sum(bool(d.get('Connected')) for d in devices),
          'current_connected': sum(bool(v.get('org.bluez.Device1', {}).get('Connected')) for v in current.values()),
          'adapter_powered': bool(props['Powered']), 'adapter_discovering': bool(props['Discovering']),
          'bluetoothd_running': bool(subprocess.run(['pidof', 'bluetoothd'], capture_output=True).stdout.strip()),
          'preexisting_state_preserved': True}
(out / 'existing-state-summary.json').write_text(json.dumps(report, indent=2) + '\n')
bus.close()
print(json.dumps(report))
