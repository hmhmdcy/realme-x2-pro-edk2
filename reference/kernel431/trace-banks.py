"""Observe original firmware bank/reset serialization without MMIO access."""
from pathlib import Path
import importlib.util,json,struct
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R4,UC_ARM_REG_R6,UC_ARM_REG_R7,UC_ARM_REG_SP,UC_ARM_REG_PC
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
module('storage431',HERE.parent/'kernel284/storage.py').mounted_build()
fw=module('fw431',HERE.parent/'kernel429/firmware-model.py');original=fw.r.Firmware
class Trace(original):
 handle_type=2
 def __init__(self):
  super().__init__();self.controls=[];u=self.u;sp=0x020e0000;ctx=fw.f.DATA+0x180000
  u.reg_write(UC_ARM_REG_R4,self.handle_type);u.reg_write(UC_ARM_REG_SP,sp)
  u.emu_start(0x1c4de|1,0x1c4f6,count=40);assert u.reg_read(UC_ARM_REG_PC)==0x1c4f6
  kind=u.reg_read(UC_ARM_REG_R2);assert kind==(0 if self.handle_type==2 else 1)
  u.reg_write(UC_ARM_REG_R0,ctx);u.reg_write(UC_ARM_REG_R4,ctx);u.reg_write(UC_ARM_REG_R6,kind);u.reg_write(UC_ARM_REG_R7,0)
  u.emu_start(0xdb0e|1,0xdb1e,count=12);assert u.reg_read(UC_ARM_REG_PC)==0xdb1e
  assert self.read32(ctx)==kind;self.write32(self.context,kind)
 def step(self,u,pc,size,user):
  if pc==0x11f92:
   sp=u.reg_read(UC_ARM_REG_SP);p=self.read32(sp+188);policy=self.read32(sp+72)
   self.controls.append(dict(value=u.reg_read(UC_ARM_REG_R1),clear_field=struct.unpack('<H',u.mem_read(p+46,2))[0],dc_field=struct.unpack('<H',u.mem_read(p+390,2))[0],ip_field=struct.unpack('<H',u.mem_read(p+392,2))[0],policy_pointer=hex(policy),policy_value=self.read32(policy),configuration=hex(self.config)))
  return super().step(u,pc,size,user)
fw.r.Firmware=Trace;rows=[]
for handle_type,cores in [(2,1),(2,2),(3,1)]:
 Trace.handle_type=handle_type
 m,job,programs,scratch=fw.prepare((P.parent/'kernel430/actual-c-config-private.bin').read_bytes(),(P.parent/'kernel430/actual-c-stripe-private.bin').read_bytes(),(P.parent/'kernel424/coarse-width-640-dc-1-iq-private.bin').read_bytes(),cores)
 (P/f'banks-type-{handle_type}-cores-{cores}-private.json').write_text(json.dumps(m.controls,indent=2)+'\n')
 for r in m.controls:r.update(dc=(r['value']>>9)&1,ip=(r['value']>>10)&1,clear=(r['value']>>12)&1,dc_bank=(r['value']>>14)&1,ip_bank=(r['value']>>15)&1)
 rows.append(dict(handle_type=handle_type,cores=cores,controls=m.controls));print(json.dumps(rows[-1]),flush=True)
fw.r.Firmware=original
(P/'bank-trace-private.json').write_text(json.dumps(rows,indent=2)+'\n')
for row in rows:
 a,b=row['controls'];bank=int(row['handle_type']==3)
 assert (a['dc'],a['ip'],a['clear'],b['dc'],b['ip'],b['clear'])==(1,0,1,0,1,0)
 assert all(r['dc_bank']==r['ip_bank']==bank for r in [a,b])
r=dict(stage=431,scope='Original firmware serialization and handle creation fragments; no MMIO or SRAM readout',
 current_m2m_handle_type=2,real_time_handle_native_context_kind=0,real_time_dc_and_ip_bank=0,
 non_real_time_handle_native_context_kind=1,non_real_time_bank1_counterfactual_executed=True,
 original_handle_mapping_and_context_store_executed=True,
 first_coarse_pass_dc=True,first_coarse_pass_sum_clear=True,full_pass_ip=True,full_pass_sum_clear=False,
 whole_average_table_byte_readout=False,hardware_bank_readback=False,
 current_hardware_consumption_and_cold_warm_initialization_behavior_evidence='../kernel430/hardware-validation.json',passed=True)
(HERE/'bank-validation.json').write_text(json.dumps(r,indent=2)+'\n')
