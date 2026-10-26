from pathlib import Path
import hashlib,json,urllib.request,subprocess

root=Path('/mnt/e/edk2-samurai-out/kernel190/location-sources');root.mkdir(parents=True,exist_ok=True)
def fetch(url):return urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Samurai-Linux-bringup'}),timeout=30).read()
base='https://api.github.com/repos/linux-mobile-broadband/ModemManager'
record=subprocess.run(['git','-c','http.version=HTTP/1.1','ls-remote','https://github.com/linux-mobile-broadband/ModemManager.git','refs/heads/main'],capture_output=True,timeout=40)
(root/'ls-remote-private.log').write_bytes(record.stdout+record.stderr);assert record.returncode==0
commit=record.stdout.decode().split()[0];assert len(commit)==40
paths=['src/mm-iface-modem-location.c','src/mm-broadband-modem-qmi.c','src/mm-iface-modem.c',
 'include/ModemManager-enums.h','introspection/org.freedesktop.ModemManager1.Modem.Location.xml']
records=[]
for name in paths:
 url='https://raw.githubusercontent.com/linux-mobile-broadband/ModemManager/'+commit+'/'+name
 raw=fetch(url);path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
 records.append(dict(path=name,sha256=hashlib.sha256(raw).hexdigest(),url=url,bytes=len(raw)))
report=dict(modemmanager_commit=commit,sources=records)
(Path(__file__).resolve().parent/'location-source-reference.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(commit=commit,files=[r['path'] for r in records])))
