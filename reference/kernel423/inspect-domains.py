"""Inspect retained native Gamma transport and fixed source types."""
from pathlib import Path
import importlib.util,subprocess,json
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(s);s.loader.exec_module(storage);storage.mounted_build()
P=Path('/mnt/e/edk2-samurai-out/kernel423');P.mkdir(mode=0o700,exist_ok=True)
repo='/home/cy122/x2pro-linux/refs/CamxChi-k117';rev='9f17f1b568626b393e785b369c5dc94543774d7a'
names=subprocess.check_output(['git','-C',repo,'ls-tree','-r','--name-only',rev,'--','camx/src'],text=True,timeout=15).splitlines()
files={n for n in names if Path(n).name in ['camxifeproperty.h','camxifegamma16.h','iqcommondefs.h']}
assert 0<len(files)<=5,files
out=P/'sources';out.mkdir(exist_ok=True)
for name in files:
    raw=subprocess.check_output(['git','-C',repo,'show',rev+':'+name]);(out/Path(name).name).write_bytes(raw)
    lines=raw.decode().splitlines()
    for i,line in enumerate(lines):
        if 'GammaInfo' in line or 'Gamma16NumberOfEntriesPerLUT' in line:print(name,i+1,'\n'.join(lines[max(0,i-10):i+4]))
hal=P.parent/'kernel281/camera.qcom.so-private'
for name,start,end in [('ltm-gamma-input',0x35e848,0x367178),('ltm-interpolation',0x49e980,0x4a0238),('ife-gamma-publication',0x31ef00,0x31f7d0)]:
    q=subprocess.run(['aarch64-linux-gnu-objdump','-d','--start-address='+hex(start),'--stop-address='+hex(end),str(hal)],capture_output=True,check=True)
    (P/(name+'-private.asm')).write_bytes(q.stdout)
print(json.dumps(dict(stage=423,files=sorted(files),phone_accessed=False)))
