#!/usr/bin/env python3
"""Check that every local installed-file hash matches the package manifest."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

MAPPING = {
    '/etc/init.d/samurai-charging': ROOT / 'service/samurai-charging',
    '/usr/sbin/samurai-charging': ROOT / 'service/samurai-charging-runtime.py',
    '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/'
    'samurai-mp2650.ko': ROOT / 'artifacts/samurai-mp2650-deferred.ko',
    '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/'
    'samurai-usb-input.ko': ROOT / 'artifacts/samurai-usb-input.ko',
    '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/'
    'samurai-gauge-protection.ko':
        ROOT / 'artifacts/samurai-gauge-protection.ko',
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    installed = manifest['installed_files']
    assert set(installed) == set(MAPPING), (
        set(installed) - set(MAPPING), set(MAPPING) - set(installed))
    for target, source in MAPPING.items():
        actual = digest(source)
        assert actual == installed[target], (target, actual, installed[target])
    print(f'package_hashes_ok={len(MAPPING)}')


if __name__ == '__main__':
    main()
