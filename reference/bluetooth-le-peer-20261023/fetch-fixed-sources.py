"""Retrieve only the six fixed BlueZ 5.87 primary references for this test."""
from pathlib import Path
import hashlib
import json
import urllib.request

COMMIT = '65d11edee469c24dcc8d075b8be9c040cebaaf98'
FILES = ['test/example-gatt-server', 'test/example-advertisement',
         'doc/org.bluez.GattCharacteristic.rst', 'doc/org.bluez.GattManager.rst',
         'doc/org.bluez.LEAdvertisement.rst', 'doc/org.bluez.LEAdvertisingManager.rst']
root = Path(__file__).parent / 'bluez-5.87-reference'
root.mkdir(exist_ok=True)
manifest_path = root / 'manifest.json'
expected = {r['source_path']: r for r in json.loads(manifest_path.read_text())} if manifest_path.exists() else {}
records = []
for source in FILES:
    url = 'https://raw.githubusercontent.com/bluez/bluez/' + COMMIT + '/' + source
    target = root / source.replace('/', '__')
    data = target.read_bytes() if target.exists() else urllib.request.urlopen(url, timeout=20).read()
    digest = hashlib.sha256(data).hexdigest()
    if source in expected:
        assert expected[source]['sha256'] == digest
    if not target.exists():
        target.write_bytes(data)
    records.append(dict(source_path=source, file=target.name, commit=COMMIT, url=url,
                        size=len(data), sha256=digest))
manifest_path.write_text(json.dumps(records, indent=2) + '\n')
print(json.dumps(dict(fixed_commit=COMMIT, references=len(records), downloaded_or_verified=True)))
