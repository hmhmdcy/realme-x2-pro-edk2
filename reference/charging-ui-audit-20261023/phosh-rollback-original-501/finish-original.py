"""Verify cached original splits with the original root-only apk binary."""
from pathlib import Path
import hashlib
import json
import runpy
import subprocess
import tarfile
import urllib.request

HERE = Path(__file__).resolve().parent
ns = runpy.run_path(str(HERE / 'fetch-original.py'))
PRIVATE, APK, KEYS = (ns[k] for k in ('PRIVATE', 'APK', 'KEYS'))
fields, sha = ns['fields'], ns['sha']
expected = json.loads(ns['SOURCE'].read_bytes())
db = json.loads(ns['POSTBOOT'].read_bytes())['raw']['package_db']
installed = {p['P']: p for p in map(fields, db.split('\n\n')) if p.get('o') == 'phosh'}
history = HERE / 'initial-fetch-result.json'
if not history.exists():
    history.write_bytes((HERE / 'result.json').read_bytes())

# Only the missing noarch split is searched; the other three HTTP payloads
# are reused byte-for-byte. An unavailable schema never becomes a fake APK.
schema = PRIVATE / 'phosh-schemas-0.57.0-r3.apk'
attempts = []
if not schema.exists():
    for repo_arch in ('edge/community/x86_64', 'v3.24/community/aarch64'):
        url = 'https://dl-cdn.alpinelinux.org/alpine/' + repo_arch + '/' + schema.name
        row = {'url': url}
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                raw = response.read(16384)
            candidate = PRIVATE / ('schema-' + repo_arch.replace('/', '-') + '.apk')
            candidate.write_bytes(raw)
            row.update(path=candidate.name, sha256=sha(raw), bytes=len(raw))
            candidates = [candidate]
        except Exception as error:
            row['error'] = repr(error)
            candidates = []
        attempts.append(row)
        if candidates:
            break
else:
    candidates = [schema]

rows = []
paths = [PRIVATE / (name + '-0.57.0-r3.apk')
         for name in ('libphosh', 'phosh', 'phosh-portalsconf')] + candidates
for path in paths:
    row = {'filename': path.name, 'bytes': path.stat().st_size, 'sha256': sha(path.read_bytes())}
    v = subprocess.run([str(APK), '--keys-dir', str(KEYS), 'verify', str(path)], capture_output=True)
    (PRIVATE / (path.stem + '-verify.log')).write_bytes(v.stdout + v.stderr)
    row['signature_rc'] = v.returncode
    if v.returncode:
        raise RuntimeError(('signature', path.name, v.returncode))
    index = PRIVATE / (path.stem + '-index.tar.gz')
    q = subprocess.run([str(APK), '--keys-dir', str(KEYS), 'index', '--rewrite-arch', 'aarch64',
                        '--output', str(index), str(path)], capture_output=True)
    (PRIVATE / (path.stem + '-index.log')).write_bytes(q.stdout + q.stderr)
    if q.returncode:
        raise RuntimeError(('index', path.name, q.returncode))
    with tarfile.open(index, 'r:gz') as archive:
        actual = fields(archive.extractfile('APKINDEX').read().decode())
    pkg = installed[actual['P']]
    for key in ('P', 'V', 'A', 'C', 'c'):
        if actual.get(key) != pkg.get(key):
            raise RuntimeError(('original identity mismatch', actual['P'], key))
    for key in ('D', 'p'):
        if set(actual.get(key, '').split()) != set((pkg.get(key) or '').split()):
            raise RuntimeError(('original dependency mismatch', actual['P'], key))
    row.update(P=actual['P'], V=actual['V'], C=actual['C'], signature_and_identity_passed=True)
    rows.append(row)
result = {'scope': 'cached original Phosh rollback APKs; no phone/build-copy mutations',
          'packages': rows, 'schema_fetch_attempts': attempts,
          'three_runtime_splits_ready': {'libphosh', 'phosh', 'phosh-portalsconf'} <= {r['P'] for r in rows},
          'schema_ready': 'phosh-schemas' in {r['P'] for r in rows},
          'original_index_sha256': sha(ns['SOURCE'].read_bytes()),
          'program_sha256': sha(Path(__file__).read_bytes()),
          'initial_failure_preserved': history.name}
(HERE / 'verified-result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
