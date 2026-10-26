"""Execute target TMC11 normalization, fixed65 PCHIP and contrast sampling."""
from pathlib import Path
import importlib.util,struct
from unicorn.arm64_const import *
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('curve407',HERE.parent/'kernel407/curve-model.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old);h=old.h
GLOBAL=0x5bf2b0
class Tmc11Machine(old.CurveMachine):
    def step(self,u,pc,size,user):
        if pc==getattr(self,'stop_pc',None):u.emu_stop();return
        return super().step(u,pc,size,user)

    def axis(self):return bytes(self.u.mem_read(0xd8ed8,4096))

    def normalize(self,equivalent,curve):
        u=self.u;adrc=h.DATA+0x10000;sp=h.STACK+0xe0000
        u.mem_write(GLOBAL+1840,equivalent);u.mem_write(GLOBAL+2112,bytes([0xa7])*256)
        assert struct.unpack('<f',u.mem_read(GLOBAL+2112+256,4))[0]==1
        u.mem_write(adrc,bytes(4240));u.mem_write(adrc+16,curve[:40]);u.mem_write(adrc+4224,struct.pack('<I',2))
        u.mem_write(sp,bytes(0x4000))
        for r,v in [(UC_ARM64_REG_SP,sp),(UC_ARM64_REG_X23,GLOBAL),(UC_ARM64_REG_X11,adrc),(UC_ARM64_REG_W21,0x457ff000)]:u.reg_write(r,v)
        self.stop_pc=0x3626dc;u.emu_start(0x362588,self.stop_pc,timeout=1000000,count=2000)
        assert u.reg_read(UC_ARM64_REG_PC)==self.stop_pc
        assert bytes(u.mem_read(GLOBAL+1840,260))==equivalent
        return bytes(u.mem_read(GLOBAL+2112,260)),bytes(u.mem_read(sp+256,4))

    def pchip(self,curve,normalized):
        u=self.u;p=h.DATA+0x20000;out=p+0x2000
        u.mem_write(p,curve);u.mem_write(p+0x100,normalized);u.mem_write(out,bytes([0xa7])*292)
        self.stop_pc=h.STOP;self.call(0x3c7070,p,p+20,p+40,p+0x100,out)
        assert bytes(u.mem_read(p,76))==curve and bytes(u.mem_read(p+0x100,260))==normalized
        assert bytes(u.mem_read(out+260,32))==bytes([0xa7])*32
        return bytes(u.mem_read(out,260))

    def contrast(self,normalized,gain,parameters,contrast):
        u=self.u;p=h.DATA+0x30000;g=p+0x1000;adrc=p+0x2000
        u.mem_write(p,normalized);u.mem_write(g,gain+bytes([0xa7])*32);u.mem_write(adrc,bytes(4240))
        u.mem_write(adrc+128,contrast);u.mem_write(adrc+4228,parameters[4:12])
        u.reg_write(UC_ARM64_REG_S0,struct.unpack_from('<I',parameters)[0])
        self.stop_pc=h.STOP;self.call(0x3c7c98,p,g,adrc,10,3)
        assert bytes(u.mem_read(p,260))==normalized and bytes(u.mem_read(adrc+128,4096))==contrast
        assert bytes(u.mem_read(g+260,32))==bytes([0xa7])*32
        return bytes(u.mem_read(g,260))
