from pathlib import Path
import json,urllib.request,hashlib
base=Path('/mnt/e/edk2-samurai-out/kernel114/primary-reference')
out=Path('/mnt/e/edk2-samurai-out/kernel115/camera-reference')
out.mkdir(exist_ok=False)
manifest=json.loads((base/'source-manifest.json').read_text())
commit=manifest['commit']; assert commit=='47087509c4289c2580c54f5433e55366b2e00445'
tree=json.loads((base/'tree.json').read_text())['tree']
selected=[x['path'] for x in tree if x['type']=='blob' and (
 (x['path'].startswith('aports/device/testing/linux-oneplus-hotdog-mainline616/') and any(n in x['path'].lower() for n in ['camss','sm8150-camnoc','sm8150-hf-axi'])) or
 x['path'] in ['docs/evidence/2026-08-09-mainline616-camera-imx586.md','docs/evidence/2026-08-07-mainline616-remaining-hardware.md'])]
records=[]
for name in selected:
    url=f'https://raw.githubusercontent.com/Sr-0w/hotdog-linux-bringup/{commit}/{name}'
    req=urllib.request.Request(url,headers={'User-Agent':'samurai-port-research'})
    with urllib.request.urlopen(req,timeout=45) as r: data=r.read()
    p=out/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    records.append(dict(path=name,url=url,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data)))
report=dict(commit=commit,files=records,board_changes_not_applied=True)
(out/'source-manifest.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(commit=commit,files=len(records),paths=selected),indent=2))
