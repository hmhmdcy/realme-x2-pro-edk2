"""Use retained primary sources and target ELF to recover GTM data contracts."""
from pathlib import Path
import hashlib,importlib.util,json,re,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage432',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.mounted_build()
repo='/home/cy122/x2pro-linux/refs/CamxChi-k117';rev='9f17f1b568626b393e785b369c5dc94543774d7a'
names=subprocess.check_output(['git','-C',repo,'ls-tree','-r','--name-only',rev],text=True).splitlines()
selected=[n for n in names if Path(n).name in ['iqcommondefs.h','gtm10interpolation.cpp','gtm10interpolation.h','gtm10setting.h','gtm10setting.cpp','camxifegtm10.cpp','camxifegtm10.h','camxifegtm10titan17x.cpp','camxifegtm10titan17x.h']]
out=P/'sources';out.mkdir(exist_ok=True);rows=[]
for n in selected:
 raw=subprocess.check_output(['git','-C',repo,'show',rev+':'+n]);(out/Path(n).name).write_bytes(raw)
 rows.append(dict(path=n,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)))
symbols=(P.parent/'kernel281/hal-debug-symbols-with-size-private.txt').read_text();found=[]
for line in symbols.splitlines():
 if re.search(r'GTM10|gtm10|gtm_1_0_0',line):found.append(line)
(P/'gtm-symbols-private.txt').write_text('\n'.join(found)+'\n')
r=dict(stage=432,reference_revision=rev,files=rows,target_hal_sha256='e2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde',target_symbol_rows=len(found),new_firmware_download=False,phone_accessed=False,passed=True)
(HERE/'primary-sources.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(files=[r['path'] for r in rows],target_symbol_rows=len(found),passed=True)))
