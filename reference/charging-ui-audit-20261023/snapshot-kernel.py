"""Read existing kernel sources into this audit directory, without edits."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'kernel284'))
import storage

source = storage.mounted_build().parent / 'source354'
names = ['bq27xxx_battery.c', 'power_supply_core.c']
result = {}
for name in names:
    original = source / 'drivers/power/supply' / name
    data = original.read_bytes()
    (ROOT / ('kernel-' + name)).write_bytes(data)
    result[name] = {'source': str(original), 'sha256': hashlib.sha256(data).hexdigest()}
(ROOT / 'kernel-sources.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
