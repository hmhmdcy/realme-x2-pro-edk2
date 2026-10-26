from pathlib import Path
import host, json, re
out = host.PRIVATE / 'bootstrap'; out.mkdir(mode=0o700)
for name in ['tftp.log-private', 'mcfg-tftp-lines-private.txt', 'cache-file-manifest-private.json']:
    host.download('/var/lib/samurai/k207-bootstrap-inspection/' + name, out / name)
text = (out / 'tftp.log-private').read_text(errors='replace')
lines = [line for line in text.splitlines() if any(word in line for word in ['request for', 'WRQ options', 'opened for writing', 'Remote returned', 'Expected DATA', 'out of sequence', 'unable to open', 'failed to write'])]
# Only packet metadata/path lines; raw packet payloads and cache contents stay private.
for line in lines:
    assert not re.search(r'\b(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}\b', line)
    print(line)
manifest = json.loads((out / 'cache-file-manifest-private.json').read_text())
print(json.dumps(dict(cache_bytes={name: manifest[name]['bytes'] for name in ['mcfg.tmp', 'server_check.txt'] if name in manifest})))
