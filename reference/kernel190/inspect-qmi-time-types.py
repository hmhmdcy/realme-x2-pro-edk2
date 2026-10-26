import host

code='''import gi,json
gi.require_version('Qmi','1.0')
from gi.repository import Qmi,GObject
GObject.type_class_ref(Qmi.ClientLoc.__gtype__)
print(json.dumps(dict(signals=list(GObject.signal_list_names(Qmi.ClientLoc)),
 source_setter=Qmi.MessageLocInjectUtcTimeInput.set_time_source.__doc__,
 uncertainty_setter=Qmi.MessageLocInjectUtcTimeInput.set_time_uncertainty.__doc__,
 utc_setter=Qmi.MessageLocInjectUtcTimeInput.set_utc_time.__doc__,
 time_source_enums=[name for name in dir(Qmi) if 'TimeSource' in name],
 inject_methods=[name for name in dir(Qmi.ClientLoc) if 'inject_utc' in name])))
'''
p=host.ssh('python3 -',input=code.encode());(host.PRIVATE/'qmi-time-types-private.json').write_bytes(p.stdout);print(p.stdout.decode())
