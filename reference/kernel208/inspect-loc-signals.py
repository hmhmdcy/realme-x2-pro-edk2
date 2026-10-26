from pathlib import Path
import gi,json
gi.require_version('Qmi','1.0')
from gi.repository import Qmi,GObject
root=Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k208-baseline/boot-id-private.txt').read_bytes()
GObject.type_class_ref(Qmi.ClientLoc.__gtype__)
print(json.dumps(dict(signals=GObject.signal_list_names(Qmi.ClientLoc.__gtype__),engine_indication_types=[name for name in dir(Qmi) if name.startswith('IndicationLoc') and any(word in name for word in ['State','Nmea'])])))
