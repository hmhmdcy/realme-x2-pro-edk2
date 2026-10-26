from pathlib import Path
import hashlib,json,tarfile,urllib.request

root=Path('/mnt/e/edk2-samurai-out/kernel190/geoclue-sources');root.mkdir(parents=True,exist_ok=True)
urls=['https://distfiles.alpinelinux.org/distfiles/edge/geoclue-2.8.2.tar.bz2','https://distfiles.alpinelinux.org/distfiles/edge/geoclue-2.8.2.tar.gz']
errors=[]
for url in urls:
 try:
  raw=urllib.request.urlopen(url,timeout=30).read()
  path=root/url.rsplit('/',1)[1];path.write_bytes(raw)
  with tarfile.open(path) as tar:tar.extractall(root,filter='data')
  report=dict(url=url,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
  (Path(__file__).resolve().parent/'geoclue-source-reference.json').write_text(json.dumps(report,indent=2)+'\n')
  print(json.dumps(report));break
 except Exception as error:errors.append(str(error))
else:raise RuntimeError(errors)
