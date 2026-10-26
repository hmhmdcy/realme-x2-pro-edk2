"""Pin the public port enumeration that was missing from the first HAL interpretation."""
from pathlib import Path
import hashlib,json,re,urllib.request
ROOT=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel294');ref='9f17f1b568626b393e785b369c5dc94543774d7a'
rows=[]
for path in ['camx/src/hwl/ife/camxifenode.h','camx/src/hwl/isphwsetting/pipeline/camxisppipeline.h','camx/src/settings/common/camxsettings.xml']:
 p=P/('reference-'+Path(path).name+'-private');url=f'https://raw.githubusercontent.com/bjzhou/CamxChi/{ref}/{path}'
 if not p.exists():p.write_bytes(urllib.request.urlopen(url,timeout=25).read())
 rows.append(dict(path=path,url=url,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size))
 lines=p.read_text().splitlines()
 for i,l in enumerate(lines):
  if re.search('IFEOutputPortStatsBHIST|IFEOutputPortStatsRS|struct IFEOutputPath|IFEOutputPath[ ;{]|IFEOutputPortStatsHDRBE',l):print(Path(path).name,str(i+1),l.strip())
(ROOT/'enable-port-sources.json').write_text(json.dumps(dict(stage=294,sources=rows),indent=2)+'\n')
