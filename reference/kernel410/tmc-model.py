"""Execute target LTM's fixed65-node/Q10 TMC10 sampler and mix fragment."""
from pathlib import Path
import importlib.util,struct
from unicorn.arm64_const import *
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('curve407',HERE.parent/'kernel407/curve-model.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
h=old.h
class TmcMachine(old.CurveMachine):
    def step(self,u,pc,size,user):
        if pc==getattr(self,'stop_pc',None):u.emu_stop();return
        return super().step(u,pc,size,user)
    def sample(self,curve,equivalent):
        assert len(curve)==72 and len(equivalent)==260
        p=h.DATA+0x10000;out=h.DATA+0x12000
        self.u.mem_write(p,curve[:56]);self.u.mem_write(p+0x100,equivalent)
        self.u.mem_write(out,bytes([0xa7])*292)
        self.u.reg_write(UC_ARM64_REG_S0,struct.unpack_from('<I',curve,60)[0])
        self.u.reg_write(UC_ARM64_REG_S1,struct.unpack_from('<I',curve,56)[0])
        self.stop_pc=h.STOP
        # Target specialization has lutSize64 folded, and qFactor in W5.
        # The specialized target has no BOOL write before RET and the real
        # caller ignores W0. Completion and output, not a source BOOL, prove it.
        self.call(0x3c6328,p,p+16,p+32,p+0x100,out,10)
        assert bytes(self.u.mem_read(out+260,32))==bytes([0xa7])*32
        assert bytes(self.u.mem_read(p,56))==curve[:56] and bytes(self.u.mem_read(p+0x100,260))==equivalent
        return bytes(self.u.mem_read(out,260))
    def mix(self,dark_gain,percentage):
        u=self.u;p=h.DATA+0x20000;sp=h.STACK+0xe0000
        u.mem_write(p,bytes(256));u.mem_write(p+56,struct.pack('<f',dark_gain));u.mem_write(p+64,struct.pack('<f',percentage))
        u.mem_write(sp,bytes(0x3000))
        for r,v in [(UC_ARM64_REG_X11,p),(UC_ARM64_REG_X23,0x5bf2b0),(UC_ARM64_REG_SP,sp)]:u.reg_write(r,v)
        self.stop_pc=0x36273c
        u.emu_start(0x3626f8,self.stop_pc,count=2000)
        assert u.reg_read(UC_ARM64_REG_PC)==self.stop_pc
        return bytes(u.mem_read(sp+256,4))
