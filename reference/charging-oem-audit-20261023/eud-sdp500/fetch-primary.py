"""Fetch only USB-IF published spec archives; never connect to USB devices."""
from pathlib import Path
import hashlib
import io
import json
import urllib.request
import zipfile

root = Path(__file__).resolve().parent / 'primary'
root.mkdir(exist_ok=True)
files = ('https://www.usb.org/sites/default/files/BCv1.2_070312_0.zip',
         'https://www.usb.org/sites/default/files/usb_20_20250603.zip')
report = []
for url in files:
    path = root / url.rsplit('/', 1)[1]
    if not path.exists():
        with urllib.request.urlopen(url, timeout=45) as response:
            data = response.read(30000000)
        assert len(data) < 30000000
        path.write_bytes(data)
    data = path.read_bytes()
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
    report.append({'url': url, 'file': path.name, 'bytes': len(data),
                   'sha256': hashlib.sha256(data).hexdigest(), 'members': names})
(root / 'archives.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
