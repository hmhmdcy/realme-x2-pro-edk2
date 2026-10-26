"""Snapshot the official public HAL for initialization-contract review."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.request import Request, urlopen
import base64, hashlib, json

here = Path(__file__).resolve().parent
out = Path('/mnt/e/edk2-samurai-out/kernel206/hal-sources')
out.mkdir(mode=0o700)
base = 'https://android.googlesource.com/platform/hardware/qcom/sm8150/gps'
def read(url):
    with urlopen(Request(url, headers={'User-Agent': 'samurai-gnss-source-review'}), timeout=40) as response:
        return response.read(3_000_000)
raw = read(base + '/+/refs/heads/main?format=JSON')
(out / 'commit-private.json').write_bytes(raw)
commit = json.loads(raw[4:])['commit']
paths = ['gnss/GnssAdapter.cpp', 'core/ContextBase.cpp', 'core/LocApiBase.h', 'core/LocApiBase.cpp', 'etc/gps.conf', 'utils/loc_cfg.cpp', 'utils/gps_extended_c.h']
def fetch(path):
    url = base + '/+/' + commit + '/' + path + '?format=TEXT'
    try:
        data = base64.b64decode(read(url))
        (out / path.replace('/', '__')).write_bytes(data)
        return path, dict(url=url, sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))
    except Exception as error:
        (out / (path.replace('/', '__') + '.failure.txt')).write_text(type(error).__name__ + ': ' + str(error))
        return path, dict(failed=True, error_type=type(error).__name__)
with ThreadPoolExecutor(max_workers=4) as pool:
    files = dict(pool.map(fetch, paths))
result = dict(stage=206, commit=commit, files=files, remote_code_executed=False)
(here / 'gnss-hal-source-validation.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
