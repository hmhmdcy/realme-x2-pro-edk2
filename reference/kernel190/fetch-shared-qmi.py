from pathlib import Path
import hashlib,json,urllib.request

ref=Path(__file__).resolve().parent;record=json.loads((ref/'location-source-reference.json').read_text());commit=record['modemmanager_commit']
name='src/mm-shared-qmi.c';url='https://raw.githubusercontent.com/linux-mobile-broadband/ModemManager/'+commit+'/'+name
raw=urllib.request.urlopen(url,timeout=30).read();path=Path('/mnt/e/edk2-samurai-out/kernel190/location-sources')/name;path.write_bytes(raw)
record['sources'].append(dict(path=name,sha256=hashlib.sha256(raw).hexdigest(),url=url,bytes=len(raw)))
(ref/'location-source-reference.json').write_text(json.dumps(record,indent=2)+'\n')
print('Pinned shared QMI implementation fetched.')
