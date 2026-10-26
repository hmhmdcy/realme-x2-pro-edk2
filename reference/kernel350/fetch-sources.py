"""Read only the fixed-revision files needed for the Gamma path."""
from pathlib import Path
import hashlib,json,shutil,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;directory=P/'sources';directory.mkdir(exist_ok=True)
commit='9f17f1b568626b393e785b369c5dc94543774d7a';repo='/home/cy122/x2pro-linux/refs/CamxChi-k117'
paths=['chi-cdk/api/chromatix/XSD/isp/gamma_1_5_0.xsd',
 'camx/src/hwl/iqsetting/gamma15setting.cpp','camx/src/hwl/iqsetting/gamma15setting.h',
 'camx/src/hwl/iqinterpolation/gamma15interpolation.cpp',
 'camx/src/hwl/isphwsetting/titan17x/camxipegamma15titan17x.cpp',
 'camx/src/hwl/ispiqmodule/camxifegamma16.cpp','camx/src/hwl/ispiqmodule/camxipegamma15.cpp',
 'camx/src/hwl/ife/camxifenode.cpp','camx/src/hwl/ipe/camxipenode.cpp',
 'camx/src/hwl/iqsetting/ltm13setting.cpp','camx/src/hwl/ispiqmodule/camxipeltm13.cpp',
 'camx/src/hwl/iqinterpolation/tmc11interpolation.cpp',
 'camx/src/hwl/ispiqmodule/camxiqinterface.cpp',
 'camx/src/hwl/isphwsetting/pipeline/ipe/camxipepipelinetitan175.cpp',
 'camx/src/hwl/isphwsetting/pipeline/ipe/camxipepipelinetitan170.cpp']
records=[]
for name in paths:
 target=directory/Path(name).name
 if not target.exists():
  if name.endswith('gamma_1_5_0.xsd'):shutil.copyfile(P.parent/'kernel349/gamma_1_5_0-reference-private.xsd',target)
  else:target.write_bytes(subprocess.check_output(['git','-C',repo,'show',commit+':'+name],timeout=45))
 raw=target.read_bytes();assert raw
 records.append(dict(path=name,url='https://github.com/bjzhou/CamxChi/blob/'+commit+'/'+name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
 print(name,len(raw),flush=True)
(HERE/'primary-sources.json').write_text(json.dumps(dict(stage=350,commit=commit,files=records),indent=2)+'\n')
