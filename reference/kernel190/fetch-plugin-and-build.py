from pathlib import Path
import json,hashlib,urllib.request

ref=Path(__file__).resolve().parent;record=json.loads((ref/'location-source-reference.json').read_text());commit=record['modemmanager_commit']
names=['src/plugins/qcom-soc/mm-broadband-modem-qmi-qcom-soc.c','src/mm-iface-modem-location.h']
root=Path('/mnt/e/edk2-samurai-out/kernel190/location-sources')
for name in names:
 url='https://raw.githubusercontent.com/linux-mobile-broadband/ModemManager/'+commit+'/'+name
 raw=urllib.request.urlopen(url,timeout=30).read();path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
 record['sources'].append(dict(path=name,sha256=hashlib.sha256(raw).hexdigest(),url=url,bytes=len(raw)))
(ref/'location-source-reference.json').write_text(json.dumps(record,indent=2)+'\n')
url='https://raw.githubusercontent.com/alpinelinux/aports/master/community/modemmanager/APKBUILD'
raw=urllib.request.urlopen(url,timeout=30).read();(root/'APKBUILD').write_bytes(raw)
print('Pinned qcom-soc implementation and current Alpine build recipe fetched.')
