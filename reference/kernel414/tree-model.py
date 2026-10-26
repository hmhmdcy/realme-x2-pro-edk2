"""Execute the original TMC11 module interpolation prefix using its native ABI."""
from pathlib import Path
import importlib.util,struct
from unicorn.arm64_const import *
spec=importlib.util.spec_from_file_location('generation413',Path(__file__).resolve().parents[1]/'kernel413/generation-model.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old);h=old.h

def region_bytes(data):
    values=[]
    for value in data.values():values.extend(value if isinstance(value,list) else [value])
    assert len(values)==44
    return struct.pack('<44f',*values)

class TreeMachine(old.GenerationMachine):
    def tree(self,root_data,controls,triggers):
        u=self.u;sp=h.STACK+0xd0000;obj=h.DATA+0x40000;root=obj+0x2000;base=root+0x1000
        blob=bytearray()
        def allocate(size):
            offset=(len(blob)+7)//8*8
            blob.extend(bytes(offset+size-len(blob)))
            return offset
        doff=allocate(24*len(root_data['core']))
        for di,drc in enumerate(root_data['core']):
            hoff=allocate(40*len(drc['children']))
            struct.pack_into('<2fI4xQ',blob,doff+24*di,*drc['trigger'],len(drc['children']),base+hoff)
            for hi,hdr in enumerate(drc['children']):
                aoff=allocate(192*len(hdr['children']))
                struct.pack_into('<6fI4xQ',blob,hoff+40*hi,*hdr['trigger'],len(hdr['children']),base+aoff)
                for ai,aec in enumerate(hdr['children']):
                    offset=aoff+192*ai
                    struct.pack_into('<4f',blob,offset,*aec['trigger'])
                    blob[offset+16:offset+192]=region_bytes(aec['data'])
        rb=bytearray(136);struct.pack_into('<I',rb,8,root_data['enabled'])
        struct.pack_into('<2I',rb,68,*controls)
        struct.pack_into('<I4xQ',rb,120,len(root_data['core']),base+doff)
        ib=bytearray(1152);struct.pack_into('<Q',ib,64,root)
        # DRC72, realGain80, lux84, and the two actual HDR input slots88/92.
        struct.pack_into('<f',ib,72,triggers[0]);struct.pack_into('<4f',ib,80,*triggers[1:])
        u.mem_write(sp,bytes(0x6000));u.mem_write(obj,bytes(ib));u.mem_write(root,bytes(rb));u.mem_write(base,bytes(blob))
        for reg,value in [(UC_ARM64_REG_SP,sp),(UC_ARM64_REG_X19,obj),
                          (UC_ARM64_REG_X23,sp+64),(UC_ARM64_REG_X24,obj+112)]:u.reg_write(reg,value)
        self.stop_pc=0x384048;before=self.instructions
        u.emu_start(0x383cdc,self.stop_pc,timeout=5000000,count=2000000)
        assert u.reg_read(UC_ARM64_REG_PC)==self.stop_pc,hex(u.reg_read(UC_ARM64_REG_PC))
        assert bytes(u.mem_read(obj,len(ib)))==ib and bytes(u.mem_read(root,len(rb)))==rb
        assert bytes(u.mem_read(base,len(blob)))==blob
        nodes=[]
        for i in range(7):
            node=sp+2712+i*72
            count,ratio=struct.unpack('<If',u.mem_read(node+32,8))
            nodes.append(dict(children=count,ratio=ratio))
        return bytes(u.mem_read(sp+64,176)),nodes,self.instructions-before
