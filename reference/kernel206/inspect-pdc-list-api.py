from pathlib import Path
import gi, json
assert Path('/proc/sys/kernel/random/boot_id').read_bytes() == Path('/var/lib/samurai/k205r2-runtime/boot-id-private.txt').read_bytes()
gi.require_version('Qmi', '1.0')
from gi.repository import Qmi
report = {}
for type_name in ['MessagePdcListConfigsInput', 'IndicationPdcListConfigsOutput', 'IndicationPdcListConfigsOutputConfigsElement', 'MessagePdcGetConfigInfoInput', 'IndicationPdcGetConfigInfoOutput']:
    typ = getattr(Qmi, type_name, None)
    report[type_name] = {n: getattr(typ, n).__doc__ for n in dir(typ) if n.startswith(('get_', 'set_')) or n in ['config_type', 'id']} if typ else None
print(json.dumps(report))
