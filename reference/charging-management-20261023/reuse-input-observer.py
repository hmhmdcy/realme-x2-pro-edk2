"""Copy the existing stage134 read-only source observer, preserving provenance."""
from pathlib import Path
import hashlib
import json
import shutil

ref = Path(__file__).resolve().parent
report = {}
for name in ['samurai-usb-input.c', 'samurai-usb-input-decode.h']:
    src = ref.parent / 'kernel134' / name
    if (ref / name).exists():
        # V2 extends the retained baseline. Never overwrite those changes.
        continue
    shutil.copy2(src, ref / name)
    report[name] = {'from': 'reference/kernel134/' + name,
                    'sha256': hashlib.sha256(src.read_bytes()).hexdigest(),
                    'unchanged': True}
(ref / 'input-observer-provenance.json').write_text(json.dumps(report, indent=2) + '\n')
