from pathlib import Path
import configparser
import hashlib
import io
import json
import os
import re
import subprocess
import dbus

os.umask(0o077)
out = Path('/var/lib/samurai/k204-bt-policy')
out.mkdir(mode=0o700)
assert os.uname().version.startswith('#183 ')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes() == Path('/var/lib/samurai/k204-runtime/boot-id-private.txt').read_bytes()
bus = dbus.SystemBus(private=True)
objects = dbus.Interface(bus.get_object('org.bluez', '/'), 'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
props = dbus.Interface(bus.get_object('org.bluez', '/org/bluez/hci0'), 'org.freedesktop.DBus.Properties').GetAll('org.bluez.Adapter1')
assert not props['Powered'] and not props['Discovering']
assert all(not v.get('org.bluez.Device1', {}).get('Connected', False) for v in objects.values())
bus.close()
path = Path('/etc/bluetooth/main.conf')
before = path.read_bytes()
(out / 'main.conf-before-private').write_bytes(before)


def keys():
    data = {}
    for p in Path('/var/lib/bluetooth').rglob('info'):
        config = configparser.ConfigParser(interpolation=None)
        config.read(p)
        secret = {s: dict(config[s]) for s in config.sections() if 'key' in s.lower()}
        data[str(p)] = secret
    return data


(out / 'pairing-keys-before-private.json').write_text(json.dumps(keys(), indent=2) + '\n')
subprocess.run(['rc-service', 'bluetooth', 'stop'], capture_output=True, check=True, timeout=25)
assert not subprocess.run(['pidof', 'bluetoothd'], capture_output=True).stdout.strip()
text = before.decode()
match = re.search(r'(?ms)^\[Policy\]\s*\n(.*?)(?=^\[|\Z)', text)
assert match
body = match[1]
for key, value in [('ReconnectAttempts', '0'), ('ReconnectUUIDs', '')]:
    pattern = r'(?m)^' + key + r'\s*=.*$'
    if re.search(pattern, body):
        body = re.sub(pattern, key + '=' + value, body)
    else:
        body += '\n' + key + '=' + value + '\n'
after = text[:match.start(1)] + body + text[match.end(1):]
temporary = path.with_name('main.conf.k204-new')
temporary.write_text(after)
temporary.chmod(path.stat().st_mode & 0o777)
os.replace(temporary, path)
subprocess.run(['rc-service', 'bluetooth', 'start'], capture_output=True, check=True, timeout=30)
assert keys() == json.loads((out / 'pairing-keys-before-private.json').read_text())
report = {'original_config_sha256': hashlib.sha256(before).hexdigest(),
          'temporary_config_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
          'preexisting_pairing_keys_unchanged': True, 'reconnect_attempts': 0,
          'reconnect_uuids_empty': True, 'bluetooth_service_started': True}
(out / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
