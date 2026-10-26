from pathlib import Path
import importlib.util,json,re,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(s);s.loader.exec_module(storage);storage.mounted_build()
repo='/home/cy122/x2pro-linux/refs/CamxChi-k117';rev='9f17f1b568626b393e785b369c5dc94543774d7a'
names=subprocess.check_output(['git','-C',repo,'ls-tree','-r','--name-only',rev],text=True).splitlines()
selected=[n for n in names if Path(n).name in ['camxtitan17xdefs.h'] or re.search(r'titan170.*ipe.*\.h$',Path(n).name,re.I)]
print(json.dumps(selected))
for n in selected:
 raw=subprocess.check_output(['git','-C',repo,'show',rev+':'+n]);(P/'sources'/Path(n).name).write_bytes(raw)
 lines=raw.decode().splitlines()
 for i,line in enumerate(lines):
  if '#include' in line and 'camxtitan17xdefs' in n:print(line)
  if 'IPE_IPE_0_PPS_CLC_LTM_MODULE_CFG' in line:
   print(n,i+1,'\n'.join(lines[max(0,i-3):i+30]))
