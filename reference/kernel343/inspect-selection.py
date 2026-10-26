"""Inspect the pinned selection implementation and retained mode container."""
from pathlib import Path
import hashlib,json,struct,subprocess
import host

HERE=Path(__file__).resolve().parent;P=host.PRIVATE;repo=Path('/home/cy122/x2pro-linux/refs/CamxChi-k117')
commit='9f17f1b568626b393e785b369c5dc94543774d7a';directory=P/'sources';directory.mkdir(exist_ok=True)
names=['camx/src/core/camxtuningdatamanager.cpp','camx/src/core/camxtuningdatamanager.h',
 'chi-cdk/api/common/chituningmodeparam.h','chi-cdk/core/chiutils/chxutils.cpp']
rows=[]
for name in names:
 target=directory/Path(name).name
 if not target.exists():
  q=subprocess.run(['git','-C',str(repo),'show',commit+':'+name],capture_output=True,timeout=35)
  if q.returncode:raise RuntimeError(name+': '+q.stderr.decode())
  target.write_bytes(q.stdout)
 raw=target.read_bytes();rows.append(dict(repository='https://github.com/bjzhou/CamxChi',commit=commit,path=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
(HERE/'primary-sources.json').write_text(json.dumps(dict(stage=343,sources=rows),indent=2)+'\n')
for name in ['sunny_s5kgw1','sunny_imx471','sunny_imx319','qtech_s5k3m5sx']:
 index=json.loads((P.parent/'kernel333'/(name+'-index-private.json')).read_text());raw=(P.parent/('kernel'+str(index['source_stage']))/index['filename']).read_bytes()
 section=next(x for x in index['sections'] if x[0]==2);data=raw[section[1]:section[1]+section[2]]
 (P/(name+'-mode-section-private.bin')).write_bytes(data)
 print(json.dumps(dict(name=name,mode_section_bytes=len(data),prefix_words=list(struct.unpack_from('<32I',data)))))
parser=Path('/home/cy122/x2pro-linux/parser-k117/ParameterParser')
q=subprocess.run(['nm','-C',str(parser)],capture_output=True,text=True);(P/'parser-symbols-private.txt').write_text(q.stdout)
print('Pinned selection sources obtained; parser symbols retained privately.')
