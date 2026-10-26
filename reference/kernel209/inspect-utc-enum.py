from pathlib import Path
import gi,json
gi.require_version('Qmi','1.0')
from gi.repository import Qmi
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k209-baseline/boot-id-private.txt').read_bytes()
report=dict(injected_time_sources={name:int(getattr(Qmi.LocInjectedTimeSource,name)) for name in dir(Qmi.LocInjectedTimeSource) if name.isupper()},field_docs={name:str(getattr(Qmi.MessageLocInjectUtcTimeInput,name).__doc__) for name in ['set_time_uncertainty','set_time_source','set_utc_time']})
print(json.dumps(report))
