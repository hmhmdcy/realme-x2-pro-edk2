"""Fetch the device-selected official APK URLs on the host; verify on device later."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import subprocess
import urllib.parse
import host

folder = host.PRIVATE / 'deps-apks-private'
folder.mkdir(exist_ok=True)
result = host.ssh('apk list glib-dev libqmi-dev libqrtr-glib-dev libmbim-dev protobuf-c-dev protobuf-c-compiler python3-dev pcre2-dev libffi-dev zlib-dev util-linux-dev', timeout=15)
(folder / 'urls-private.txt').write_bytes(result.stdout + result.stderr)
names = [s.split()[0] + '.apk' for s in result.stdout.decode().splitlines() if ' aarch64 ' in s]
assert len(names) == 11


def fetch(name):
    target = folder / name
    if not target.exists():
        temp = folder / (name + '.partial')
        windows = 'E:/' + str(temp)[len('/mnt/e/'):]
        attempts = []
        for repository in ['https://mirror.postmarketos.org/postmarketos/main',
                           'https://dl-cdn.alpinelinux.org/alpine/edge/main',
                           'https://dl-cdn.alpinelinux.org/alpine/edge/community']:
            url = repository + '/aarch64/' + name
            p = subprocess.run(['/mnt/c/Windows/System32/curl.exe', '-sS', '-fL',
                                '--connect-timeout', '8', '--max-time', '35',
                                url, '-o', windows], capture_output=True, timeout=45)
            attempts.append({'url': url, 'exit_code': p.returncode})
            (folder / (name + '-fetch-private.log')).write_bytes(p.stdout + p.stderr)
            if p.returncode == 0:
                temp.rename(target)
                break
        else:
            return {'name': name, 'attempts': attempts, 'downloaded': False}
    return {'name': name, 'downloaded': True, 'bytes': target.stat().st_size}


with ThreadPoolExecutor(max_workers=4) as pool:
    report = list(pool.map(fetch, names))
(folder / 'fetch-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'official_apk_packages': len(names), 'complete': sum(r['downloaded'] for r in report),
                  'device_signature_verification_pending': True}))
if not all(r['downloaded'] for r in report):
    raise SystemExit(1)
