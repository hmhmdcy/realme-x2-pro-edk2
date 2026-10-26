from pathlib import Path
import importlib.util,json,struct
from unicorn.arm64_const import UC_ARM64_REG_X0,UC_ARM64_REG_LR
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;storage.mount.mounted_build()
s=importlib.util.spec_from_file_location('native425',HERE.parent/'kernel425/native-model.py');n=importlib.util.module_from_spec(s);s.loader.exec_module(n)
class Trace(n.Native):
 def __init__(self):self.events=[];self.pending={};super().__init__()
 def step(self,u,pc,size,user):
  if pc in self.pending:
   row=self.pending.pop(pc);row['output_hex']=bytes(u.mem_read(row['args'][5],40)).hex()
  if pc in [0x140520,0x1556a0,0x155770,0x1557a8,0x1557b8]:
   row=dict(pc=hex(pc),caller=hex(u.reg_read(UC_ARM64_REG_LR)),args=[u.reg_read(UC_ARM64_REG_X0+i) for i in range(8)]);self.events.append(row)
   if pc==0x1556a0:self.pending[u.reg_read(UC_ARM64_REG_LR)]=row
  super().step(u,pc,size,user)
for w,h in [(640,480),(1280,720),(1920,1080)]:
 m=Trace();config=(P/f'{w}x{h}-config-private.bin').read_bytes();iq=(P/f'{w}x{h}-iq-private.bin').read_bytes();m.striping(config,w,h,1,iq)
 (P/f'{w}x{h}-helper-trace-private.json').write_text(json.dumps(m.events,indent=2)+'\n')
 print(json.dumps({'width':w,'height':h,'events':m.events}),flush=True)
