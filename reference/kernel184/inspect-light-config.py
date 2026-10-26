"""Report only interface selectors and calibration equality, not calibration data."""
from pathlib import Path
import hashlib
import json

source = Path('/var/lib/samurai/k111-sensor-sources-readonly')
ram = Path('/run/samurai-sensors-ram-k184-light-v1/sensors')
found = []


def visit(value, path, file):
    if isinstance(value, dict):
        for key, child in value.items():
            if key == 'als_type':
                found.append({'file': file, 'json_path': path + '/' + key, 'selector': child})
            visit(child, path + '/' + key, file)
    elif isinstance(value, list):
        for i, child in enumerate(value):
            visit(child, path + '/' + str(i), file)


for p in (source / 'sensors-vendor/config').glob('*.json'):
    raw = p.read_text()
    if 'als_type' in raw:
        visit(json.loads(raw, strict=False), '', p.name)
cal = []
for p in (source / 'sensors-persist/registry').rglob('*'):
    if not p.is_file():
        continue
    raw = p.read_text(errors='replace')
    if 'als_type' in raw:
        visit(json.loads(raw, strict=False), '', str(p.relative_to(source)))
    if any(t in p.name for t in ['fac_cal', 'calibration']):
        target = ram / 'registry' / p.relative_to(source / 'sensors-persist/registry')
        cal.append({'name': p.name, 'ram_exists': target.exists(),
                    'byte_identical': target.exists() and p.read_bytes() == target.read_bytes()})
print(json.dumps({'selectors': found, 'calibration_files': len(cal),
                  'calibration_preserved_count': sum(c['byte_identical'] for c in cal),
                  'light_calibration_files': [c for c in cal if any(t in c['name'] for t in ['als', 'stk'])]}))
