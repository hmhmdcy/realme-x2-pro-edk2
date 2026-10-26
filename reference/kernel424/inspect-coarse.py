"""Locate retained source and native symbols for the missing LTM coarse path."""
from pathlib import Path
import importlib.util,json,re,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(s);s.loader.exec_module(storage);storage.mounted_build()
repo='/home/cy122/x2pro-linux/refs/CamxChi-k117';rev='9f17f1b568626b393e785b369c5dc94543774d7a'
names=subprocess.check_output(['git','-C',repo,'ls-tree','-r','--name-only',rev,'--','camx/src'],text=True).splitlines()
selected=[n for n in names if Path(n).name in ['camxipenode.cpp','camxipenode.h','ipe_data.h','ipeiqsettings.h','camxifeiqinterface.cpp']]
for name in selected:
 raw=subprocess.check_output(['git','-C',repo,'show',rev+':'+name]);dest=P/'sources'/Path(name).name;dest.write_bytes(raw)
 lines=raw.decode().splitlines();matches=[(i+1,l) for i,l in enumerate(lines) if re.search(r'LTM|ltm|Coarse|coarse',l) and re.search(r'Buffer|buffer|Stat|stat|DC|Average|average|Pass|pass',l)]
 print(name,'\n'.join(str(n)+':'+l for n,l in matches[:110]))
symbols=(P.parent/'kernel281/hal-debug-symbols-with-size-private.txt').read_text().splitlines()
matches=[l for l in symbols if re.search(r'(IPENode::.*(LTM|Ltm|ltm|Pass|LoopBack|Multipass)|IFEGTM10|GTM10Calculate|GTM10Setting)',l)]
(P/'coarse-symbols-private.txt').write_text('\n'.join(matches)+'\n');print('Native symbol candidates:', '\n'.join(matches[:45]))
print(json.dumps(dict(selected_reference_files=selected,reference_revision=rev,phone_accessed=False)))
