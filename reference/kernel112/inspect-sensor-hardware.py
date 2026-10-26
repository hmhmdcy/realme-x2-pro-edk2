"""Read only bus/power properties, never expose sensor factory calibration."""
from pathlib import Path
import json

src = Path('/mnt/e/edk2-samurai-out/kernel111/source-files/k111-sensor-sources-readonly')
registry = src / 'sensors-persist/registry/registry'
allowed = {'bus_type', 'bus_instance', 'slave_config', 'min_bus_speed_khz', 'max_bus_speed_khz',
           'dri_irq_num', 'irq_num', 'irq_pull_type', 'irq_drive_strength', 'irq_trigger_type',
           'is_chip_pin', 'num_rail', 'rail_on_state', 'vddio_rail', 'vdd_rail', 'rigid_body_type'}
results = {}
def walk(obj, found):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in allowed:
                found[key] = value.get('data', value) if isinstance(value, dict) else value
            elif key == 'name' and value in allowed:
                found[value] = {k:v for k,v in obj.items() if k in ('data', 'str', 'flt', 'sint')}
            walk(value, found)
    elif isinstance(obj, list):
        for value in obj: walk(value, found)

for path in sorted(registry.glob('*_platform.config')):
    if not any(s in path.name for s in ['lsm6', 'mmc', 'stk', 'alsps']): continue
    data = json.loads(path.read_text())
    found = {}; walk(data, found)
    results[path.name] = found or {'top_keys_only':list(data)[:8]}
out = Path('/mnt/e/edk2-samurai-out/kernel112/sensor-hardware-properties.json')
out.write_text(json.dumps(results, indent=2)+'\n')
print(json.dumps(results))
