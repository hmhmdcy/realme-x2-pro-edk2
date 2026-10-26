"""Fetch only named files from the same-machine fixed OEM commit; no devices."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,urllib.request,sys
HERE=Path(__file__).resolve().parent
PRIVATE=Path('E:/edk2-samurai-out/charging-management-20261023/oem-fastcharge-private') if sys.platform=='win32' else Path('/mnt/e/edk2-samurai-out/charging-management-20261023/oem-fastcharge-private')
OUT=PRIVATE/'oem';OUT.mkdir(parents=True,exist_ok=True)
REPO='realme-kernel-opensource/realmeX2pro-X3-AndroidR-kernel-source'
COMMIT='23172a1571bd91156032cc9fef16284a82b63d2c'
FILES=['drivers/power/oppo/oplus_vooc.c','drivers/power/oppo/oplus_vooc.h',
 'drivers/power/oppo/vooc_ic/Makefile','drivers/power/oppo/vooc_ic/oplus_stm8s.c',
 'drivers/power/oppo/vooc_ic/oplus_rk826.c','drivers/power/oppo/vooc_ic/oplus_rt5125.c',
 'drivers/power/oppo/vooc_ic/oplus_op10.c','drivers/power/oppo/vooc_ic/oplus_vooc_fw.c',
 'drivers/power/oppo/vooc_ic/oplus_vooc_fw.h','drivers/power/oppo/charger_ic/oplus_da9313.c',
 'arch/arm64/boot/dts/19781/sm8150-pinctrl.dtsi','drivers/power/oppo/Kconfig']
def fetch(name):
 p=OUT/name.replace('/','--')
 url=f'https://raw.githubusercontent.com/{REPO}/{COMMIT}/{name}'
 if not p.exists():p.write_bytes(urllib.request.urlopen(url,timeout=30).read())
 return dict(path=name,local=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),url=url)
with ThreadPoolExecutor(max_workers=4) as pool: files=list(pool.map(fetch,FILES))
(HERE/'source-manifest.json').write_text(json.dumps(dict(repository=REPO,commit=COMMIT,files=files),indent=2)+'\n')
print(json.dumps([{'path':x['path'],'bytes':x['bytes']} for x in files]))
