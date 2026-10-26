#!/usr/bin/env python3
"""Fetch upstream benchmark and inspect a private, non-installed native SDK."""
import hashlib
import io
import json
from pathlib import Path
import tarfile
import urllib.request

out = Path('/mnt/e/edk2-samurai-out/kernel131/native-sdk')
out.mkdir(mode=0o700, parents=True, exist_ok=True)
urls = {
    'glmark2-2023.01.tar.gz': 'https://codeload.github.com/glmark2/glmark2/tar.gz/refs/tags/2023.01',
    'APKINDEX.tar.gz': 'https://dl-cdn.alpinelinux.org/alpine/edge/main/aarch64/APKINDEX.tar.gz',
}
receipts = []
for name, url in urls.items():
    path = out / name
    if not path.exists():
        with urllib.request.urlopen(url, timeout=45) as response:
            body = response.read(32 * 1024 * 1024 + 1)
        assert len(body) <= 32 * 1024 * 1024
        path.write_bytes(body)
    body = path.read_bytes()
    receipts.append({'file': name, 'url': url, 'bytes': len(body),
                     'sha256': hashlib.sha256(body).hexdigest()})
with tarfile.open(out / 'APKINDEX.tar.gz') as archive:
    entries = archive.extractfile('APKINDEX').read().decode().split('\n\n')
packages = {}
for entry in entries:
    fields = dict(line.split(':', 1) for line in entry.splitlines() if ':' in line)
    if 'P' in fields:
        packages[fields['P']] = fields
wanted = ['gcc', 'g++', 'binutils', 'musl', 'musl-dev', 'libgcc-static', 'linux-headers',
          'libstdc++-dev', 'gmp', 'mpfr4', 'mpc1', 'isl26', 'isl',
          'zstd-libs', 'libpng-dev', 'libjpeg-turbo-dev', 'wayland-dev',
          'wayland-protocols', 'mesa-dev', 'wayland-tools']
selected = {name: packages[name] for name in wanted if name in packages}
(out / 'source-receipts.json').write_text(json.dumps(receipts, indent=2) + '\n')
(out / 'sdk-index-selected-private.json').write_text(json.dumps(selected, indent=2) + '\n')
for name, fields in selected.items():
    print(name, fields['V'], fields.get('D', ''))
with tarfile.open(out / 'glmark2-2023.01.tar.gz') as archive:
    names = [m.name for m in archive.getmembers() if 'wscript' in m.name or m.name.endswith('meson.build')]
    print('build_files', names)
