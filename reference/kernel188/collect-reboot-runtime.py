"""Run the baseline boot checks plus actual OpenRC SSC/SensorProxy checks."""
from pathlib import Path
import subprocess
import host

data = (Path(__file__).resolve().parent.parent / 'kernel185/collect-reboot-runtime.py').read_text()
data = data.replace('k185-reboot-runtime', 'k188-reboot-runtime').replace('k185-preflash', 'k188-preflash')
data = data.replace("'stage': 185", "'stage': 188")
data = data.replace("'slpi': 'offline'", "'slpi': 'running'")
data = data.replace("== 'vdd=0 vddio=0'", "== 'vdd=1 vddio=1'")
data = data.replace("report = {'stage': 188", """
deadline = time.monotonic() + 65
while not bus.name_has_owner('net.hadess.SensorProxy') and time.monotonic() < deadline:
    time.sleep(.5)
assert bus.name_has_owner('net.hadess.SensorProxy')
proxy = dbus.Interface(bus.get_object('net.hadess.SensorProxy', '/net/hadess/SensorProxy'), 'org.freedesktop.DBus.Properties')
values = proxy.GetAll('net.hadess.SensorProxy')
assert all(values.get(k) for k in ['HasAccelerometer','HasAmbientLight','HasProximity'])
for service in ['samurai-ssc', 'iio-sensor-proxy']:
    assert subprocess.run(['rc-service', service, 'status'], capture_output=True).returncode == 0
capture(['/usr/sbin/samurai-ssc', 'status'], 'ssc-service-status.txt')
loaded = subprocess.check_output(['pidof', 'iio-sensor-proxy'], text=True).strip().split()
assert len(loaded) == 1
maps = Path('/proc') / loaded[0] / 'maps'
assert '/usr/lib/samurai/ssc/libssc.so.2' in maps.read_text()
report = {'stage': 188""")
# Original collector closes its Bluetooth bus before this extension; create a new private one.
data = data.replace("deadline = time.monotonic() + 65\n", "bus = dbus.SystemBus(private=True)\ndeadline = time.monotonic() + 65\n")
data = data.replace("(out / 'summary.json').write_text", """report.update(ssc_service_started_automatically=True, sensor_proxy_started_automatically=True,
    candidate_library_loaded=True, sensor_proxy={str(k):values[k] for k in
        ['HasAccelerometer','HasAmbientLight','HasProximity','AccelerometerOrientation','LightLevel','LightLevelUnit']})
bus.close()
(out / 'summary.json').write_text""")
try:
    p = host.ssh('python3 -', input=data.encode(), timeout=165)
except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
    path = host.PRIVATE / 'reboot-runtime-first-failure-private.log'
    if path.exists():
        path = host.PRIVATE / 'reboot-runtime-followup-failure-private.log'
    assert not path.exists()
    path.write_bytes((error.stdout or b'') + (error.stderr or b''))
    raise
(host.PRIVATE / 'reboot-runtime-host-private.log').write_bytes(p.stdout + p.stderr)
print(p.stdout.decode().strip())
