"""Execute corrected IPE input binding and actual AEC-to-HDR trigger arithmetic."""
from pathlib import Path
import importlib.util,struct
from unicorn.arm64_const import *
spec=importlib.util.spec_from_file_location('metadata415',Path(__file__).resolve().parents[1]/'kernel415/metadata-model.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old);h=old.h
class BindingMachine(old.MetadataMachine):
    def binding(self,version,initial):
        u=self.u;sp=h.STACK+0xd0000;inp=sp+0x340;container=h.DATA+0x10000;node=h.DATA+0x20000
        u.mem_write(inp-64,bytes([0xa7])*(19928+128));u.mem_write(sp+408,struct.pack('<Q',container))
        u.reg_write(UC_ARM64_REG_SP,sp);self.stop_set={0x2cf514};before=self.instructions
        u.emu_start(0x2cf504,0x2cf514,count=1000)
        assert bytes(u.mem_read(inp,19928))==bytes(19928)
        assert bytes(u.mem_read(inp-64,64))==bytes([0xa7])*64
        assert bytes(u.mem_read(inp+19928,64))==bytes([0xa7])*64
        u.mem_write(container,bytes(4480));u.mem_write(container+116,struct.pack('<I',version))
        u.mem_write(inp+3016,struct.pack('<I',initial));u.mem_write(node+8296,bytes(8))
        for reg,value in [(UC_ARM64_REG_X24,sp+0x240),(UC_ARM64_REG_X27,node)]:u.reg_write(reg,value)
        self.stop_set={0x2d6590};u.emu_start(0x2d6564,0x2d6590,count=1000)
        assert self.read64(inp+3024)==container+112
        out=struct.pack('<2I',self.read32(inp+3016),1)
        self.stop_set=set();return out,self.instructions-before
    def hdr(self,record):
        assert len(record)==32
        t0,t1,g0,g1,s0,s1=struct.unpack('<2Q4f',record);u=self.u
        inp=h.DATA+0x10000;aec=inp+0x8000;sp=h.STACK+0xd0000
        frame=bytearray(72);struct.pack_into('<Q2f',frame,0,t0,g0,s0);struct.pack_into('<Q2f',frame,24,t1,g1,s1)
        u.mem_write(inp,bytes(19928));u.mem_write(inp,struct.pack('<Q',aec));u.mem_write(aec,bytes(frame))
        for reg,value in [(UC_ARM64_REG_X0,inp),(UC_ARM64_REG_X1,0),(UC_ARM64_REG_SP,sp)]:u.reg_write(reg,value)
        self.stop_set={0x3771b8};before=self.instructions
        u.emu_start(0x377120,0x3771b8,count=1000)
        assert bytes(u.mem_read(aec,len(frame)))==frame
        out=bytes(u.mem_read(inp+2872,12));self.stop_set=set();return out,self.instructions-before
