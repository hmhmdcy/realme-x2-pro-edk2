"""Reuse target Gamma disassembly and read bounded pinned command sources."""
from pathlib import Path
import hashlib,importlib.util,json,re,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(s);s.loader.exec_module(storage);source=storage.mounted_build().parent/'source354'
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()=='de94e65e7ab4ae2ec23ee1665f981d0aeb7395e7'
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'])
base=source/'drivers/media/platform/qcom/camss'
for n in ['camss-icp-a5-colour.c','camss-icp-a5-colour.h','camss-icp-a5-ipe.h','camss-icp-a5-ipe.c','camss-icp-a5-boot.c']:(P/(n+'.before')).write_bytes((base/n).read_bytes())
asm=P.parent/'kernel350/gamma15-execute-private.asm';assert asm.is_file();(P/'gamma-execute-private.asm').write_bytes(asm.read_bytes())
symbols=(P.parent/'kernel350/hal-symbols-private.txt').read_text().splitlines();selected=[s for s in symbols if any(x in s for x in ['IPEGamma15','WriteDMI','AddNestedCmdBufferInfo','GetPatch','Gamma15Calculate'])]
(P/'gamma-symbols-private.txt').write_text('\n'.join(selected)+'\n')
repo='/home/cy122/x2pro-linux/refs/CamxChi-k117';commit='9f17f1b568626b393e785b369c5dc94543774d7a'
names=subprocess.check_output(['git','-C',repo,'ls-tree','-r','--name-only',commit,'camx/src/hwl','camx/src/utils'],text=True).splitlines()
paths=[n for n in names if re.search(r'(camxipegamma15titan17x|camxipegamma15\.|camxpacketbuilder\.)',n,re.I)]
paths+=['camx/src/core/camxpacketbuilder.cpp','camx/src/core/camxpacketbuilder.h','camx/src/csl/camxcdmdefs.h','chi-cdk/api/isp/chiipedefs.h']
paths=sorted(set(paths))
out=P/'sources';out.mkdir(exist_ok=True);rows=[]
for path in paths:
 target=out/Path(path).name;prior=P.parent/'kernel350/sources'/target.name
 if not target.exists():target.write_bytes(prior.read_bytes() if prior.exists() else subprocess.check_output(['git','-C',repo,'show',commit+':'+path],timeout=45))
 rows.append(dict(path=path,bytes=target.stat().st_size,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),url='https://github.com/bjzhou/CamxChi/blob/'+commit+'/'+path))
(HERE/'primary-sources.json').write_text(json.dumps(dict(stage=401,commit=commit,files=rows),indent=2)+'\n')
print(json.dumps(dict(source_clean=True,retained_gamma_disassembly_reused=True,symbols=selected,source_files=[r['path'] for r in rows]),indent=2))
