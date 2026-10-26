"""Inspect retained kernel and reference IQ paths without modifying the phone."""
from pathlib import Path
import importlib.util,json,re,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(s);s.loader.exec_module(storage)
kernel=storage.mounted_build().parent/'source354'
q=subprocess.run(['git','-C',str(kernel),'status','--short'],capture_output=True,check=True);print('Kernel status:',q.stdout.decode())
camss=kernel/'drivers/media/platform/qcom/camss'
selected={}
for name in ['camss-icp-a5-ipe.c','camss-icp-a5-core.c','camss-icp-a5-colour.c','camss-icp-a5-m2m.c','camss-icp-a5.h']:
 p=camss/name
 if not p.exists():continue
 selected[name]=p.read_text();(P/name).write_text(selected[name])
 matches=[(i+1,l) for i,l in enumerate(selected[name].splitlines()) if re.search(r'coarse|ltm.*stat|ltm.*dc|gtm|GTM|avg3d|avg_3d',l,re.I)]
 print(name,'\n'.join(str(n)+':'+l for n,l in matches[:65]))
repo='/home/cy122/x2pro-linux/refs/CamxChi-k117';rev='9f17f1b568626b393e785b369c5dc94543774d7a'
names=subprocess.check_output(['git','-C',repo,'ls-tree','-r','--name-only',rev,'--','camx/src'],text=True).splitlines()
names=[n for n in names if re.search(r'(gtm10|ltm13|ipeltm|ipe.*pipeline)',Path(n).name,re.I)]
print('Reference files:',json.dumps(names))
out=P/'sources';out.mkdir(exist_ok=True)
for name in names:
 raw=subprocess.check_output(['git','-C',repo,'show',rev+':'+name]);(out/Path(name).name).write_bytes(raw)
 if re.search(r'(camxifegtm10|camxipeltm13)\.(cpp|h)$',name,re.I):
  lines=raw.decode().splitlines();matches=[(i+1,l) for i,l in enumerate(lines) if re.search(r'gtmPercentage|ltmPercentage|DRCGain|Coarse|Avg3D|avg3d|DCEnable|IPEnable|dataCollect',l,re.I)]
  print(name,'\n'.join(str(n)+':'+l for n,l in matches[:65]))
(P/'selected-sources-private.json').write_text(json.dumps(dict(reference_revision=rev,paths=names),indent=2)+'\n')
print('Kernel HEAD:',subprocess.check_output(['git','-C',str(kernel),'rev-parse','HEAD'],text=True).strip())
