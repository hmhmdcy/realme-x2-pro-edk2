"""Pin existing public protocol references privately; retain only facts in public receipts."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,re,subprocess,urllib.request
import host
ROOT=Path(__file__).resolve().parent;REF='9f17f1b568626b393e785b369c5dc94543774d7a'
tree=json.loads((host.PRIVATE/'camx-reference-tree-private.json').read_bytes())
paths=[p['path'] for p in tree['tree'] if p['type']=='blob' and p['path'].startswith('camx/') and re.search(r'(camxifebhiststats14(titan17x)?\.(cpp|h)|camxifebls12titan17x\.(cpp|h)|bls12setting\.(cpp|h)|camxifehdrbhiststats13titan17x\.(cpp|h)|titan170_ife\.h|camxtitan170ife\.h)$',p['path'])]
def fetch(path):
 url=f'https://raw.githubusercontent.com/bjzhou/CamxChi/{REF}/{path}';p=host.PRIVATE/('reference-'+Path(path).name+'-private')
 try:
  if not p.exists():p.write_bytes(urllib.request.urlopen(url,timeout=25).read())
  b=p.read_bytes();return dict(path=path,url=url,bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
 except Exception as e:return dict(path=path,url=url,error=str(e))
with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(fetch,paths))
oemrepo=Path('/mnt/e/Realme X2 Pro移植主线Linux/sources/realme-downstream.git');commit='9668fcdc6ec15be7a10d66f7b93c347829e0fdb6'
for name in ['drivers/media/platform/msm/camera/cam_isp/isp_hw_mgr/isp_hw/vfe_hw/vfe17x/cam_vfe175.h','drivers/media/platform/msm/camera/cam_isp/isp_hw_mgr/isp_hw/vfe_hw/vfe_bus/cam_vfe_bus_ver2.c']:
 b=subprocess.check_output(['git','-C',str(oemrepo),'show',commit+':'+name]);(host.PRIVATE/('oem-'+Path(name).name+'-private')).write_bytes(b);rows.append(dict(path=name,commit=commit,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),official_oem_git=True))
(ROOT/'protocol-sources.json').write_text(json.dumps(dict(stage=294,sources=rows,no_oem_execution=True),indent=2)+'\n')
print(json.dumps(rows,indent=2))
for p in host.PRIVATE.glob('reference-*-private'):
 if p.suffix=='.json':continue
 lines=p.read_text(errors='replace').splitlines();hits=[i for i,l in enumerate(lines) if re.search('regIFE|CHANNEL_SELECT|UNIFORM|BIN|OFFSET|SCALE|REGION|RGN_|DMI|BlackLevel|blackLevel|numBins|numOfBins',l)]
 if hits:
  selected=set()
  for i in hits:
   selected.update(range(max(0,i-1),min(len(lines),i+3)))
  out='\n'.join(f'{i+1}: {lines[i]}' for i in sorted(selected));(host.PRIVATE/(p.name+'-fact-windows.txt')).write_text(out)
  print(p.name,'lines',len(lines),'fact_windows',len(selected))
