"""Execute target TMC11 generation after interpolation, including histogram math."""
from pathlib import Path
import ctypes,importlib.util,struct
from unicorn.arm64_const import *
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('knee411',HERE.parent/'kernel411/knee-model.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old);h=old.h
libm=ctypes.CDLL('libm.so.6');libm.expf.argtypes=[ctypes.c_float];libm.expf.restype=ctypes.c_float
class GenerationMachine(old.KneeMachine):
    def default_gamma(self,fill):
        u=self.u;obj=h.DATA+0x60000;u.mem_write(obj,bytes([fill])*1152)
        u.reg_write(UC_ARM64_REG_X19,obj);self.stop_pc=0x383a28
        u.emu_start(0x38396c,self.stop_pc,timeout=1000000,count=2000)
        assert u.reg_read(UC_ARM64_REG_PC)==self.stop_pc
        return bytes(u.mem_read(obj+112,1028))

    def step(self,u,pc,size,user):
        if pc==0x5b1980:
            self.instructions+=1;self.providers[hex(pc)]=self.providers.get(hex(pc),0)+1
            v=struct.unpack('<f',struct.pack('<I',u.reg_read(UC_ARM64_REG_S0)))[0]
            u.reg_write(UC_ARM64_REG_S0,struct.unpack('<I',struct.pack('<f',libm.expf(v)))[0])
            u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR));return
        return super().step(u,pc,size,user)

    def generate(self,region,gains,gamma,histogram=None):
        assert len(region)==176 and len(gains)==8 and len(gamma)==1028
        u=self.u;sp=h.STACK+0xd0000;obj=h.DATA+0x40000;root=obj+0x2000;out=root+0x2000;hist=out+0x4000
        ib=bytearray(1152);struct.pack_into('<Q',ib,64,root);ib[72:80]=gains
        struct.pack_into('<2Q',ib,96,hist if histogram is not None else 0,out);ib[112:1140]=gamma
        rb=bytearray(160);struct.pack_into('<I',rb,8,1);struct.pack_into('<4I',rb,76,1,1,2,5)
        u.mem_write(sp,bytes(0x6000));u.mem_write(sp+64,region)
        u.mem_write(obj,bytes(ib));u.mem_write(root,bytes(rb));u.mem_write(out,bytes([0xa7])*4288)
        if histogram is not None:
            assert len(histogram)==4096;u.mem_write(hist,histogram)
        # X23 is the interpolated-region base at SP+64, not SP itself.
        for r,v in [(UC_ARM64_REG_SP,sp),(UC_ARM64_REG_X23,sp+64),(UC_ARM64_REG_X19,obj),
                    (UC_ARM64_REG_X24,obj+112)]:u.reg_write(r,v)
        self.stop_pc=0x38565c;before=self.instructions
        u.emu_start(0x384048,self.stop_pc,timeout=5000000,count=2000000)
        assert u.reg_read(UC_ARM64_REG_PC)==self.stop_pc,hex(u.reg_read(UC_ARM64_REG_PC))
        assert bytes(u.mem_read(obj,len(ib)))==ib and bytes(u.mem_read(root,len(rb)))==rb
        if histogram is not None:assert bytes(u.mem_read(hist,4096))==histogram
        assert bytes(u.mem_read(out+4236,52))==bytes([0xa7])*52
        return dict(adrc=bytes(u.mem_read(out,4236)),region=bytes(u.mem_read(sp+64,176)),
                    processed_hist=bytes(u.mem_read(sp+3792,4096)),instructions=self.instructions-before)
