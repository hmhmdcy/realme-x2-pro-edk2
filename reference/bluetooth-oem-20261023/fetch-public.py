"""Fetch only the fixed public OEM files declared in the saved manifest.

Existing files are verified and reused. No ROM or proprietary HAL is fetched.
"""
from pathlib import Path
import hashlib
import json
import urllib.request

root = Path(__file__).parent / 'public-sources'
manifest = json.loads((root / 'manifest.json').read_text())
for item in manifest:
    name = item['file']
    assert Path(name).name == name
    url = item['url']
    assert url.startswith('https://raw.githubusercontent.com/realme-kernel-opensource/')
    assert '/23172a1571bd91156032cc9fef16284a82b63d2c/' in url
    target = root / name
    data = target.read_bytes() if target.exists() else urllib.request.urlopen(url, timeout=30).read()
    assert len(data) == item['size'], name
    assert hashlib.sha256(data).hexdigest() == item['sha256'], name
    if not target.exists():
        target.write_bytes(data)
    print(name, item['sha256'])
