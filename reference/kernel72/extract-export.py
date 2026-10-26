"""Verify a device-saved EUD export; never repair missing data."""
from pathlib import Path
import base64
import gzip
import hashlib
import json
import re
import sys

root, capture, marker, output, plain_size = sys.argv[1:]
root = Path(root)
text = (root / (capture + '.txt')).read_bytes().decode('ascii').replace('\r', '')
match = re.search(rf'(?m)^{re.escape(marker)}B\n(.*?)\n{re.escape(marker)}E$', text, re.S)
assert match, 'Missing complete export markers'
lines = match[1].splitlines()
expected = lines[0].split()[0]
assert re.fullmatch('[0-9a-f]{64}', expected), 'Invalid device SHA256'
data = base64.b64decode(''.join(lines[1:]), validate=True)
assert hashlib.sha256(data).hexdigest() == expected, 'Device SHA256 mismatch'
body = gzip.decompress(data)
assert len(body) == int(plain_size), 'Device plain length mismatch'
(root / (output + '-received.gz')).write_bytes(data)
(root / (output + '.validated.txt')).write_bytes(body)
report = dict(bytes=len(data), plain_bytes=len(body), device_sha256=expected,
              plain_sha256=hashlib.sha256(body).hexdigest(), sha256_pass=True,
              gzip_crc_pass=True, length_pass=True)
(root / (output + '-validation.json')).write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
