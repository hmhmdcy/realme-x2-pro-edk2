"""Use the already running SensorProxy from the actual unprivileged desktop UID."""
import dbus
import json
import os
import time

assert os.geteuid() == 10000
bus = dbus.SystemBus(private=True)
assert bus.name_has_owner('net.hadess.SensorProxy')
obj = bus.get_object('net.hadess.SensorProxy', '/net/hadess/SensorProxy')
props = dbus.Interface(obj, 'org.freedesktop.DBus.Properties')
iface = dbus.Interface(obj, 'net.hadess.SensorProxy')
values = props.GetAll('net.hadess.SensorProxy')
assert all(values.get(k) for k in ['HasAccelerometer', 'HasAmbientLight', 'HasProximity'])
claims = []
try:
    for name in ['Accelerometer', 'Light', 'Proximity']:
        getattr(iface, 'Claim' + name)(timeout=5)
        claims.append(name)
    time.sleep(6)
    values = props.GetAll('net.hadess.SensorProxy')
    report = dict(desktop_uid=10000, desktop_claims_succeeded=True,
                  sensor_proxy={str(k): values[k] for k in ['HasAccelerometer',
                      'HasAmbientLight', 'HasProximity', 'AccelerometerOrientation',
                      'LightLevel', 'LightLevelUnit', 'ProximityNear']})
finally:
    for name in reversed(claims):
        getattr(iface, 'Release' + name)(timeout=5)
    bus.close()
report['releases_succeeded'] = True
print(json.dumps(report))
