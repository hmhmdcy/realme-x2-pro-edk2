from pathlib import Path
import urllib.request,json,hashlib
out=Path('/mnt/e/edk2-samurai-out/kernel117/camera-dt-reference');out.mkdir(exist_ok=False)
commit='47087509c4289c2580c54f5433e55366b2e00445'
names=['0056-arm64-dts-sm8150-add-the-camera-subsystem.patch','0057-arm64-dts-sm8150-add-the-camera-control-interfaces.patch']
records=[]
for name in names:
    path='aports/device/testing/linux-oneplus-hotdog-mainline616/'+name
    url=f'https://raw.githubusercontent.com/Sr-0w/hotdog-linux-bringup/{commit}/{path}'
    with urllib.request.urlopen(url,timeout=30) as r:data=r.read()
    (out/name).write_bytes(data)
    records.append(dict(path=path,url=url,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
(out/'source-manifest.json').write_text(json.dumps(dict(commit=commit,files=records,board_changes_not_downloaded=True),indent=2)+'\n')
print('SOC_CAMERA_CCI_DT_REFERENCE_PINNED',len(records))
