from pathlib import Path
import json
locations=[Path('/home/cy122/pmos-samurai-rootfs01/work/cache_apk_aarch64'),Path('/home/cy122/pmos-samurai-rootfs01/work/packages')]
records=[]
for root in locations:
    for p in root.rglob('libcamera*.apk'):
        records.append(dict(path=str(p),file=p.name,bytes=p.stat().st_size))
private=Path('/mnt/e/edk2-samurai-out/kernel214');(private/'rollback-apk-cache-private.json').write_text(json.dumps(records,indent=2)+'\n');print(json.dumps([dict(file=r['file'],bytes=r['bytes']) for r in records]))
