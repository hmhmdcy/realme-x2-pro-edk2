"""Execute actual IPE metadata cache transport and LTM version selection gate."""
from pathlib import Path
import importlib.util,struct
from unicorn.arm64_const import *
spec=importlib.util.spec_from_file_location('policy415',Path(__file__).resolve().parent/'policy-model.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old);h=old.h
class MetadataMachine(old.PolicyMachine):
    def metadata(self,property,cache):
        assert len(cache)==4236 and (property is None or len(property)==4236)
        u=self.u;node=h.DATA+0x10000;container=node+0x14938;out=container+112;prop=h.DATA+0x40000;sp=h.STACK+0xd0000
        u.mem_write(node,bytes([0xa7])*0x17000);u.mem_write(out,cache)
        if property is not None:u.mem_write(prop,property)
        u.mem_write(sp+408,struct.pack('<Q',container));u.mem_write(0x96aac0+584,bytes(1))
        for reg,value in [(UC_ARM64_REG_X26,prop if property is not None else 0),(UC_ARM64_REG_X27,node),
                          (UC_ARM64_REG_X20,0x96aac0),(UC_ARM64_REG_SP,sp)]:u.reg_write(reg,value)
        self.stop_set={0x2e01f8};before=self.instructions
        u.emu_start(0x2dffe0,0x2e01f8,timeout=2000000,count=50000)
        assert u.reg_read(UC_ARM64_REG_PC)==0x2e01f8
        assert bytes(u.mem_read(out+4236,64))==bytes([0xa7])*64
        assert bytes(u.mem_read(out-112,112))==bytes([0xa7])*112
        if property is not None:assert bytes(u.mem_read(prop,4236))==property
        self.stop_set=set();return bytes(u.mem_read(out,4236)),self.instructions-before
    def ltm(self,record):
        rp,re,rl,version,up,ultm,changed=struct.unpack('<7I',record)
        u=self.u;obj=h.DATA+0x10000;root=obj+0x1000;inp=root+0x2000;adrc=inp+0x6000;sp=h.STACK+0xd0000
        u.mem_write(obj,bytes(1200));u.mem_write(root,bytes(120));u.mem_write(inp,bytes(0x5000));u.mem_write(adrc,bytes(4236))
        u.mem_write(obj+1160,struct.pack('<Q',root if rp else 0));u.mem_write(root+8,struct.pack('<I',re));u.mem_write(root+68,struct.pack('<I',rl))
        u.mem_write(inp+3016,struct.pack('<I',version));u.mem_write(inp+3024,struct.pack('<Q',adrc if up else 0));u.mem_write(adrc+12,struct.pack('<I',ultm))
        u.mem_write(sp+240,struct.pack('<Q',obj));u.mem_write(sp+248,struct.pack('<Q',inp));u.mem_write(0x96aac0+584,bytes(1))
        for reg,value in [(UC_ARM64_REG_X26,obj),(UC_ARM64_REG_X24,inp),(UC_ARM64_REG_X20,0x96aac0),
                          (UC_ARM64_REG_W22,changed),(UC_ARM64_REG_SP,sp)]:u.reg_write(reg,value)
        self.stop_set={0x363994,0x35e9dc};before=self.instructions
        u.emu_start(0x360088,h.STOP,timeout=2000000,count=50000)
        pc=u.reg_read(UC_ARM64_REG_PC);assert pc in self.stop_set,hex(pc)
        own=pc==0x363994;ltm=self.read32(obj+92);change=u.reg_read(UC_ARM64_REG_W22)
        if not own:assert self.read64(obj+96)==(adrc if up else 0)
        self.stop_set=set();return struct.pack('<3I',0 if own else 1 if up else 2,ltm,change),self.instructions-before
