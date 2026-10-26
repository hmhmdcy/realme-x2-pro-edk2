"""Cache an official TI reference manual once for offline protocol review."""
from pathlib import Path
import hashlib
import json
import urllib.request

private = Path('E:/edk2-samurai-out/charging-management-20261023')
private.mkdir(parents=True, exist_ok=True)
old = private / 'charging-management-20261023.tar.gz'
v1 = private / 'charging-management-20261023-v1.tar.gz'
if not v1.exists() and old.exists():
    v1.write_bytes(old.read_bytes())
p = private / 'ti-bq28z610-sluua65.pdf'
url = 'https://www.ti.com/lit/pdf/sluua65'
if not p.exists():
    with urllib.request.urlopen(url, timeout=40) as response:
        data = response.read()
    assert data.startswith(b'%PDF-')
    p.write_bytes(data)
print(json.dumps({'url': url, 'path': str(p), 'bytes': p.stat().st_size,
                  'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}))
