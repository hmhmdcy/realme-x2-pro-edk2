"""Exercise the patched library through the stock CLI and SensorProxy D-Bus."""
from pathlib import Path
import collections
import hashlib
import json
import os
import re
import subprocess
import time
import dbus
import argparse

os.umask(0o077)
parser = argparse.ArgumentParser()
parser.add_argument('--output', required=True)
args = parser.parse_args()
out = Path(args.output)
out.mkdir(mode=0o700)
candidate = Path('/var/lib/samurai/k184-libssc-r2/build-r4/src/libssc.so.2')
assert candidate.is_file()
assert Path('/sys/class/remoteproc/remoteproc0/state').read_text().strip() == 'running'
assert not subprocess.run(['pidof', 'iio-sensor-proxy'], capture_output=True).stdout.strip()
package_db = Path('/lib/apk/db/installed').read_bytes()
system_sha = hashlib.sha256(Path('/usr/lib/libssc.so.2').read_bytes()).hexdigest()
env = dict(os.environ, LD_LIBRARY_PATH=str(candidate.parent))
env.pop('LIBSSC_LIGHT_DATA_TYPE', None)
summary = {'candidate_sha256': hashlib.sha256(candidate.read_bytes()).hexdigest()}


def cli(name, environment):
    p = subprocess.run(['ssccli', '--debug', '--sensor', 'light', '--timeout', '8'],
                       capture_output=True, env=environment, timeout=25)
    (out / (name + '-private.txt')).write_bytes(p.stdout + p.stderr)
    text = (p.stdout + p.stderr).decode(errors='replace')
    return {'exit_code': p.returncode,
            'measurements': len(re.findall(r'Light sensor measurement:', text)),
            'disabled': 'Light sensor disabled' in text}


summary['default_type'] = cli('default', env)
assert summary['default_type']['exit_code'] != 0 and summary['default_type']['measurements'] == 0
env['LIBSSC_LIGHT_DATA_TYPE'] = 'wise_light'
env['G_MESSAGES_DEBUG'] = 'all'
summary['vendor_type'] = cli('wise', env)
assert summary['vendor_type']['exit_code'] == 0 and summary['vendor_type']['measurements'] > 0
assert summary['vendor_type']['disabled']

proxy = None
claimed = False
interface = None
bus = dbus.SystemBus(private=True)
try:
    with (out / 'proxy-private.txt').open('wb') as log:
        proxy = subprocess.Popen(['/usr/libexec/iio-sensor-proxy'], env=env,
                                 stdout=log, stderr=subprocess.STDOUT)
        dbus_if = dbus.Interface(bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus'), 'org.freedesktop.DBus')
        deadline = time.monotonic() + 35
        values = {}
        while time.monotonic() < deadline:
            if proxy.poll() is not None:
                raise RuntimeError('SensorProxy exited during startup')
            if dbus_if.NameHasOwner('net.hadess.SensorProxy'):
                owner = dbus_if.GetNameOwner('net.hadess.SensorProxy')
                assert int(dbus_if.GetConnectionUnixProcessID(owner)) == proxy.pid
                obj = bus.get_object('net.hadess.SensorProxy', '/net/hadess/SensorProxy')
                properties = dbus.Interface(obj, 'org.freedesktop.DBus.Properties')
                values = properties.GetAll('net.hadess.SensorProxy', timeout=5)
                if values.get('HasAmbientLight'):
                    break
            time.sleep(.25)
        assert values.get('HasAmbientLight')
        interface = dbus.Interface(obj, 'net.hadess.SensorProxy')
        interface.ClaimLight(timeout=5)
        claimed = True
        time.sleep(5)
        values = properties.GetAll('net.hadess.SensorProxy', timeout=5)
        summary['sensor_proxy'] = {name: values.get(name) for name in
                                   ['HasAmbientLight', 'LightLevelUnit', 'LightLevel', 'HasProximity',
                                    'ProximityNear', 'HasAccelerometer']}
        summary['light_claim_succeeded'] = True
finally:
    if claimed:
        interface.ReleaseLight(timeout=5)
    bus.close()
    if proxy is not None and proxy.poll() is None:
        proxy.terminate()
        try:
            proxy.wait(timeout=12)
        except subprocess.TimeoutExpired:
            proxy.kill()
            proxy.wait(timeout=3)
    if proxy is not None:
        summary['proxy_exit'] = proxy.returncode
    summary['system_library_unchanged'] = hashlib.sha256(Path('/usr/lib/libssc.so.2').read_bytes()).hexdigest() == system_sha
    summary['package_database_unchanged'] = Path('/lib/apk/db/installed').read_bytes() == package_db
    summary['physical_lux_accuracy_proven'] = False
    (out / 'summary.json').write_text(json.dumps(summary, indent=2, default=str) + '\n')
    print(json.dumps(summary, default=str))
