"""Execute the target TMC10 knee/percentage block after region interpolation."""
from pathlib import Path
import ctypes,importlib.util,struct
from unicorn.arm64_const import *
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('tmc410',HERE.parent/'kernel410/tmc-model.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
h=old.h
libm=ctypes.CDLL('libm.so.6');libm.logf.argtypes=[ctypes.c_float];libm.logf.restype=ctypes.c_float
class KneeMachine(old.TmcMachine):
    def step(self,u,pc,size,user):
        if pc==0x5b12c0:
            self.instructions+=1;self.providers[hex(pc)]=self.providers.get(hex(pc),0)+1
            v=struct.unpack('<f',struct.pack('<I',u.reg_read(UC_ARM64_REG_S0)))[0]
            u.reg_write(UC_ARM64_REG_S0,struct.unpack('<I',struct.pack('<f',libm.logf(v)))[0])
            u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR));return
        return super().step(u,pc,size,user)

    def knees(self,parameters):
        assert len(parameters)==28
        p=struct.unpack('<7f',parameters);u=self.u;sp=h.STACK+0xe0000
        inp=h.DATA+0x30000;root=inp+0x1000;region=root+0x1000;out=region+0x1000
        ib=struct.pack('<Q2f',root,p[0],p[1])+bytes(16)+struct.pack('<Q',out)
        rb=struct.pack('<11f',p[2],p[3],0,0,p[4],p[5],p[6],0,0,0,0)
        u.mem_write(sp,bytes(0x1000));u.mem_write(inp,ib);u.mem_write(root,bytes(128))
        u.mem_write(root+8,struct.pack('<I',1));u.mem_write(root+64,struct.pack('<2I',1,1))
        u.mem_write(region,rb);u.mem_write(out,bytes([0xa7])*128)
        u.mem_write(sp+104,struct.pack('<Q',region))
        for r,v in [(UC_ARM64_REG_SP,sp),(UC_ARM64_REG_X29,sp+480),(UC_ARM64_REG_X19,inp)]:u.reg_write(r,v)
        self.stop_pc=0x377d50
        u.emu_start(0x377a08,self.stop_pc,timeout=1000000,count=10000)
        assert u.reg_read(UC_ARM64_REG_PC)==self.stop_pc
        assert bytes(u.mem_read(inp,len(ib)))==ib and bytes(u.mem_read(region,len(rb)))==rb
        assert bytes(u.mem_read(out+92,36))==bytes([0xa7])*36
        curve=bytes(u.mem_read(out+16,16))+bytes(u.mem_read(out+32,16))+bytes(u.mem_read(out+68,24))
        dark=bytes(u.mem_read(out+56,4));pct=bytes(u.mem_read(out+64,4));gtm=bytes(u.mem_read(out+60,4))
        return curve+dark+pct+gtm+self.mix(struct.unpack('<f',dark)[0],struct.unpack('<f',pct)[0])

    def tree(self,root_data,lux,real_gain,drc_gain,dark_gain,control=None):
        u=self.u;inp=h.DATA+0x40000;root=inp+0x1000;leaves=root+0x1000;out=leaves+0x4000
        rb=bytearray(120);struct.pack_into('<I',rb,8,root_data['enabled'])
        struct.pack_into('<I',rb,60,root_data['control_method'] if control is None else control)
        struct.pack_into('<2I',rb,64,root_data['reserve']['use_gtm'],root_data['reserve']['use_ltm'])
        struct.pack_into('<I',rb,104,len(root_data['core']));struct.pack_into('<Q',rb,112,leaves)
        names=['gtm_percentage','ltm_percentage','la_percentage','gamma_percentage','knee_out_mid',
               'dark_boost_ratio',*['core_rsv_para'+str(i) for i in range(1,6)]]
        lb=b''.join(struct.pack('<15f',*row['trigger'],*[row['data'][n] for n in names]) for row in root_data['core'])
        # Target TMC10InputData has realGain at+16 and luxIndex at+20.
        ib=struct.pack('<Q4fQ',root,drc_gain,dark_gain,real_gain,lux,0)+struct.pack('<Q',out)
        u.mem_write(inp,ib);u.mem_write(root,bytes(rb));u.mem_write(leaves,lb);u.mem_write(out,bytes([0xa7])*128)
        self.stop_pc=h.STOP;ret=self.call(0x3774b0,inp,phase='whole TMC10 interpolation and knee generation')
        assert ret==1,ret
        assert bytes(u.mem_read(inp,len(ib)))==ib and bytes(u.mem_read(root,len(rb)))==rb and bytes(u.mem_read(leaves,len(lb)))==lb
        assert bytes(u.mem_read(out+92,36))==bytes([0xa7])*36
        interpolated=bytes(u.mem_read(h.STACK+0xf0000-608,44))
        frame=h.STACK+0xf0000-608;children=struct.unpack('<I',u.mem_read(frame+80,4))[0]
        assert children in [1,2]
        first=struct.unpack('<Q',u.mem_read(frame+168,8))[0]
        last=struct.unpack('<Q',u.mem_read(frame+240,8))[0] if children==2 else first
        assert (first-leaves)%60==0 and (last-leaves)%60==0
        self.last_selection=struct.pack('<2I',int((first-leaves)//60),int((last-leaves)//60))+(bytes(u.mem_read(frame+84,4)) if children==2 else bytes(4))
        curve=bytes(u.mem_read(out+16,16))+bytes(u.mem_read(out+32,16))+bytes(u.mem_read(out+68,24))
        dark=bytes(u.mem_read(out+56,4));pct=bytes(u.mem_read(out+64,4));gtm=bytes(u.mem_read(out+60,4))
        return interpolated,curve+dark+pct+gtm+self.mix(struct.unpack('<f',dark)[0],struct.unpack('<f',pct)[0])
