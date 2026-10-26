"""Actual target LTM IQ/DMI and retained conversion/Gamma references."""
from pathlib import Path
import ast,importlib.util,struct
from unicorn.arm64_const import *
HERE=Path(__file__).resolve().parent
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=module('ltm403',HERE.parent/'kernel403/ltm-model.py')
tree=ast.parse((HERE.parent/'kernel403/check-contract.py').read_text());fields=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='fields' for t in n.targets))
class Oracle(m.LTM):
 def iq(self,values):
  assert len(values)==22;packed={off:0 for off in [468,480,508,512,516,520,544]}
  for value,(_,offset,src,shift,width) in zip(values,fields):
   assert 0<=value<1<<width;packed[src]|=value<<shift
  obj=m.DATA+0x20000;inp=m.DATA+0x22000;iq=m.DATA+0x30000;sp=m.h.STACK+0xe0000;u=self.u
  u.mem_write(obj,bytes(1168));u.mem_write(inp,bytes(0x6000));u.mem_write(iq,bytes([0xa7])*2584);u.mem_write(iq+440,struct.pack('<I',1));u.mem_write(obj+12,struct.pack('<I',1));u.mem_write(inp+2584,struct.pack('<Q',iq));u.mem_write(sp+240,struct.pack('<2Q',obj,inp))
  for off,value in packed.items():u.mem_write(obj+off,struct.pack('<I',value))
  for reg,value in [(UC_ARM64_REG_X24,inp),(UC_ARM64_REG_X26,obj),(UC_ARM64_REG_SP,sp)]:u.reg_write(reg,value)
  u.emu_start(0x3669e0,0x366b4c,count=1000);assert u.reg_read(UC_ARM64_REG_PC)==0x366b4c
  return bytes(u.mem_read(iq+2096,92))
