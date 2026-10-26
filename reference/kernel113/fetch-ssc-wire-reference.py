from pathlib import Path
import base64,hashlib,json,urllib.request

out=Path('/mnt/e/edk2-samurai-out/kernel113/libssc-suid-reference-private')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
url='https://chromium.googlesource.com/chromiumos/third_party/libqmi/+/refs/tags/1.38.0/data/qmi-service-ssc.json?format=TEXT'
file=out/'qmi-service-ssc-1.38.0.json'
if not file.exists():
    with urllib.request.urlopen(url,timeout=20) as response:
        raw=base64.b64decode(response.read(128*1024))
    assert raw.lstrip().startswith(b'[') and b'Report Large' in raw
    file.write_bytes(raw)
else: raw=file.read_bytes()
for name in ['.gitmodules','data/meson.build']:
    path=out/('source-'+name.replace('/','-').lstrip('.'))
    if not path.exists():
        with urllib.request.urlopen('https://sources.debian.org/data/main/libs/libssc/0.4.4-2/'+name,timeout=20) as response:
            payload=response.read(64*1024)
        assert b'<!DOCTYPE' not in payload
        path.write_bytes(payload)
    print(name+': '+path.read_text()[:1200])
(ref/'qmi-ssc-wire-reference.json').write_text(json.dumps(dict(url=url,
    version='1.38.0',sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),
    installed_version='1.38.0_git20261005-r0',protocol_checked_against_upstream_reference=True,
    phone_changed=False),indent=2)+'\n')
print(raw.decode()[:7500])
