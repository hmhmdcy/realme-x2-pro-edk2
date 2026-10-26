"""Cache only small, public upstream sources. Never accesses the phone/SDK."""
from pathlib import Path
import concurrent.futures
import hashlib
import json
import urllib.request

ROOT = Path(__file__).resolve().parent
SOURCES = {
    'phosh-battery-info.c': 'https://raw.githubusercontent.com/PhoshMobi/phosh/a3cded46d6c6ad8f51678834cd17e95967cc0702/src/battery-info.c',
    'phosh-battery-manager.c': 'https://raw.githubusercontent.com/PhoshMobi/phosh/a3cded46d6c6ad8f51678834cd17e95967cc0702/src/battery-manager.c',
    'upower-up-backend.c': 'https://gitlab.freedesktop.org/api/v4/projects/upower%2Fupower/repository/files/src%2Flinux%2Fup-backend.c/raw?ref=v1.91.0',
    'upower-up-device-supply.c': 'https://gitlab.freedesktop.org/api/v4/projects/upower%2Fupower/repository/files/src%2Flinux%2Fup-device-supply.c/raw?ref=v1.91.0',
    'upower-up-device-supply-battery.c': 'https://gitlab.freedesktop.org/api/v4/projects/upower%2Fupower/repository/files/src%2Flinux%2Fup-device-supply-battery.c/raw?ref=v1.91.0',
    'upower-up-enumerator-udev.c': 'https://gitlab.freedesktop.org/api/v4/projects/upower%2Fupower/repository/files/src%2Flinux%2Fup-enumerator-udev.c/raw?ref=v1.91.0',
    'upower-up-device.c': 'https://gitlab.freedesktop.org/api/v4/projects/upower%2Fupower/repository/files/src%2Fup-device.c/raw?ref=v1.91.0',
    'upower-up-device-battery.c': 'https://gitlab.freedesktop.org/api/v4/projects/upower%2Fupower/repository/files/src%2Fup-device-battery.c/raw?ref=v1.91.0',
    'upower-up-daemon.c': 'https://gitlab.freedesktop.org/api/v4/projects/upower%2Fupower/repository/files/src%2Fup-daemon.c/raw?ref=v1.91.0',
}


def fetch(item):
    name, url = item
    result = {'requested_url': url}
    try:
        previous = ROOT / 'upstream-sources.json'
        if previous.exists() and (ROOT / name).exists():
            prior = json.loads(previous.read_text()).get(name, {})
            if prior.get('requested_url') == url and prior.get('sha256') == hashlib.sha256((ROOT / name).read_bytes()).hexdigest():
                return name, prior
        request = urllib.request.Request(url)
        with urllib.request.urlopen(request, timeout=25) as response:
            data = response.read(400000)
            result.update(final_url=response.url, bytes=len(data))
        assert b'<!doctype html' not in data.lower()[:1000], 'server returned an HTML challenge'
        assert len(data) > 1000, 'short source response'
        (ROOT / name).write_bytes(data)
        result.update(sha256=hashlib.sha256(data).hexdigest(), cached=True)
    except Exception as error:
        result.update(cached=False, error=str(error))
    return name, result


if __name__ == '__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        result = dict(executor.map(fetch, SOURCES.items()))
    (ROOT / 'upstream-sources.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
