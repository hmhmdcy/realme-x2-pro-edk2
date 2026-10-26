"""Execute actual TMC11 dependence/update/version prefix, stopping before math."""
from pathlib import Path
import importlib.util,struct
from unicorn.arm64_const import *
spec=importlib.util.spec_from_file_location('generation413',Path(__file__).resolve().parents[1]/'kernel413/generation-model.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old);h=old.h
class PolicyMachine(old.GenerationMachine):
    def step(self,u,pc,size,user):
        if pc in getattr(self,'stop_set',set()):u.emu_stop();return
        return super().step(u,pc,size,user)
    def policy(self,record):
        # candidateUid/enable,cachedUid,cachePresent,currentEnable,force,locks,
        # histPresent,oldHistPresent then old/new DRC,dark,gain,lux,slot88,slot92.
        assert len(record)==88
        values=struct.unpack('<10I12f',record);u=self.u
        obj=h.DATA+0x10000;root=obj+0x1000;cached=root+0x1000;adrc=cached+0x1000
        inp=adrc+0x2000;tags=inp+0x8000;hist=tags+0x1000;oldhist=hist+0x2000
        ib=bytearray(0x6000);mb=bytearray(1152)
        uid,enabled,old_uid,present,old_enable,force,awb,aec,hp,op=values[:10]
        struct.pack_into('<I',mb,12,old_enable);struct.pack_into('<3Q',mb,48,adrc,root,cached if present else 0)
        struct.pack_into('<2f',mb,72,*values[10:12]);struct.pack_into('<4f',mb,80,*values[12:16])
        struct.pack_into('<Q',mb,96,oldhist if op else 0)
        struct.pack_into('<Q',ib,2512,tags);struct.pack_into('<I',ib,19896,force)
        for offset,value in zip([2912,2916,2884,2892,2872,2880],values[16:]):struct.pack_into('<f',ib,offset,value)
        struct.pack_into('<Q',ib,3000,hist if hp else 0)
        rb=bytearray(136);struct.pack_into('<I',rb,0,uid);struct.pack_into('<I',rb,8,enabled)
        cb=bytearray(136);struct.pack_into('<I',cb,0,old_uid)
        tb=bytearray(128);tb[98]=awb;tb[99]=aec
        u.mem_write(obj,bytes(mb));u.mem_write(root,bytes(rb));u.mem_write(cached,bytes(cb))
        u.mem_write(adrc,bytes([0xa7])*4288);u.mem_write(inp,bytes(ib));u.mem_write(tags,bytes(tb))
        self.stop_set={0x383cdc,0x38565c};self.stop_pc=h.STOP
        for reg,value in [(UC_ARM64_REG_X0,obj),(UC_ARM64_REG_X1,inp),(UC_ARM64_REG_LR,h.STOP),
                          (UC_ARM64_REG_SP,h.STACK+0xf0000)]:u.reg_write(reg,value)
        before=self.instructions;u.emu_start(0x383728,h.STOP,timeout=2000000,count=50000)
        pc=u.reg_read(UC_ARM64_REG_PC);assert pc in self.stop_set,hex(pc)
        def word(address):return struct.unpack('<I',u.mem_read(address,4))[0]
        def ptr(address):return struct.unpack('<Q',u.mem_read(address,8))[0]
        # Abstract pointers to booleans/selected root while preserving all policy fields.
        cached_current=ptr(obj+64);assert cached_current in [root,cached,0]
        new_hist=ptr(obj+96);assert new_hist in [oldhist,hist+8,0]
        result=struct.pack('<8I',word(obj+12),word(inp+3016),int(pc==0x383cdc),
            int(ptr(obj+104)==adrc),int(ptr(inp+3024)==adrc),int(cached_current==root),
            2 if new_hist==hist+8 else 1 if new_hist==oldhist else 0,word(cached_current) if cached_current else 0)
        result+=bytes(u.mem_read(obj+72,24))
        assert bytes(u.mem_read(root,136))==rb and bytes(u.mem_read(cached,136))==cb
        assert bytes(u.mem_read(adrc,4288))==bytes([0xa7])*4288
        self.stop_set=set()
        return result,self.instructions-before
