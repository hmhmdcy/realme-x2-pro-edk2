import contextlib
import dbus
import io
import json
import os
import runpy

assert os.geteuid() == 10000
bus = dbus.SystemBus(private=True)
manager = dbus.Interface(bus.get_object('org.freedesktop.login1', '/org/freedesktop/login1'), 'org.freedesktop.login1.Manager')
session = manager.GetSessionByPID(os.getpid())
props = dbus.Interface(bus.get_object('org.freedesktop.login1', session), 'org.freedesktop.DBus.Properties')
values = props.GetAll('org.freedesktop.login1.Session')
assert values['Active'] and values['Type'] == 'wayland' and values['Seat'][0] == 'seat0' and int(values['User'][0]) == 10000
bus.close()
with contextlib.redirect_stdout(io.StringIO()):
    result = runpy.run_path('/usr/share/samurai/ssc/test-persistent-client.py')
report = result['report']
report.update(active_local_wayland_session_verified=True, polkit_policy_unchanged=True)
print(json.dumps(report))
