"""PC-only read of specific current EUD/platform files, plus cached OEM files."""
from pathlib import Path
import gzip
import hashlib
import json
import sys
sys.path.insert(0, '/mnt/e/RealmeX2Pro edk2/reference/kernel284')
import storage
build = storage.mounted_build()
source = build.parent / 'source354'
root = Path(__file__).resolve().parent
report = {}
files = ('drivers/usb/misc/qcom_eud.c',
         'Documentation/devicetree/bindings/usb/qcom,eud.yaml',
         'drivers/usb/gadget/composite.c',
         'arch/arm64/boot/dts/qcom/sm8150-samurai.dts')
for name in files:
    path = source / name
    if not path.exists():
        report[name] = {'exists': False}
        continue
    data = path.read_bytes()
    assert len(data) < 200000
    (root / name.replace('/', '--')).write_bytes(data)
    report[name] = {'source': str(path), 'bytes': len(data),
                    'sha256': hashlib.sha256(data).hexdigest()}
for name in ('stock-eud', 'stock-usb-dts', 'mainline-eud-control'):
    path = Path('/mnt/e/edk2-samurai-out/kernel69') / (name + '.source.gz')
    data = gzip.decompress(path.read_bytes())
    (root / (name + '.c')).write_bytes(data)
    report[name] = {'cached_source': str(path), 'sha256': hashlib.sha256(data).hexdigest()}
(root / 'platform-manifest.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
