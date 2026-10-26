from pathlib import Path
import hashlib, host, json
lock = json.loads((Path(__file__).resolve().parents[2] / 'linux-port/radio/source-lock.json').read_text())
out = host.PRIVATE / 'verified-source-cache'; out.mkdir(mode=0o700)
original = host.PRIVATE.parent / 'kernel88'
for item in lock['source_records']:
    project = item['repo'].split('/')[-1]
    path = original / project / item['path']
    if project == 'tqftpserv' and item['path'] == 'tqftpserv.c': path = path.with_name('tqftpserv.c.before')
    data = path.read_bytes()
    assert len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == item['sha256']
    target = out / project / item['path']; target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
(host.PRIVATE / 'network-build-failure-private.json').write_text(json.dumps(dict(failure='TLS unexpected EOF while reading a pinned public source', failed_directory='tftp-clean-rebuild', recovered_from_hash_verified_prior_downloads=True), indent=2) + '\n')
print('All ten cached public sources verified against the same pinned hashes; failed network build preserved.')
