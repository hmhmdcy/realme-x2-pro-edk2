from pathlib import Path
import base64, gzip, hashlib, json, re, sys

root = Path('/mnt/e/edk2-samurai-out/kernel67')
name, marker, output = sys.argv[1:4]
text = (root / (name+'.txt')).read_bytes().decode('ascii').replace('\r', '')
start = re.search(rf'(?m)^{marker}B$', text)
assert start, 'Export start marker not present'
end_match = re.search(rf'(?m)^{marker}E$', text[start.end():])
assert end_match, 'Export end marker not present after start'
end_pos = start.end()+end_match.start()
lines = text[start.end():end_pos].strip().splitlines()
expected = lines[0].split()[0]
assert re.fullmatch('[0-9a-f]{64}', expected)
data = base64.b64decode(''.join(lines[1:]), validate=True)
digest = hashlib.sha256(data).hexdigest()
assert digest == expected, f'SHA mismatch: {digest} != {expected}; bytes {len(data)}'
compressed = data[:2] == b'\x1f\x8b'
body = gzip.decompress(data) if compressed else data
(root / (output+'-received'+('.gz' if compressed else '.bin'))).write_bytes(data)
(root / (output+'.validated.txt')).write_bytes(body)
info = dict(name=output, bytes=len(data), device_sha256=expected, sha256_pass=True,
            gzip_crc_pass=compressed, plain_bytes=len(body))
(root / (output+'-validation.json')).write_text(json.dumps(info, indent=2)+'\n')
print(json.dumps(info))
if len(body) < 5000:
    try:
        print(body.decode())
    except UnicodeDecodeError:
        pass
