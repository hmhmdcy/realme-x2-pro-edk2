"""Run the whole original SWTMC11 Execute with persistent preallocated storage."""
from pathlib import Path
import importlib.util,struct
from unicorn.arm64_const import *
spec=importlib.util.spec_from_file_location('tree414',Path(__file__).resolve().parents[1]/'kernel414/tree-model.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old);h=old.h
class ExecuteMachine(old.TreeMachine):
    def step(self,u,pc,size,user):
        if pc==0x383cdc:self.did_calculate=True
        if pc==0x3837e0:self.refreshed=True
        if pc==0x383afc:self.hist_updated=True
        return super().step(u,pc,size,user)
    def reset(self):
        self.obj=h.DATA+0x10000;self.inp=h.DATA+0x18000;self.tags=h.DATA+0x20000
        self.adrc=h.DATA+0x22000;self.hist=[0,h.DATA+0x25000,h.DATA+0x27000]
        self.roots={};self.cursor=h.DATA+0x30000;u=self.u
        u.mem_write(self.obj,bytes(1152));u.mem_write(self.adrc,bytes(4288))
        u.mem_write(self.obj+48,struct.pack('<Q',self.adrc));u.mem_write(self.tags,bytes(128))
        for token,data in [(1,struct.pack('<1024I',*([64]*1024))),
                           (2,struct.pack('<1024I',65536,*([0]*1023)))]:
            u.mem_write(self.hist[token],bytes(8)+data)
        u.mem_write(0x96aac0+584,bytes(1))
    def install(self,root_data):
        key=(root_data['uid'],root_data['enabled'])
        if key in self.roots:return self.roots[key][0]
        root=self.cursor;base=root+0x100;blob=bytearray()
        def alloc(size):
            at=(len(blob)+7)//8*8;blob.extend(bytes(at+size-len(blob)));return at
        doff=alloc(24*len(root_data['core']))
        for di,drc in enumerate(root_data['core']):
            hoff=alloc(40*len(drc['children']))
            struct.pack_into('<2fI4xQ',blob,doff+di*24,*drc['trigger'],len(drc['children']),base+hoff)
            for hi,hdr in enumerate(drc['children']):
                aoff=alloc(192*len(hdr['children']))
                struct.pack_into('<6fI4xQ',blob,hoff+hi*40,*hdr['trigger'],len(hdr['children']),base+aoff)
                for ai,aec in enumerate(hdr['children']):
                    at=aoff+ai*192;struct.pack_into('<4f',blob,at,*aec['trigger']);blob[at+16:at+192]=old.region_bytes(aec['data'])
        rb=bytearray(136);struct.pack_into('<I',rb,0,root_data['uid']);struct.pack_into('<I',rb,8,root_data['enabled'])
        struct.pack_into('<2I',rb,68,*root_data['control_method']);r=root_data['reserve']
        struct.pack_into('<4I6f',rb,76,r['use_gtm'],r['use_ltm'],r['curve_model'],r['curve_order'],r['tone_max_ratio'],
                         *[r['reserve_rsv_para'+str(i)] for i in range(1,6)])
        struct.pack_into('<I4xQ',rb,120,len(root_data['core']),base+doff)
        self.u.mem_write(root,bytes(rb));self.u.mem_write(base,bytes(blob))
        self.cursor=(base+len(blob)+4095)//4096*4096;assert self.cursor<h.DATA+0xf0000
        self.roots[key]=(root,bytes(rb),base,bytes(blob));return root
    def request(self,root_data,triggers,force,locks,hist_token):
        u=self.u;obj=self.obj;inp=self.inp;candidate=self.install(root_data)
        ib=bytearray(19928);struct.pack_into('<Q',ib,2512,self.tags)
        struct.pack_into('<I',ib,19896,force)
        for at,value in zip([2912,2916,2884,2892,2872,2880],triggers):struct.pack_into('<f',ib,at,value)
        struct.pack_into('<Q',ib,3000,self.hist[hist_token]);u.mem_write(inp,bytes(ib))
        u.mem_write(self.tags+98,bytes(locks));u.mem_write(obj+56,struct.pack('<Q',candidate))
        self.did_calculate=False;self.refreshed=False;self.hist_updated=False;self.stop_pc=h.STOP
        before=self.instructions;ret=self.call(0x383728,obj,inp,phase='complete SWTMC11 Execute')
        assert ret==0
        cached=self.read64(obj+64);hist=self.read64(obj+96)
        token=next(i for i,ptr in enumerate(self.hist) if hist==(ptr+8 if ptr else 0))
        policy=struct.pack('<8I',self.read32(obj+12),self.read32(inp+3016),self.did_calculate,
            self.read64(obj+104)==self.adrc,self.read64(inp+3024)==self.adrc,self.refreshed,
            2 if self.hist_updated else 1 if token else 0,self.read32(cached))
        policy+=bytes(u.mem_read(obj+72,24))
        for root,rb,base,blob in self.roots.values():
            assert bytes(u.mem_read(root,len(rb)))==rb and bytes(u.mem_read(base,len(blob)))==blob
        assert bytes(u.mem_read(self.adrc+4236,52))==bytes(52)
        return dict(policy=policy,adrc=bytes(u.mem_read(self.adrc,4236)),hist_token=token,
                    gamma=bytes(u.mem_read(obj+112,1028)),instructions=self.instructions-before)
