"""Root-only known storage mount reuse; read only targeted PM/console sources."""
from pathlib import Path
import hashlib
import json
import sys

sys.path.insert(0, '/mnt/e/RealmeX2Pro edk2/reference/kernel284')
import storage
shared = storage.mounted_build()
source = shared.parent / 'source354'
root = Path(__file__).resolve().parent
names = tuple(sys.argv[1:]) if len(sys.argv) > 1 else ('kernel/power/suspend.c', 'kernel/power/console.c', 'kernel/power/process.c',
         'kernel/printk/printk.c', 'drivers/tty/vt/vt.c', 'drivers/base/power/main.c',
         'drivers/base/power/wakeup.c')
manifest = root / 'source-manifest.json'
report = json.loads(manifest.read_text()) if manifest.exists() else {}
for name in names:
    p = source / name
    if not p.exists():
        report[name] = {'source': str(p), 'exists': False}
        continue
    data = p.read_bytes()
    assert len(data) < 400000, 'Keep this audit targeted'
    out = root / name.replace('/', '--')
    out.write_bytes(data)
    report[name] = {'source': str(p), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
manifest.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({name: report[name] for name in names}, indent=2))
