"""Cache only the four installed original Phosh splits; no installation."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib
import json
import os
import subprocess
import tarfile
import urllib.error
import urllib.request

HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/charging-ui-audit-20261023/phosh-original-rollback-501')
SOURCE = HERE.parent.parent / 'charging-oem-audit-20261023/phosh-private-build-inputs-501-r1/original-split-index.json'
APK = Path('/home/cy122/pmos-samurai-rootfs01/work/apk.static')
KEYS = Path('/home/cy122/pmos-samurai-rootfs01/work/config_apk_keys')
POSTBOOT = Path('/mnt/e/edk2-samurai-out/charging-management-20261023/image501-activation/image501-gauge-live-001/postboot-r1-04-private/stdout-private.json')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fields(block):
    return dict(line.split(':', 1) for line in block.splitlines() if ':' in line)


def main():
    os.umask(0o077)
    if PRIVATE.exists() and any(PRIVATE.iterdir()):
        raise RuntimeError('refusing an existing nonempty download directory')
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    original = json.loads(SOURCE.read_bytes())
    db = json.loads(POSTBOOT.read_bytes())['raw']['package_db']
    installed = {p['P']: p for p in map(fields, db.split('\n\n')) if p.get('o') == 'phosh'}
    if set(installed) != {'phosh', 'libphosh', 'phosh-schemas', 'phosh-portalsconf'}:
        raise RuntimeError('installed Phosh split set changed')
    for name, pkg in installed.items():
        for key in ('P', 'V', 'A', 'C', 'c'):
            if pkg.get(key) != original[name].get(key):
                raise RuntimeError(('actual/frozen package mismatch', name, key))

    def fetch(name):
        expected = installed[name]
        url = ('https://dl-cdn.alpinelinux.org/alpine/edge/community/aarch64/'
               + name + '-' + expected['V'] + '.apk')
        row = {'name': name, 'url': url, 'expected_C': expected['C']}
        try:
            with urllib.request.urlopen(url, timeout=35) as response:
                if response.url != url:
                    raise RuntimeError(('unexpected redirect', response.url))
                raw = response.read(int(expected['S']) + 1)
            path = PRIVATE / (name + '-' + expected['V'] + '.apk')
            path.write_bytes(raw)
            row.update(bytes=len(raw), sha256=sha(raw))
            verify = subprocess.run([str(APK), '--keys-dir', str(KEYS), 'verify', str(path)],
                                    capture_output=True, timeout=30)
            (PRIVATE / (name + '-verify.log')).write_bytes(verify.stdout + verify.stderr)
            row['verify_returncode'] = verify.returncode
            if verify.returncode:
                raise RuntimeError('original signature verification failed')
            index = PRIVATE / (name + '-index.tar.gz')
            indexed = subprocess.run([str(APK), '--keys-dir', str(KEYS), 'index',
                                      '--rewrite-arch', 'aarch64', '--output', str(index), str(path)],
                                     capture_output=True, timeout=30)
            (PRIVATE / (name + '-index.log')).write_bytes(indexed.stdout + indexed.stderr)
            if indexed.returncode:
                raise RuntimeError(('index failed', indexed.returncode))
            with tarfile.open(index, mode='r:gz') as archive:
                actual = fields(archive.extractfile('APKINDEX').read().decode())
            for key in ('P', 'V', 'A', 'C', 'c', 'S'):
                if actual.get(key) != expected.get(key):
                    raise RuntimeError(('original identity mismatch', key, actual.get(key), expected.get(key)))
            for key in ('D', 'p'):
                if set(actual.get(key, '').split()) != set(expected.get(key, '').split()):
                    raise RuntimeError(('original metadata mismatch', key))
            row.update(accepted=True, original_signature_and_actual_installed_identity=True)
        except Exception as error:
            row.update(accepted=False, error=repr(error))
        return row

    with ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(fetch, sorted(installed)))
    result = {'scope': 'original four actually installed Phosh split rollback payloads only',
              'passed': all(row['accepted'] for row in rows), 'packages': rows,
              'source_sha256': sha(Path(__file__).read_bytes()),
              'phone_or_build_copy_changed': False}
    (HERE / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
