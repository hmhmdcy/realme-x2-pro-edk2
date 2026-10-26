"""Retain exact output writes from the original target striping algorithm."""
from pathlib import Path
import importlib.util,json,struct
from unicorn import UC_HOOK_MEM_WRITE
from unicorn.arm64_const import UC_ARM64_REG_PC,UC_ARM64_REG_X0
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('hal380',HERE.parent/'kernel380/hal-machine.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def execute(width,height,port=8,cores=1,trace=False,dirty=0xa5,uv_swap=False):
 class SeededMachine(m.Machine):
  def step(self,u,pc,size,user):
   allocation_bytes=u.reg_read(UC_ARM64_REG_X0) if pc==0x5b13c0 else 0
   super().step(u,pc,size,user)
   if allocation_bytes:u.mem_write(u.reg_read(UC_ARM64_REG_X0),bytes([dirty])*allocation_bytes)
 model=SeededMachine();u=model.u;D=m.DATA;config=bytearray(1216)
 for index in [0,port]:
  off=index*84;struct.pack_into('<III',config,off,20,width,height);struct.pack_into('<I',config,off+24,int(uv_swap));struct.pack_into('<4I',config,off+52,width,height,width,height//2)
 struct.pack_into('<I',config,1192,1);u.mem_write(D,bytes(config))
 assert model.call(0x144348,D,0,0x10705,0x10000,D+0x2000,D+0x2010,D+0x2014,phase='create')==0
 context=model.read64(D+0x2000);capacity=model.read32(D+0x2010);bl=model.read32(D+0x2014)
 out=D+0x20000;params=D+0x3000;iq=D+0x10000
 u.mem_write(params,struct.pack('<5QI',iq,D+0x12000,D+0x14000,D+0x16000,D+0x18000,cores))
 for target in [D+0x16000,D+0x18000]:u.mem_write(target,struct.pack('<6I',width,height,0,0,width,height))
 for off in [52,68,244,260]:u.mem_write(iq+off,struct.pack('<I',1))
 u.mem_write(out,bytes([dirty])*capacity);writes=[];mask=bytearray(capacity)
 def writing(uc,access,address,size,value,user):
  lo=max(address,out);hi=min(address+size,out+capacity)
  if lo>=hi:return
  mask[lo-out:hi-out]=bytes([1])*(hi-lo)
  if trace:writes.append(dict(pc=uc.reg_read(UC_ARM64_REG_PC),offset=address-out,size=size,value=value&((1<<(8*size))-1)))
 u.hook_add(UC_HOOK_MEM_WRITE,writing)
 assert model.call(0x1448f0,context,params,out,D+0x70000,D+0x80000,phase='execute')==0
 data=bytes(u.mem_read(out,capacity));passes=struct.unpack_from('<I',data,20)[0];counts=[struct.unpack_from('<H',data,428+412*i)[0] for i in range(passes)];used=2268+624*sum(counts)
 assert used<=capacity and model.call(0x144988,D+0x2000,phase='destroy')==0 and not model.allocations
 return data[:used],bytes(mask[:used]),writes,dict(width=width,height=height,output_port=port,max_cores=cores,passes=passes,stripes=counts,bytes=used,bl_capacity=bl)
if __name__=='__main__':
 rows=[]
 for width,height,port,cores in [(640,480,8,1),(1920,1080,8,1),(4608,3456,8,1),(4608,3456,8,2),(640,480,9,1)]:
  blob,mask,writes,info=execute(width,height,port,cores,True);slug=f'{width}x{height}-p{port}-c{cores}'
  (P/(slug+'-stripe-private.bin')).write_bytes(blob);(P/(slug+'-write-mask-private.bin')).write_bytes(mask);(P/(slug+'-writes-private.json')).write_text(json.dumps(writes)+'\n')
  info.update(written_bytes=sum(mask),nonzero_written_bytes=sum(a and b!=0 for a,b in zip(mask,blob)),writes=len(writes));rows.append(info)
 (P/'striping-traces-private.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))
