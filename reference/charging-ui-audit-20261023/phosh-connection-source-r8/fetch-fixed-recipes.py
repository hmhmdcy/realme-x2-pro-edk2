"""Fetch only installed-commit packaging inputs; never build or run their content."""
from pathlib import Path
import hashlib
import json
import urllib.error
import urllib.request

HERE = Path(__file__).resolve().parent
PINS = {
    'phosh': ('97dba23dc382440e73c3813c9072a25099fb0d67', '0.57.0', '3'),
    'upower': ('ab329cc95719eba4b967c403f5e2e034184a37d1', '1.91.0', '2'),
}


def main():
    receipt = {'scope': 'fixed installed APK c: commits, primary Alpine repositories only', 'files': {}, 'attempts': []}
    for package, (commit, version, release) in PINS.items():
        path = f'community/{package}/APKBUILD'
        target = HERE / f'{package}-APKBUILD'
        if target.exists():
            raise RuntimeError(f'refuse overwrite {target.name}')
        urls = [
            f'https://gitlab.alpinelinux.org/alpine/aports/-/raw/{commit}/{path}',
            f'https://git.alpinelinux.org/aports/plain/{path}?id={commit}',
            f'https://raw.githubusercontent.com/alpinelinux/aports/{commit}/{path}',
        ]
        for url in urls:
            try:
                with urllib.request.urlopen(url, timeout=20) as response:
                    raw = response.read(512 * 1024 + 1)
                    final = response.url
                if len(raw) > 512 * 1024 or f'pkgver={version}'.encode() not in raw or f'pkgrel={release}'.encode() not in raw:
                    raise ValueError('response is not the exact expected recipe')
                target.write_bytes(raw)
                receipt['files'][target.name] = {'url': url, 'final_url': final, 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw), 'installed_c': commit, 'pkgver': version, 'pkgrel': release}
                receipt['attempts'].append({'url': url, 'accepted': True})
                break
            except Exception as error:
                receipt['attempts'].append({'url': url, 'accepted': False, 'error': f'{type(error).__name__}: {error}'})
        else:
            (HERE / 'recipe-fetch-result.json').write_text(json.dumps(receipt, indent=2)+'\n')
            raise RuntimeError(f'no exact recipe obtained for {package}')
    receipt['passed'] = True
    (HERE / 'recipe-fetch-result.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
