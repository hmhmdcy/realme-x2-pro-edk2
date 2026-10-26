from pathlib import Path
import gi, json
assert Path('/proc/sys/kernel/random/boot_id').read_bytes() == Path('/var/lib/samurai/k205r2-runtime/boot-id-private.txt').read_bytes()
gi.require_version('Qmi', '1.0')
from gi.repository import Qmi
names = ['get_selected_config', 'get_selected_config_finish', 'list_configs', 'list_configs_finish']
report = {n: getattr(Qmi.ClientPdc, n).__doc__ if hasattr(Qmi.ClientPdc, n) else None for n in names}
for type_name in ['MessagePdcGetSelectedConfigInput', 'MessagePdcGetSelectedConfigOutput', 'IndicationPdcGetSelectedConfigOutput', 'PdcConfigurationType']:
    typ = getattr(Qmi, type_name, None)
    report[type_name] = {n: getattr(typ, n).__doc__ for n in dir(typ) if n.startswith(('get_', 'set_'))} if typ else None
print(json.dumps(report))
