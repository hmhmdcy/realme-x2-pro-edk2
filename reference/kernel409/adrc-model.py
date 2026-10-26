"""Execute original sampled-gain conversion and following curve/scale blend."""
from pathlib import Path
import importlib.util,struct
from unicorn.arm64_const import *
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('hal380',HERE.parent/'kernel380/hal-machine.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
GLOBAL=0x5bf2b0
class AdrcMachine(h.Machine):
    def step(self,u,pc,size,user):
        if pc==getattr(self,'stop_pc',None):u.emu_stop();return
        return super().step(u,pc,size,user)

    def evaluate(self,record):
        assert len(record)==1176
        u=self.u;sp=h.STACK+0xe0000;obj=h.DATA+0x10000;reserve=h.DATA+0x20000
        u.mem_write(sp,bytes(0x4000));u.mem_write(obj,bytes(1024));u.mem_write(reserve,bytes(1024))
        u.mem_write(GLOBAL+1840,record[:260])
        u.mem_write(obj+168,record[520:780])
        u.mem_write(sp+8304,record[260:520])
        u.mem_write(sp+104,struct.pack('<Q',reserve))
        u.mem_write(sp+160,struct.pack('<Q',obj+168+48))
        u.mem_write(sp+168,struct.pack('<Q',obj+168+96))
        u.mem_write(sp+176,struct.pack('<4f',64,64,64,64))
        u.mem_write(sp+192,struct.pack('<Q',obj+168))
        u.mem_write(sp+224,struct.pack('<Q',reserve+428))
        u.mem_write(sp+256,record[780:784]+bytes(12))
        u.mem_write(reserve+428,record[784:1044])
        u.mem_write(sp+9216,record[1044:1174])
        for r,value in [(UC_ARM64_REG_SP,sp),(UC_ARM64_REG_X22,obj),
                        (UC_ARM64_REG_X23,GLOBAL),(UC_ARM64_REG_X28,reserve),
                        (UC_ARM64_REG_W21,0x457ff000)]:u.reg_write(r,value)
        before=self.instructions;self.stop_pc=0x3642d4
        u.emu_start(0x362774,self.stop_pc,timeout=3000000,count=200000)
        assert u.reg_read(UC_ARM64_REG_PC)==self.stop_pc,hex(u.reg_read(UC_ARM64_REG_PC))
        curves=bytes(u.mem_read(sp+7760,260))+bytes(u.mem_read(sp+8032,260))
        self.stop_pc=0x364598
        u.emu_start(0x3642d4,self.stop_pc,timeout=1000000,count=30000)
        assert u.reg_read(UC_ARM64_REG_PC)==self.stop_pc
        blended=bytes(u.mem_read(sp+8576,260))+bytes(u.mem_read(sp+9216,130))
        assert bytes(u.mem_read(obj+168,260))==record[520:780]
        assert bytes(u.mem_read(reserve+428,260))==record[784:1044]
        return struct.pack('<I',1)+curves+struct.pack('<I',1)+blended,self.instructions-before
