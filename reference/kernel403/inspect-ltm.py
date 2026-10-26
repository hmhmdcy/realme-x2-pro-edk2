"""Inspect target LTM routines and bounded primary sources from pinned Git."""
from pathlib import Path
import hashlib,importlib.util,json,re,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(s);s.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';state=json.loads((HERE.parent/'kernel402/source-state.json').read_text());assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==state['commit'] and not subprocess.check_output(['git','-C',str(source),'status','--porcelain'])
state.update(stage=403,source_unchanged_from402=True,phone_accessed=False);(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
repo='/home/cy122/x2pro-linux/refs/CamxChi-k117';rev='9f17f1b568626b393e785b369c5dc94543774d7a'
names=subprocess.check_output(['git','-C',repo,'ls-tree','-r','--name-only',rev,'camx/src/hwl'],text=True).splitlines()
paths=[n for n in names if re.search(r'/(camxipeltm13(?:titan17x)?\.(?:cpp|h)|ltm13setting\.(?:cpp|h))$',n)]
assert len(paths)==6,paths
out=P/'sources';out.mkdir(exist_ok=True);rows=[]
for name in paths:
 target=out/Path(name).name;target.write_bytes(subprocess.check_output(['git','-C',repo,'show',rev+':'+name],timeout=45));rows.append(dict(path=name,bytes=target.stat().st_size,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),url='https://github.com/bjzhou/CamxChi/blob/'+rev+'/'+name))
(HERE/'primary-sources.json').write_text(json.dumps(dict(stage=403,commit=rev,files=rows),indent=2)+'\n')
hal=P.parent/'kernel281/camera.qcom.so-private'
for name,start,end in [('ltm-execute-private.asm',0x35e848,0x366dd0),('ltm-resource-private.asm',0x366dd0,0x3672a0)]:
 q=subprocess.run(['aarch64-linux-gnu-objdump','-d','--start-address='+hex(start),'--stop-address='+hex(end),str(hal)],capture_output=True,check=True);(P/name).write_bytes(q.stdout)
print(json.dumps(dict(source_clean=True,source_commit=state['commit'],pinned_files=[r['path'] for r in rows],target_ltm_execution_and_resource_disassembly_saved=True,phone_accessed=False),indent=2))
