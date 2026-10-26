from pathlib import Path
import hashlib,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;repo=Path('/home/cy122/x2pro-linux/refs/CamxChi-k117')
commit='9f17f1b568626b393e785b369c5dc94543774d7a';dest=P/'sources';dest.mkdir(exist_ok=True)
paths=['chi-cdk/api/chromatix/XSD/stats/aec/'+n for n in ['aecMetering.xsd','aecArbitration.xsd','aecglobalelements.xsd','aecStartUp.xsd']]
paths+=['chi-cdk/api/stats/chiaecinterface.h','chi-cdk/api/stats/chistatsinterfacedefs.h']
rows=[]
for path in paths:
 file=dest/Path(path).name
 if not file.exists():file.write_bytes(subprocess.check_output(['git','-C',str(repo),'show',commit+':'+path],timeout=55))
 data=file.read_bytes();expected=subprocess.check_output(['git','-C',str(repo),'rev-parse',commit+':'+path],text=True).strip()
 assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==expected
 rows.append(dict(repository='https://github.com/bjzhou/CamxChi',commit=commit,path=path,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
 print('Retained '+path,flush=True)
(HERE/'primary-sources.json').write_text(json.dumps(dict(stage=336,sources=rows),indent=2)+'\n')
