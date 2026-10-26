from pathlib import Path
import hashlib, json, tarfile

O=Path('/mnt/e/edk2-samurai-out/kernel89')
W=Path('/mnt/e/RealmeX2Pro edk2')
old=O.parent/'kernel88'
sha=lambda b:hashlib.sha256(b).hexdigest()
dest=O/'runtime-firmware.tar'
assert not dest.exists()
mpss=json.loads((old/'mpss-firmware-manifest.json').read_text())
assert sha((old/'mpss-firmware-stock.tar').read_bytes())==mpss['archive_sha256']
files={}
with tarfile.open(old/'mpss-firmware-stock.tar') as t:
    for item in mpss['files']:
        data=t.extractfile('./'+item['name']).read()
        assert sha(data)==item['sha256'] and len(data)==item['bytes']
        files[item['name']]=data
wifi=json.loads((W/'reference/kernel81/wifi-firmware-manifest.json').read_text())
with tarfile.open(O.parent/'kernel81/wifi-firmware-stock.tar') as t:
    data=t.extractfile('wlanmdsp.mbn').read()
item=next(x for x in wifi['files'] if x['name']=='wlanmdsp.mbn')
assert sha(data)==item['sha256'] and len(data)==item['bytes']
files['wlanmdsp.mbn']=data
import io
with tarfile.open(dest,'w') as t:
    for name,data in files.items():
        record=tarfile.TarInfo('qcom/sm8150/realme/samurai/'+name)
        record.size=len(data);record.mode=0o444
        t.addfile(record,io.BytesIO(data))
(O/'runtime-firmware-sha256.txt').write_text('\n'.join(f'{sha(data)}  qcom/sm8150/realme/samurai/{name}' for name,data in files.items())+'\n')
(O/'runtime-firmware-manifest.json').write_text(json.dumps({'archive_sha256':sha(dest.read_bytes()),'bytes':dest.stat().st_size,'files':len(files),'board_files_installed':False,'source':'same handset private stock archives'},indent=2)+'\n')
print('Prepared same-handset firmware:',len(files),'files;',sha(dest.read_bytes()))
