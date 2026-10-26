"""Execute original configuration and frame preparation, recording stripe reads."""
from pathlib import Path
import importlib.util,json,struct,sys
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_READ
from unicorn.arm_const import UC_ARM_REG_PC,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_CPSR,UC_ARM_REG_R0
spec=importlib.util.spec_from_file_location('firmware_model',Path(__file__).resolve().parent/'firmware-model.py');f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
P=f.P;D=f.DATA;model=f.Machine();model.call(0x7998,phase='chip-info')
model.payload=D+0x10000;model.write32(model.payload,5);model.u.mem_write(model.payload+8,(P.parent/'kernel380/640x480-port8-cores1-config-private.bin').read_bytes());model.write32(D,D+0xc000)
assert model.call(0x16534,D,phase='config')==0
frame=bytearray((P.parent/'kernel380/640x480-port8-cores1-encoded-frame-private.bin').read_bytes())
stripe=D+0x30000;iq=D+0x40000;bl=D+0x60000
struct.pack_into('<4I',frame,0,stripe,iq,D+0x45000,48);struct.pack_into('<II',frame,24,bl,156512-32)
model.u.mem_write(stripe,(P.parent/'kernel380/640x480-port8-cores1-stripe-private.bin').read_bytes())
model.u.mem_write(iq,(P.parent/'kernel382/hal-default-ica-iq-private.bin').read_bytes())
model.payload=D+0x20000;model.write32(model.payload,6);model.u.mem_write(model.payload+8,bytes(frame));reads={}
def reading(u,access,address,size,value,user):
 if address<stripe+3516 and address+size>stripe:
  pc=u.reg_read(UC_ARM_REG_PC)
  for off in range(max(address,stripe)-stripe,min(address+size,stripe+3516)-stripe):reads.setdefault(off,set()).add(pc)
if '--no-reads' not in sys.argv:model.u.hook_add(UC_HOOK_MEM_READ,reading,begin=stripe,end=stripe+3516-1)
stack_rows=[]
def checkpoints(u,pc,size,user):
 if pc in [0x1059e,0x10676,0x1067a,0xe142,0xe156,0xf21e,0xf232,0xf26a,0xf274]:
  sp=u.reg_read(UC_ARM_REG_SP);stack_rows.append(dict(pc=hex(pc),sp=hex(sp),lr=hex(u.reg_read(UC_ARM_REG_LR)),cpsr=hex(u.reg_read(UC_ARM_REG_CPSR)),r0=hex(u.reg_read(UC_ARM_REG_R0)),words=struct.unpack('<10I',u.mem_read(sp,40))))
model.u.hook_add(UC_HOOK_CODE,checkpoints)
try:
 ret=model.call(0x17f30,D,phase='frame-preparation-prefix',stop=0x181be if '--full' not in sys.argv else 0x220a2);assert ret==0
 print(json.dumps(dict(stopped_at=hex(model.u.reg_read(UC_ARM_REG_PC)),stopped_before_hardware_enqueue='--full' in sys.argv,instructions=model.instructions,providers=model.providers,allocations=model.allocated,stripe_read_bytes=len(reads),payload_status=model.read32(model.payload+4),packet_headers=[p[:40].hex() for p in model.packets])))
finally:
 (P/'engine-stripe-reads-private.json').write_text(json.dumps({str(k):sorted(v) for k,v in reads.items()})+'\n')
 (P/'engine-model-state-private.json').write_text(json.dumps(dict(phase=model.phase,instructions=model.instructions,providers=model.providers,allocations=model.allocated,fault=model.fault))+'\n')
 (P/'engine-stack-checkpoints-private.json').write_text(json.dumps(stack_rows,indent=2)+'\n')
 (P/'free-trace-private.json').write_text(json.dumps(model.free_trace)+'\n')
 (P/'free-code-private.bin').write_bytes(model.u.mem_read(0xf21e,0x60))
 (P/'engine-logs-private.json').write_text(json.dumps(model.logs,indent=2)+'\n')
 (P/'engine-bl-private.bin').write_bytes(model.u.mem_read(bl,156512))
