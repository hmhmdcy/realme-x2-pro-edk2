"""Assemble only terminal, verified HTTP range downloads. No device actions."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, sys

root = Path('/mnt/e/edk2-samurai-out/rx61')
plan = json.loads((root / 'ewdk-download-plan.json').read_text(encoding='utf-8-sig'))
snapshot = Path(sys.argv[1]) if len(sys.argv) == 2 else root / 'download-state-current.json'
assert snapshot.parent.resolve() == root.resolve(), 'Snapshot must stay within RX61 output directory'
state = json.loads(snapshot.read_text(encoding='utf-8-sig'))
stamp = datetime.fromisoformat(state['utc'].replace('Z', '+00:00'))
assert 0 <= (datetime.now(timezone.utc) - stamp).total_seconds() < 120, 'Refresh observer first'
assert state['live_count'] == 0 and state['total_bytes'] == state['expected_iso_bytes']
assert len(state['parts']) == 8 and all(not p['live'] for p in state['parts'])
parts = []
for p in state['parts']:
    assert p['http206'] and p['range_ok'] and p['etag_matches']
    assert p['bytes'] == p['expected'] == 2500317184
    name = f"part-{p['index']:02}.bin"
    file = root / 'ewdk-download' / name
    result = dict(line.split('=', 1) for line in file.with_suffix('.result.txt').read_text().splitlines() if '=' in line)
    assert result['http_code'] == '206' and result['exitcode'] == '0'
    assert int(result['size_download']) == p['expected'] == file.stat().st_size
    parts.append((p['index'], file))
parts.sort()
assert [i for i, _ in parts] == list(range(8))
iso = root / 'EWDK_ge_release_svc_prod1_26100_250904-1728.iso'
temp = iso.with_suffix('.iso.assembling')
assert not iso.exists() and not temp.exists(), 'Existing output requires independent inspection'
digest = hashlib.sha256()
records = []
with temp.open('xb') as out:
    for index, part in parts:
        h = hashlib.sha256()
        with part.open('rb') as stream:
            while block := stream.read(16 * 1024 * 1024):
                out.write(block)
                digest.update(block)
                h.update(block)
        records.append({'index': index, 'bytes': part.stat().st_size, 'sha256': h.hexdigest()})
    out.flush()
    os.fsync(out.fileno())
assert temp.stat().st_size == 20002537472
temp.rename(iso)
report = {'utc': datetime.now(timezone.utc).isoformat(), 'iso': str(iso),
          'bytes': iso.stat().st_size, 'sha256': digest.hexdigest(), 'parts': records,
          'transport_validation': 'Microsoft HTTPS; eight exact 206 ranges; same HEAD ETag; terminal curl exit 0',
          'official_sha256_available': False,
          'note': 'ETag is an opaque HTTP validator, not assumed to be an official SHA256.',
          'device_io': False, 'installed': False}
(root / 'ewdk-assembly.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
