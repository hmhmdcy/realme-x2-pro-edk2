"""Target scalar/weight and unsigned-LUT fragments, with memory providers only."""
from pathlib import Path
import importlib.util,struct
from unicorn.arm64_const import *
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('hal380',HERE.parent/'kernel380/hal-machine.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
class StaticMachine(h.Machine):
    def step(self,u,pc,size,user):
        if pc==getattr(self,'stop_pc',None):u.emu_stop();return
        return super().step(u,pc,size,user)
    def run(self,start,end):
        self.stop_pc=end
        self.u.emu_start(start,end,timeout=2000000,count=30000)
        assert self.u.reg_read(UC_ARM64_REG_PC)==end,hex(self.u.reg_read(UC_ARM64_REG_PC))
    def pack(self,nodes):
        u=self.u;sp=h.STACK+0xe0000;source=h.DATA+0x50000;out=h.DATA+0x52000
        u.mem_write(source,struct.pack('<65i',*nodes));u.mem_write(out,bytes([0xa5])*288)
        u.mem_write(sp+440,struct.pack('<Q',out));u.mem_write(sp+8848,struct.pack('<i',nodes[0]))
        u.reg_write(UC_ARM64_REG_SP,sp);u.reg_write(UC_ARM64_REG_X19,source+16)
        self.run(0x365278,0x365444)
        assert bytes(u.mem_read(out+256,32))==bytes([0xa5])*32
        return bytes(u.mem_read(out,256))
    def evaluate(self,record):
        assert len(record)==684
        rgb=record[:16];y=record[16:20];flags=struct.unpack_from('<5I',record,20)
        weights=record[40:136];kernels=record[136:160];mask=struct.unpack_from('<65i',record,160)
        la=struct.unpack_from('<65f',record,420);threshold=struct.unpack_from('<I',record,680)[0]
        u=self.u;sp=h.STACK+0xe0000;reserve=h.DATA+0x10000;region=h.DATA+0x20000
        obj=h.DATA+0x30000;constants=h.DATA+0x40000;out=h.DATA+0x60000
        for address,size in [(sp,0x4000),(reserve,1024),(region,1024),(obj,2048),(constants,8192),(out,512)]:u.mem_write(address,bytes(size))
        u.mem_write(reserve+32,rgb);u.mem_write(region+656,y)
        u.mem_write(constants+1360,struct.pack('<4I',63,63,63,64))
        u.mem_write(obj+112,struct.pack('<3H',640,0,480))
        u.mem_write(sp+240,struct.pack('<Q',obj))
        for reg,value in [(UC_ARM64_REG_SP,sp),(UC_ARM64_REG_X2,reserve),(UC_ARM64_REG_X25,constants),
                          (UC_ARM64_REG_X26,constants),(UC_ARM64_REG_X13,constants),(UC_ARM64_REG_X23,region),
                          (UC_ARM64_REG_X8,constants+4096),(UC_ARM64_REG_W1,1023)]:u.reg_write(reg,value)
        u.reg_write(UC_ARM64_REG_Q22,int.from_bytes(struct.pack('<4f',64,64,64,64),'little'))
        u.reg_write(UC_ARM64_REG_Q23,0)
        self.run(0x360c3c,0x360cc8)
        rgb_actual=struct.unpack('<4H',u.mem_read(sp+392,8));y_actual=self.read32(sp+552)>>16
        u.mem_write(reserve+12,struct.pack('<3I',flags[0],flags[1],flags[2]))
        u.mem_write(reserve+48,weights);u.mem_write(reserve+144,kernels)
        u.mem_write(reserve+688,struct.pack('<I',threshold))
        u.mem_write(sp+104,struct.pack('<Q',reserve));u.mem_write(sp+80,struct.pack('<Q',out))
        u.mem_write(sp+400,struct.pack('<Q',out))
        u.reg_write(UC_ARM64_REG_X21,region+260);u.reg_write(UC_ARM64_REG_X23,out)
        self.run(0x360f90,0x3612d4)
        weight_actual=bytes(u.mem_read(out,48));kernel_actual=struct.unpack('<6H',u.mem_read(sp+416,12))
        scale,shift=struct.unpack('<2H',u.mem_read(sp+428,4))
        ig,adapt=struct.unpack('<2H',u.mem_read(sp+386,4));mask_en=struct.unpack('<H',u.mem_read(sp+432,2))[0]
        self.run(0x365444,0x365470);lce=struct.unpack('<H',u.mem_read(sp+552,2))[0]
        values=(*rgb_actual,y_actual,ig,adapt,mask_en,int(bool(flags[3])),int(bool(flags[4])),*kernel_actual,scale,shift,lce)
        la_int=[int(v+.5) for v in la]
        return struct.pack('<19I',*values)+weight_actual+self.pack(mask)+self.pack(la_int)
