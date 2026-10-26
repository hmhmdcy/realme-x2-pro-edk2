"""Read primary repositories; never execute or deploy their contents."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,urllib.request

out=Path('/mnt/e/edk2-samurai-out/kernel203/related-device-sources');out.mkdir(parents=True,exist_ok=True)
sources={
 'hotdog-status':'https://raw.githubusercontent.com/Sr-0w/hotdog-linux-bringup/main/docs/status.md',
 'hotdog-readme':'https://raw.githubusercontent.com/Sr-0w/hotdog-linux-bringup/main/README.md',
 'hotdog-camera':'https://raw.githubusercontent.com/Sr-0w/hotdog-linux-bringup/main/docs/evidence/2026-08-09-mainline616-camera-telephoto.md',
 'oppo-r11-readme':'https://raw.githubusercontent.com/CPH1707-Mainline/oppo-r11-archlinux-sdm660-oppor11-t/main/README.md',
 'oppo-r11-wifi':'https://raw.githubusercontent.com/CPH1707-Mainline/oppo-r11-archlinux-sdm660-oppor11-t/main/OPPO_R11T_WIFI_MAINLINE_BRINGUP.md',
 'realme-x3-meta':'https://api.github.com/repos/sm8150-linux-mainline/pmos_realme_x3',
 'oppo-sm8150-meta':'https://api.github.com/repos/oppo-source/android_kernel_oppo_sm8150',
}
def fetch(item):
 name,url=item
 try:
  data=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'samurai-linux-research'}),timeout=25).read();(out/(name+'.txt')).write_bytes(data)
  return name,dict(url=url,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),fetched=True)
 except Exception as exc:return name,dict(url=url,fetched=False,error_type=type(exc).__name__)
records=dict(ThreadPoolExecutor(max_workers=5).map(fetch,sources.items()))
(out/'sources.json').write_text(json.dumps(records,indent=2)+'\n')
print(json.dumps(records,indent=2))
