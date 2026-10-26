import host

code='''from pathlib import Path
import subprocess,gi,json
gi.require_version('Qmi','1.0')
from gi.repository import Qmi,GObject
root=Path('/var/lib/samurai/k190-api');assert not root.exists();root.mkdir(mode=0o700)
for name,cmd in [('loc-help',['qmicli','--help-loc']),('geoclue-conf',['cat','/etc/geoclue/geoclue.conf']),('geoclue-files',['apk','info','-L','geoclue'])]:
 p=subprocess.run(cmd,capture_output=True);(root/(name+'-private.txt')).write_bytes(p.stdout+p.stderr)
 print(name,p.stdout.decode(errors='replace'))
print(json.dumps(dict(time_input_methods=[m for m in dir(Qmi.MessageLocInjectUtcTimeInput) if m.startswith('set_')],
 client_loc_signals=list(GObject.signal_list_names(Qmi.ClientLoc)),
 location_modes=[m for m in dir(Qmi.LocOperationMode) if m.isupper()])))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=25);(host.PRIVATE/'location-api-private.log').write_bytes(p.stdout+p.stderr)
print(p.stdout.decode())
