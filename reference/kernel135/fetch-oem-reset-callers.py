from pathlib import Path
import hashlib
import json
import urllib.request
out = Path('/mnt/e/edk2-samurai-out/kernel135')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel135')
assert not (ref / 'oem-reset-caller-validation.json').exists()
commit = '9668fcdc6ec15be7a10d66f7b93c347829e0fdb6'
records = []
for name in ['sde_encoder.c', 'sde_hw_catalog.c', 'sde_hw_ctl.h']:
    url = f'https://raw.githubusercontent.com/realme-kernel-opensource/realmeX2Pro-kernel-source/{commit}/drivers/gpu/drm/msm/sde/{name}'
    data = urllib.request.urlopen(url, timeout=30).read()
    p = out / ('oem-' + name)
    assert not p.exists()
    p.write_bytes(data)
    records.append(dict(source=name, url=url, bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))
(ref / 'oem-reset-caller-validation.json').write_text(json.dumps(dict(commit=commit, sources=records,
    phone_unchanged=True, hardware_reset_not_issued=True, display_fix_not_proven=True), indent=2) + '\n')
print('K135_OEM_RESET_CALLERS_AND_CATALOG_FETCHED_FIXED_COMMIT', flush=True)
