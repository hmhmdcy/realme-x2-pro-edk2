"""Freeze newly verified primary sources; no downloaded code is executed."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import datetime
import hashlib
import json
import urllib.request

R = Path(__file__).resolve().parent
P = Path('/mnt/e/edk2-samurai-out/kernel239/related-linux-sources-private')
P.mkdir(parents=True, exist_ok=True)
linux = 'https://raw.githubusercontent.com/torvalds/linux/2f2f7eeef8b0a1a9b9ca998231419873ccae8d4e/'
sources = {
    'upstream-s5k3m5': linux + 'drivers/media/i2c/s5k3m5.c',
    'upstream-imx471': linux + 'drivers/media/i2c/imx471.c',
    'upstream-imx319': linux + 'drivers/media/i2c/imx319.c',
    'upstream-ov02a10': linux + 'drivers/media/i2c/ov02a10.c',
    'upstream-s5k3m5-introduction': 'https://api.github.com/repos/torvalds/linux/commits/7d402666094ce25d2b52da679b8d7210cde01a34',
    'upstream-imx471-introduction': 'https://api.github.com/repos/torvalds/linux/commits/be1589e567aeea5d32d9dd7027501657787d3ad3',
    'upstream-imx471-cci-fix': 'https://api.github.com/repos/torvalds/linux/commits/b272a1780e8515617fed2564edccb8da8431d707',
    'upstream-ov02a10-endpoint-fix': 'https://api.github.com/repos/torvalds/linux/commits/94971ba0592ca77ec99b292226a4b398763315b8',
    'realme-x3-dts': 'https://raw.githubusercontent.com/sm8150-linux-mainline/linux/91911e069acbb9d38e5dcc633d454f7b1ff9bc4b/arch/arm64/boot/dts/qcom/sm8150-realme-x3.dts',
    'samurai-halium-manifest': 'https://raw.githubusercontent.com/FusinX/android_device_realme_samurai/c64691bf3a15a7048fb3a8aa1cd3d284a7fb6db4/manifest.xml',
    'oppo-oem-camera-dts': 'https://raw.githubusercontent.com/oppo-source/Reno10X-RenoAce-10.0-kernel-source/289d6118ef783a281a8ecf0378e3c560ff6976c4/msm-4.14/arch/arm64/boot/dts/19081/sm8150-camera-sensor-mtp.dtsi',
    'samurai-halium-status': 'https://api.github.com/repos/Halium/projectmanagement/issues/324',
    'mm-supl-fix': 'https://chromium.googlesource.com/external/gitlab.freedesktop.org/mobile-broadband/ModemManager/+/f51cc9488b94a53f411149b7cb5380c5839c3a27?format=JSON',
    'hotdog-head': 'https://api.github.com/repos/Sr-0w/hotdog-linux-bringup/commits/main',
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
            assert target.read_bytes() == data, 'source changed within review'
        else:
            target.write_bytes(data)
        return name, dict(url=url, final_url=final_url, fetched=True, bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    except Exception as error:
        return name, dict(url=url, fetched=False, error_type=type(error).__name__)


with ThreadPoolExecutor(max_workers=6) as pool:
    results = dict(pool.map(fetch, sources.items()))
report = dict(stage=239, retrieved_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              public_primary_sources_only=True, no_phone_operation=True, results=results,
              previous_hotdog_duo_geoclue_gnss_share_sources='reference/kernel238/related-linux-source-validation.json')
(P / 'manifest-private.json').write_text(json.dumps(report, indent=2) + '\n')
(R / 'related-linux-source-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({name: {'fetched': value['fetched'], 'bytes': value.get('bytes'), 'error_type': value.get('error_type')} for name, value in results.items()}))
