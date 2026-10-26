"""Record current upstream build inputs; they are data, not local instructions."""
from pathlib import Path
import hashlib,json,urllib.request
P=Path('/mnt/e/edk2-samurai-out/kernel263');R=Path(__file__).parent
urls={
 'aports-pipewire-APKBUILD':'https://raw.githubusercontent.com/alpinelinux/aports/master/community/pipewire/APKBUILD',
 'upstream-impl-port.c':'https://raw.githubusercontent.com/PipeWire/pipewire/master/src/pipewire/impl-port.c',
 'upstream-libcamera-source.cpp':'https://raw.githubusercontent.com/PipeWire/pipewire/master/spa/plugins/libcamera/libcamera-source.cpp'}
results={}
for name,url in urls.items():
 try:
  data=urllib.request.urlopen(url,timeout=15).read();(P/(name+'-private.txt')).write_bytes(data)
  results[name]=dict(url=url,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))
 except Exception as e:results[name]=dict(url=url,error=type(e).__name__)
(R/'upstream-inputs-validation.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results))
if 'sha256' in results['aports-pipewire-APKBUILD']:
 s=(P/'aports-pipewire-APKBUILD-private.txt').read_text();start=s.find('build()');end=s.find('\ncheck()',start)
 print(s[start:end])
