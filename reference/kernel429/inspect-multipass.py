"""Read the retained native DC helpers and pass structures privately."""
from pathlib import Path
import importlib.util,json,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.mounted_build()
hal=P.parent/'kernel281/camera.qcom.so-private'
symbols=[]
for line in (P.parent/'kernel281/hal-debug-symbols-with-size-private.txt').read_text().splitlines():
 f=line.split(None,3)
 if len(f)!=4:continue
 try:a=int(f[0],16);size=int(f[1],16)
 except ValueError:continue
 if 0x153000<=a<0x156000 and size and f[2].lower()=='t':symbols.append(dict(address=a,size=size,name=f[3]))
(P/'multipass-neighbor-symbols-private.json').write_text(json.dumps(symbols,indent=2)+'\n')
for name,a,b in [('ltm-coarse-and-ip',0x155000,0x155900)]:
 data=subprocess.check_output(['aarch64-linux-gnu-objdump','-d','--start-address='+hex(a),'--stop-address='+hex(b),str(hal)])
 (P/(name+'-private.asm')).write_bytes(data)
rows=[]
for width in [640,650]:
 raw=(P.parent/f'kernel425/width-{width}-dc-1-stripe-private.bin').read_bytes()
 for index in [0,1]:
  base=20+index*412;count=struct.unpack_from('<H',raw,base+408)[0];off=base+struct.unpack_from('<I',raw,base+412)[0]
  rows.append(dict(width=width,index=index,stripes=count,offset=off,halfwords=struct.unpack_from('<312H',raw,off)))
(P/'native-pass-layout-private.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps(dict(symbols=len(symbols),native_pass_rows=len(rows),saved_privately=True)))
