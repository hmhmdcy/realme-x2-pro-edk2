from pathlib import Path
import hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.mounted_build()
repo='/home/cy122/x2pro-linux/refs/CamxChi-k117';rev='9f17f1b568626b393e785b369c5dc94543774d7a'
names=subprocess.check_output(['git','-C',repo,'ls-tree','-r','--name-only',rev],text=True).splitlines()
selected=[n for n in names if Path(n).name in ['camxifemnds16.cpp','camxifemnds16.h','camxispinputdata.h','camxifecrop10.cpp','camxifeprecrop10.cpp']]
out=P/'scaler-reference';out.mkdir(exist_ok=True);rows=[]
for name in selected:
 data=subprocess.check_output(['git','-C',repo,'show',rev+':'+name]);(out/Path(name).name).write_bytes(data)
 rows.append(dict(path=name,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data)))
(HERE/'scaler-reference-validation.json').write_text(json.dumps(dict(stage=428,repository='https://github.com/bjzhou/CamxChi',revision=rev,files=rows,original_target_binary_used_separately=True,passed=bool(rows)),indent=2)+'\n');print(json.dumps(rows))
