from pathlib import Path
import hashlib,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;directory=P/'sources';directory.mkdir(exist_ok=True)
repo='/home/cy122/x2pro-linux/refs/CamxChi-k117';commit='9f17f1b568626b393e785b369c5dc94543774d7a';records=[]
path='camx/src/hwl/ipe/camxipenode.h';target=directory/Path(path).name
if not target.exists():target.write_bytes(subprocess.check_output(['git','-C',repo,'show',commit+':'+path],timeout=50))
raw=target.read_bytes();records.append(dict(path=path,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),url='https://github.com/bjzhou/CamxChi/blob/'+commit+'/'+path))
print('\n'.join(l for l in raw.decode().splitlines() if l.startswith('#include')))
names=subprocess.check_output(['git','-C',repo,'ls-tree','-r','--name-only',commit,'--','camx/src/hwl','camx/src/csl'],text=True,timeout=25).splitlines()
matches=[n for n in names if any(x in Path(n).name.lower() for x in ['ipe_data','ipe_hfi','ipe.h','ipe_types','fwdefs','fw_intf'])]
(P/'matching-reference-paths-private.json').write_text(json.dumps(matches,indent=2)+'\n');print(json.dumps(matches))
(HERE/'primary-sources.json').write_text(json.dumps(dict(stage=377,commit=commit,files=records),indent=2)+'\n')
