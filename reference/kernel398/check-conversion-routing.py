"""Verify conversion contracts using bounded target HAL and firmware execution.

Full CST calculation and CDM packet encoding execute unchanged. CV numerical
OEM code is a bounded fragment, not a claim of complete Execute/interpolation.
"""
from pathlib import Path
import importlib.util,json,math,random,struct
from unicorn.arm64_const import *
from unicorn.arm_const import UC_ARM_REG_R9,UC_ARM_REG_R5,UC_ARM_REG_PC as FW_PC
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
h=module('hal380',HERE.parent/'kernel380/hal-machine.py');fw=module('fw383',HERE.parent/'kernel383/firmware-model.py')
D=h.DATA
class Conversion(h.Machine):
 def step(self,u,pc,size,user):
  if pc in [0x4cd8b0,0x4cda68]:
   self.instructions+=1;self.providers[hex(pc)]=self.providers.get(hex(pc),0)+1
   assert u.reg_read(UC_ARM64_REG_X0)==D+0xa000
   if pc==0x4cd8b0:
    assert u.reg_read(UC_ARM64_REG_W1) in [10,14];result=D+0xb000
   else:result=0
   u.reg_write(UC_ARM64_REG_X0,result);u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR));return
  return super().step(u,pc,size,user)
 def bounded(self,start,end):
  self.u.emu_start(start,end,timeout=1000000,count=10000);assert self.u.reg_read(UC_ARM64_REG_PC)==end

a=Conversion();u=a.u;f32=lambda x:struct.unpack('<f',struct.pack('<f',x))[0]
roundaway=lambda x:math.floor(x+.5) if x>=0 else math.ceil(x-.5)
clamp=lambda x,lo,hi:min(max(x,lo),hi)
cases=[];rng=random.Random(398)
for i in range(96):
 matrix=[rng.randint(-8192,8192)/1024 for _ in range(9)]
 offset=[rng.randint(-2000,2000) for _ in range(3)];subtract=[rng.randint(-2000,2000) for _ in range(3)]
 low=[rng.randint(0,1500) for _ in range(3)];high=[rng.randint(0,1500) for _ in range(3)]
 cases.append((matrix,offset,subtract,low,high))
for i in range(9):
 for n in [-4096,-1,0,1,4095]:
  mat=[0.]*9;mat[i]=n/1024;cases.append((mat,[0]*3,[0]*3,[0]*3,[1023]*3))
for matrix,offset,subtract,low,high in cases:
 override=D+0x1000;out=D+0x5000;regs=D+0x6000
 u.mem_write(D,bytes(256));u.mem_write(override,bytes(0x3000));u.mem_write(regs,bytes(64))
 u.mem_write(override+4160,struct.pack('<6I9f6i',*low,*high,*matrix,*offset,*subtract));u.mem_write(out,struct.pack('<IIQ',2,0,regs))
 assert a.call(0x37b4d8,D,override,out,phase='actual-ipe-cst-type2')==0
 words=[];q=[clamp(roundaway(f32(x*1024)),-4096,4095) for x in matrix]
 for channel in range(3):
  words.extend([(q[channel*3]&0x1fff)|((q[channel*3+1]&0x1fff)<<16),q[channel*3+2]&0x1fff,(clamp(subtract[channel],-1024,1023)&0x7ff)|(clamp(offset[channel],0,1023)<<16),clamp(low[channel],0,1023)|(clamp(high[channel],0,1023)<<16)])
 actual=bytes(u.mem_read(regs,48));assert actual==struct.pack('<12I',*words)
 assert bytes(u.mem_read(regs+48,16))==bytes(16)
 (P/'cst-last-registers-private.bin').write_bytes(actual)

# Module fragments call the real packet encoder and update the exact IQ field.
routes=[]
for name,objreg,datareg,start,end,regstart,count,regoffset,iqoffset,index in [
 ('CST',UC_ARM64_REG_X20,UC_ARM64_REG_X19,0x35024c,0x350284,0x5a68,12,64,2092,3),
 ('CV',UC_ARM64_REG_X19,UC_ARM64_REG_X20,0x34cfa0,0x34cfe0,0x6468,8,112,2200,4)]:
 for enabled in [0,1]:
  obj=D+0xc000;data=D+0xd000;array=D+0x14000;iq=D+0x15000
  for p,n in [(obj,1024),(data,0x6000),(array,128),(iq,2584)]:u.mem_write(p,bytes(n))
  registers=bytes(range(count*4));u.mem_write(obj+12,struct.pack('<I',enabled));u.mem_write(obj+regoffset,registers)
  u.mem_write(data+2584,struct.pack('<Q',iq));u.mem_write(data+2600,struct.pack('<Q',array));u.mem_write(array+index*8,struct.pack('<Q',D+0xa000));u.mem_write(D+0xb000,bytes([0xa7])*64)
  u.reg_write(objreg,obj);u.reg_write(datareg,data);a.bounded(start,end)
  assert a.read32(iq+iqoffset)==enabled
  expected=struct.pack('<II',0x03000000|count,regstart)+registers if enabled else bytes([0xa7])*(8+4*count)
  assert bytes(u.mem_read(D+0xb000,len(expected)))==expected
  routes.append(dict(module=name,enabled=enabled,iq_offset=iqoffset,register_range=regstart,register_words=count,command_buffer_index=index,passed=True))

fwrows=[]
for name,offset,start,end,output,register in [('CST',2092,0x114c5,0x114d4,8,0x5a60),('CV',2200,0x11505,0x11514,40,0x6460)]:
 for value in [0,1,2,3,0xffffffff]:
  b=fw.Machine();v=b.u;v.mem_write(fw.DATA,bytes(2584));v.mem_write(fw.DATA+offset,struct.pack('<I',value));v.mem_write(fw.DATA+0x10000,bytes(64))
  v.reg_write(UC_ARM_REG_R9,fw.DATA);v.reg_write(UC_ARM_REG_R5,fw.DATA+0x10000)
  v.emu_start(start,end,timeout=1000000,count=20);assert v.reg_read(FW_PC)==end
  assert struct.unpack('<2I',v.mem_read(fw.DATA+0x10000+output,8))==(register,value&1)
  fwrows.append(dict(module=name,iq_value=value,register=register,register_value=value&1,passed=True))
report=dict(stage=398,cst_complete_original_calculation_cases=len(cases),cst_output_type=2,cst_matrix_signed_bits=13,cst_matrix_fractional_bits=10,cst_subtract_signed_bits=11,cst_add_offset_unsigned_max=1023,cst_clamp_unsigned_bits=10,hal_module_fragment_cases=routes,firmware_enable_fragment_cases=fwrows,cv_iq_offset=2200,cv_enable_register=0x6460,cv_data_register=0x6468,previous_tentative_cv_iq2196_identification_withdrawn=True,complete_conversion_execute_not_claimed=True,colour_domain_not_hardware_established=True,phone_changed=False,passed=True)
(HERE/'conversion-routing-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
