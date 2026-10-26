"""Locate target DS4/precrop/packer instructions using retained debug symbols."""
from pathlib import Path
import hashlib,importlib.util,json,re,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.mounted_build()
old=P.parent/'kernel281';binary=old/'camera.qcom.so-private'
assert hashlib.sha256(binary.read_bytes()).hexdigest()=='e2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde'
symbols=(old/'hal-debug-symbols-with-size-private.txt').read_text();rows=[]
names=['IFEDS410::Create','IFEDS410::Execute','IFEDS410::CheckDependenceChange','IFEDS410::RunCalculation','IFEDS410::UpdateIFEInternalData','IFEPreCrop10::Execute','IFER2PD10::Execute','IFERoundClamp11::Execute']
for name in names:
 line=next(l for l in symbols.splitlines() if name+'(' in l);fields=line.split(maxsplit=3);start,size=int(fields[0],16),int(fields[1],16)
 raw=subprocess.check_output(['aarch64-linux-gnu-objdump','-d','--start-address='+hex(start),'--stop-address='+hex(start+size),str(binary)])
 (P/(name.replace('::','-')+'-private.asm')).write_bytes(raw)
 rows.append(dict(name=name,address=hex(start),bytes=size))
(HERE/'native-functions.json').write_text(json.dumps(dict(stage=426,functions=rows),indent=2)+'\n')
print(json.dumps(rows,indent=2))
