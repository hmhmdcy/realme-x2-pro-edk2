"""Fetch a bounded set of source files for comparison, without running them."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,urllib.request

out=Path('/mnt/e/edk2-samurai-out/kernel203/related-device-sources')
hot='https://raw.githubusercontent.com/Sr-0w/hotdog-linux-bringup/main/'
oppo='https://raw.githubusercontent.com/oppo-source/android_kernel_oppo_sm8150/oppo/sm8150_s_12.1_oppo_reno10/arch/arm64/boot/dts/qcom/'
sources={
 'hotdog-gnss':hot+'docs/evidence/2026-08-10-gnss-qmi-loc.md',
 'hotdog-pdc-gate':hot+'docs/evidence/2026-08-25-modemmanager-preonline-gate.md',
 'hotdog-physical-sensors':hot+'docs/evidence/2026-08-23-the-firmware-version-was-the-cause.md',
 'oppo-dts-makefile':oppo+'Makefile',
 'oppo-sm8150-common':oppo+'sm8150.dtsi',
 'realme-x3-readme-main':'https://raw.githubusercontent.com/sm8150-linux-mainline/pmos_realme_x3/main/README.md',
 'realme-x3-apkbuild':'https://raw.githubusercontent.com/sm8150-linux-mainline/pmaports/master/device/testing/device-realme-x3/APKBUILD',
 'realme-x3-kernel-apkbuild':'https://raw.githubusercontent.com/sm8150-linux-mainline/pmaports/master/device/testing/linux-realme-x3/APKBUILD',
 'realme-x3-firmware-apkbuild':'https://raw.githubusercontent.com/sm8150-linux-mainline/pmaports/master/device/testing/firmware-realme-x3/APKBUILD',
 'realme-x3-dts':'https://raw.githubusercontent.com/sm8150-linux-mainline/linux/sm8150/6.11/arch/arm64/boot/dts/qcom/sm8150-realme-x3.dts',
 'realme-x3-dts-pinned':'https://raw.githubusercontent.com/sm8150-linux-mainline/linux/91911e069acbb9d38e5dcc633d454f7b1ff9bc4b/arch/arm64/boot/dts/qcom/sm8150-realme-x3.dts',
 'realme-x3-hci-qca-pinned':'https://raw.githubusercontent.com/sm8150-linux-mainline/linux/91911e069acbb9d38e5dcc633d454f7b1ff9bc4b/drivers/bluetooth/hci_qca.c',
}
def fetch(item):
 name,url=item
 try:
  path=out/(name+'.txt')
  data=path.read_bytes() if path.exists() else urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'samurai-linux-research'}),timeout=25).read()
  path.write_bytes(data)
  return name,dict(url=url,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),fetched=True)
 except Exception as exc:return name,dict(url=url,fetched=False,error_type=type(exc).__name__)
records=dict(ThreadPoolExecutor(max_workers=5).map(fetch,sources.items()))
(out/'detail-sources.json').write_text(json.dumps(records,indent=2)+'\n');print(json.dumps(records,indent=2))
