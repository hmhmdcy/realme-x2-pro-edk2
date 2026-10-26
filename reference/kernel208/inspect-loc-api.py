from pathlib import Path
import dbus,gi,json,os
gi.require_version('Qmi','1.0')
from gi.repository import Qmi
os.umask(0o077)
root=Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k208-baseline/boot-id-private.txt').read_bytes()
out=root/'k208-loc-api-r2';out.mkdir(mode=0o700)
names=['MessageLocSetNmeaTypesInput','LocNmeaType','LocEventRegistrationFlag','MessageLocRegisterEventsInput','ClientLoc']
docs={name:{n:str(getattr(getattr(Qmi,name),n).__doc__) for n in dir(getattr(Qmi,name)) if any(word in n for word in ['nmea','supported','gnss','register'])} for name in names}
flags={name:{n:int(getattr(getattr(Qmi,name),n)) for n in dir(getattr(Qmi,name)) if n.isupper()} for name in ['LocNmeaType','LocEventRegistrationFlag']}
(out/'api-docs-private.json').write_text(json.dumps(docs,indent=2)+'\n')
print(json.dumps(dict(stage=208,flags=flags,set_nmea_docs=docs['MessageLocSetNmeaTypesInput'],client_methods=[n for n in dir(Qmi.ClientLoc) if any(word in n for word in ['nmea','supported','gnss'])],unknown_debug_flag_constructible=int(Qmi.LocNmeaType(0x20000))==0x20000)))
