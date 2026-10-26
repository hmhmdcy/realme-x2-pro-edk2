"""Read only specific USB files via the existing storage mount, PC-only."""
from pathlib import Path
import hashlib
import json
import sys
sys.path.insert(0, '/mnt/e/RealmeX2Pro edk2/reference/kernel284')
import storage
build = storage.mounted_build()
source = build.parent / 'source354'
root = Path(__file__).resolve().parent
files = ('drivers/usb/dwc3/dwc3-qcom-legacy.c', 'drivers/usb/dwc3/core.c',
         'drivers/usb/dwc3/gadget.c', 'drivers/usb/dwc3/core.h',
         'drivers/usb/gadget/udc/core.c', 'drivers/usb/dwc3/debugfs.c',
         'drivers/usb/dwc3/trace.h')
result = {}
for name in files:
    data = (source / name).read_bytes()
    assert len(data) < 400000
    (root / name.replace('/', '--')).write_bytes(data)
    result[name] = {'path': str(source / name), 'bytes': len(data),
                    'sha256': hashlib.sha256(data).hexdigest()}
(root / 'source-manifest.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
