"""Fetch public primary sources only; never run repository code or touch phone."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import datetime
import hashlib
import json
import urllib.request

R = Path(__file__).resolve().parent
P = Path('/mnt/e/edk2-samurai-out/kernel238/related-linux-sources-private')
P.mkdir(parents=True, exist_ok=True)
hotdog = 'https://raw.githubusercontent.com/Sr-0w/hotdog-linux-bringup/47087509c4289c2580c54f5433e55366b2e00445/'
surya = 'https://raw.githubusercontent.com/woodyst/surya-pmos/d7eadb03f230506140839f18a6c0ef3c43016d7e/'
sources = {
    'hotdog-readme': hotdog + 'README.md',
    'hotdog-camera': hotdog + 'docs/evidence/2026-08-09-mainline616-camera-libcamera.md',
    'hotdog-gnss': hotdog + 'docs/evidence/2026-08-10-gnss-qmi-loc.md',
    'hotdog-status': hotdog + 'docs/status.md',
    'samurai-halium-issue': 'https://api.github.com/repos/Halium/projectmanagement/issues/324',
    'samurai-halium-manifest': 'https://raw.githubusercontent.com/FusinX/samurai.halium10/98de27ba33403851d83ce3ffbf6cdc0f8c419232/Realme_RMX1931.xml',
    'realme-oem-kernel': 'https://api.github.com/repos/realme-kernel-opensource/realmeX2pro-X3-AndroidR-kernel-source',
    'oppo-oem-kernel': 'https://api.github.com/repos/oppo-source/Reno10X-RenoAce-10.0-kernel-source',
    'libcamera-getting-started': 'https://docs.libcamera.org/master/getting-started.html',
    'upstream-imx319': 'https://raw.githubusercontent.com/torvalds/linux/master/drivers/media/i2c/imx319.c',
    'mm-location-api': 'https://www.freedesktop.org/software/ModemManager/api/latest/gdbus-org.freedesktop.ModemManager1.Modem.Location.html',
    'gnss-share-readme': 'https://gitlab.com/postmarketOS/gnss-share/-/raw/master/README.md',
    'gnss-share-modemmanager': 'https://gitlab.com/postmarketOS/gnss-share/-/raw/master/internal/gnss/modemmanager.go',
    'surya-same-cid': surya + 'packages/libqmi/0004-qmicli-loc-combine-loc-start-with-monitoring.patch',
    'surya-gsv': surya + 'packages/modemmanager/0002-shared-qmi-synthesise-missing-gsv-traces.patch',
    'droidian-hybris': 'https://raw.githubusercontent.com/droidian/geoclue/2f578dd7959c153fd085514cdbf20a7c71fb2aaf/src/gclue-hybris-binder.c',
    'duo-gnss-build': 'https://raw.githubusercontent.com/agentsco-lab/surfaceduo-droidian/7cb53ddca60590b1f44c402d1b5bfd333b44fa66/adaptation/package/build.sh',
}


def fetch(item):
    name, url = item
    target = P / (name + '.txt')
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'samurai-linux-primary-source-review'})
        with urllib.request.urlopen(request, timeout=22) as response:
            data = response.read(4 * 1024 * 1024)
            assert not response.read(1), 'source exceeds bound'
            final_url = response.url
        if target.exists():
            assert target.read_bytes() == data, 'public source changed within review; preserve original'
        else:
            target.write_bytes(data)
        return name, dict(url=url, final_url=final_url, fetched=True, bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    except Exception as error:
        return name, dict(url=url, fetched=False, error_type=type(error).__name__, error=str(error)[:160])


with ThreadPoolExecutor(max_workers=6) as pool:
    results = dict(pool.map(fetch, sources.items()))
report = dict(stage=238, retrieved_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              public_primary_sources_only=True, no_phone_operation=True, results=results)
(P / 'manifest-private.json').write_text(json.dumps(report, indent=2) + '\n')
(R / 'related-linux-source-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({name: {'fetched': value['fetched'], 'bytes': value.get('bytes'), 'error_type': value.get('error_type')} for name, value in results.items()}))
