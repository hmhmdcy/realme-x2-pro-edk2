"""Find bounded conversion sources and target HAL symbols, reusing retained files."""
from pathlib import Path
import hashlib,importlib.util,json,re,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage);storage.mounted_build()
repo='/home/cy122/x2pro-linux/refs/CamxChi-k117';commit='9f17f1b568626b393e785b369c5dc94543774d7a'
tree=subprocess.check_output(['git','-C',repo,'ls-tree','-r','--name-only',commit,'camx/src/hwl'],text=True).splitlines()
names=[p for p in tree if re.search(r'(ipecolortransform12|ipecst12titan17|ipechromaenhancement12|ipecv12titan17|cst12setting|cv12setting)',p,re.I)]
out=P/'sources';out.mkdir(exist_ok=True);rows=[]
for path in names:
 target=out/Path(path).name;previous=P.parent/'kernel350/sources'/target.name
 if not target.exists():target.write_bytes(previous.read_bytes() if previous.exists() else subprocess.check_output(['git','-C',repo,'show',commit+':'+path],timeout=45))
 rows.append(dict(path=path,bytes=target.stat().st_size,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),reused_from350=previous.exists(),url='https://github.com/bjzhou/CamxChi/blob/'+commit+'/'+path))
(HERE/'primary-sources.json').write_text(json.dumps(dict(stage=398,commit=commit,files=rows),indent=2)+'\n')
symbols=(P.parent/'kernel350/hal-symbols-private.txt').read_text().splitlines();selected=[s for s in symbols if any(x in s for x in ['IPEColorTransform12','IPEChromaEnhancement12','CST12CalculateSetting','CV12CalculateSetting'])]
(P/'hal-conversion-symbols-private.txt').write_text('\n'.join(selected)+'\n')
addresses=sorted({int(l.split()[0],16) for l in selected if l.split()[1].lower()=='t'});all_addresses=sorted({int(l.split()[0],16) for l in symbols if len(l.split())>1 and l.split()[1].lower()=='t'})
for start in addresses:
 end=next(x for x in all_addresses if x>start)
 q=subprocess.run(['aarch64-linux-gnu-objdump','-d','-C','--start-address='+hex(start),'--stop-address='+hex(end),str(P.parent/'kernel281/camera.qcom.so-private')],check=True,capture_output=True)
 (P/('hal-conversion-'+hex(start)+'-private.asm')).write_bytes(q.stdout)
print(json.dumps(dict(files=rows,symbols=selected),indent=2))
