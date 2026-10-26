from pathlib import Path
import hashlib,json,urllib.request

out=Path('/mnt/e/edk2-samurai-out/kernel113/libssc-suid-reference-private')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
out.mkdir(exist_ok=True)
root='https://sources.debian.org/data/main/libs/libssc/0.4.4-2/'
files=['src/libssc-client.c','src/libssc-sensor.c','src/libssc-cli.c','src/libssc-common-private.h',
    'data/ssc-common.proto','data/ssc-sensor-suid.proto']
report=[]
for name in files:
    path=out/Path(name).name
    if path.exists(): raw=path.read_bytes()
    else:
        with urllib.request.urlopen(root+name,timeout=20) as response:
            assert response.status==200
            raw=response.read(256*1024+1)
        assert len(raw)<=256*1024 and raw.startswith((b'/*',b'//')) and b'<!DOCTYPE' not in raw
        path.write_bytes(raw)
    report.append(dict(url=root+name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
(ref/'libssc-suid-source-reference.json').write_text(json.dumps(dict(
    upstream_version='0.4.4',debian_source_version='0.4.4-2',files=report,
    installed_version='0.4.4-r0',installed_binary_replaced=False,phone_changed=False),indent=2)+'\n')
print(json.dumps(dict(source_files=len(report),version='0.4.4',phone_changed=False)))
