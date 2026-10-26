"""Trace original command construction before enqueue; retain all native bytes privately."""
from pathlib import Path
import importlib.util,json,struct
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_SP,UC_ARM_REG_LR
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
module('storage430',HERE.parent/'kernel284/storage.py').mounted_build()
fw=module('fw429',HERE.parent/'kernel429/firmware-model.py')
old=fw.r.Firmware
class Trace(old):
 def __init__(self):super().__init__();self.events=[]
 def step(self,u,pc,size,user):
  names={0xf340:'random-reg-program',0xf420:'dmi-program',0x11366:'pps-parameters',0x1153a:'striping-pass',0x1ecd6:'sync-cores',0x1fea8:'accumulator-regs',0x1ff82:'accumulator-command',0x1fb4c:'enqueue-accumulator'}
  if pc in names:
   args=[u.reg_read(r) for r in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]];sp=u.reg_read(UC_ARM_REG_SP)
   row=dict(kind=names[pc],caller=hex(u.reg_read(UC_ARM_REG_LR)&~1),args=args,stack=struct.unpack('<8I',u.mem_read(sp,32)))
   if pc==0x1ff82 and args[2]<=4096:row['command_hex']=bytes(u.mem_read(args[1],args[2])).hex()
   if pc==0xf420:row['extra_words']=struct.unpack('<8I',u.mem_read(sp,32))
   self.events.append(row)
  return super().step(u,pc,size,user)
config=(P.parent/'kernel425/width-640-dc-1-config-private.bin').read_bytes();iq=(P.parent/'kernel424/coarse-width-640-dc-1-iq-private.bin').read_bytes();stripe=(P.parent/'kernel429/actual-c-stripe-private.bin').read_bytes()
fw.r.Firmware=Trace
for cores in [1,2]:
 m,job,commands,scratch=fw.prepare(config,stripe,iq,cores)
 (P/f'cores-{cores}-events-private.json').write_text(json.dumps(m.events,indent=2)+'\n')
 (P/f'cores-{cores}-commands-private.bin').write_bytes(commands)
 from collections import Counter
 print(json.dumps(dict(cores=cores,events=Counter(r['kind'] for r in m.events),scratch_bytes=scratch,instructions=m.instructions,hardware_enqueue_executed=False)),flush=True)
fw.r.Firmware=old
