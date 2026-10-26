from pathlib import Path
from urllib.request import Request,urlopen
from concurrent.futures import ThreadPoolExecutor
import base64,hashlib,json
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel222');out=private/'sof-public-source';assert not out.exists();out.mkdir(mode=0o700)
prefix='https://android.googlesource.com/kernel/msm/+/1f626a61841c7474c4baa02e5e6f4260c0622bdd/drivers/media/platform/msm/ais/cam_isp/isp_hw_mgr/isp_hw/vfe_hw/vfe17x/'
def fetch(name):
 url=prefix+name
 try:
  data=base64.b64decode(urlopen(Request(url+'?format=TEXT',headers={'User-Agent':'samurai-linux-source-review'}),timeout=25).read(2_000_000),validate=True);(out/name).write_bytes(data)
  return name,dict(url=url,fetched=True,bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
 except Exception as error:return name,dict(url=url,fetched=False,error_type=type(error).__name__)
records=dict(ThreadPoolExecutor(max_workers=3).map(fetch,['cam_vfe170.h','cam_vfe175.h','cam_vfe_lite170.h']))
r=dict(stage=222,source_review_only=True,files=records);(here/'sof-public-source-validation.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r))
for name,item in records.items():
 if not item['fetched']:continue
 lines=(out/name).read_text().splitlines();ix=[i for i,l in enumerate(lines) if any(s in l for s in ['sof_irq_mask','sof_status','rdi0_reg_data','rdi1_reg_data','rdi2_reg_data'])]
 print(name+'\n'+'\n'.join(f'{i+1}: {l}' for i,l in enumerate(lines) if any(-3<=i-j<7 for j in ix)))
