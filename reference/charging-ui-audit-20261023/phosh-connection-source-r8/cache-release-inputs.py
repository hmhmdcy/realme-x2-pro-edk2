"""Cache checksum-pinned release inputs and read selected source members only."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib
import json
import re
import tarfile
import urllib.request

HERE = Path(__file__).resolve().parent
PRIVATE = Path('E:/edk2-samurai-out/charging-ui-audit-20261023/phosh-connection-source-r8')
SPECS = [
    ('phosh', 'phosh-0.57.0.tar.xz', 'https://sources.phosh.mobi/releases/phosh/phosh-0.57.0.tar.xz', True),
    ('phosh', 'splash-timeout-flatpak-dbus.patch', 'https://gitlab.alpinelinux.org/alpine/aports/-/raw/97dba23dc382440e73c3813c9072a25099fb0d67/community/phosh/splash-timeout-flatpak-dbus.patch', False),
    ('upower', 'upower-v1.91.0.tar.bz2', 'https://gitlab.freedesktop.org/upower/upower/-/archive/v1.91.0/upower-v1.91.0.tar.bz2', True),
    ('upower', '0001-fix-self-test-sleep-duration.patch', 'https://gitlab.alpinelinux.org/alpine/aports/-/raw/ab329cc95719eba4b967c403f5e2e034184a37d1/community/upower/0001-fix-self-test-sleep-duration.patch', False),
]
SELECT = {
    'phosh': ['src/battery-manager.c', 'src/battery-manager.h', 'src/battery-info.c', 'src/battery-info.h', 'src/status-icon.c', 'src/status-icon.h', 'src/ui/top-panel.ui', 'src/top-panel.c', 'src/resources.gresource.xml', 'meson.build'],
    'upower': ['libupower-glib/up-client.c', 'libupower-glib/up-client.h', 'libupower-glib/up-device.h', 'src/up-constants.h', 'src/up-daemon.c', 'src/up-device.c', 'src/up-device-battery.c', 'src/linux/up-enumerator-udev.c', 'src/linux/up-device-supply.c', 'src/linux/up-device-supply-battery.c'],
}


def fetch(spec):
    package, name, url, archive = spec
    raw_recipe = (HERE / f'{package}-APKBUILD').read_text()
    expected = re.search(r'^([0-9a-f]{128})  '+re.escape(name)+r'$', raw_recipe, re.M)[1]
    output = (PRIVATE if archive else HERE) / name
    if output.exists():
        raise RuntimeError(f'refuse overwrite {name}')
    with urllib.request.urlopen(url, timeout=30) as response:
        raw = response.read(64*1024*1024+1)
        final = response.url
    if len(raw)>64*1024*1024 or hashlib.sha512(raw).hexdigest() != expected:
        raise ValueError(f'checksum/size mismatch {name}')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(raw)
    return {'name': name, 'package': package, 'url': url, 'final_url': final, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(), 'sha512': expected, 'archive_private': archive}


def main():
    results = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(fetch, spec) for spec in SPECS]
        for spec, future in zip(SPECS, futures):
            try:
                results.append(future.result() | {'passed': True})
            except Exception as error:
                results.append({'name': spec[1], 'passed': False, 'error': f'{type(error).__name__}: {error}'})
    receipt = {'inputs': results, 'selected_files': {}, 'missing_members': [], 'build_executed': False, 'patch_applied': False, 'device_accessed': False}
    for record in results:
        if not record.get('passed') or not record.get('archive_private'):
            continue
        package = record['package']
        with tarfile.open(PRIVATE / record['name'], 'r:*') as archive:
            members = {m.name.split('/', 1)[1]: m for m in archive.getmembers() if '/' in m.name and m.isfile()}
            for name in SELECT[package]:
                if name not in members:
                    receipt['missing_members'].append(f'{package}/{name}')
                    continue
                raw = archive.extractfile(members[name]).read()
                destination = HERE / 'release-files' / package / name
                if destination.exists():
                    raise RuntimeError('refuse overwrite selected source')
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(raw)
                receipt['selected_files'][f'{package}/{name}'] = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw), 'archive': record['name'], 'member': members[name].name}
    receipt['passed'] = all(record.get('passed') for record in results)
    (HERE / 'release-input-result.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
