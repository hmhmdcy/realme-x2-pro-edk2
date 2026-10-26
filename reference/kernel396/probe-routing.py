"""Execute original striping and complete firmware preparation with post-LTM CDM."""
from pathlib import Path
import importlib.util,json,struct
from unicorn.arm64_const import UC_ARM64_REG_X0
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_LR,UC_ARM_REG_PC
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
h=module('hal380',HERE.parent/'kernel380/hal-machine.py');f=module('fw383',HERE.parent/'kernel383/firmware-model.py')

def striping(width,height,port,cores,enabled):
 m=h.Machine();u=m.u;D=h.DATA;config=bytearray(1216)
 for index in [0,port]:
  off=index*84;struct.pack_into('<III',config,off,20,width,height);struct.pack_into('<4I',config,off+52,width,height,width,height//2)
 struct.pack_into('<I',config,1192,1);u.mem_write(D,bytes(config));assert m.call(0x144348,D,0,0x10705,0x10000,D+0x2000,D+0x2010,D+0x2014,phase='create')==0
 context=m.read64(D+0x2000);capacity=m.read32(D+0x2010);bl=m.read32(D+0x2014);out=D+0x20000;params=D+0x3000;iq=D+0x10000
 u.mem_write(params,struct.pack('<5QI',iq,D+0x12000,D+0x14000,D+0x16000,D+0x18000,cores))
 for target in [D+0x16000,D+0x18000]:u.mem_write(target,struct.pack('<6I',width,height,0,0,width,height))
 for off in [52,68,244,260]:u.mem_write(iq+off,struct.pack('<I',1))
 u.mem_write(iq+2188,struct.pack('<I',enabled));u.mem_write(out,bytes([0xa5])*capacity)
 assert m.call(0x1448f0,context,params,out,D+0x70000,D+0x80000,phase='execute')==0
 data=bytes(u.mem_read(out,capacity));passes=struct.unpack_from('<I',data,20)[0];used=2268+624*sum(struct.unpack_from('<H',data,428+412*i)[0] for i in range(passes))
 assert m.call(0x144988,D+0x2000,phase='destroy')==0 and not m.allocations
 return data[:used],bl,m.instructions

class Firmware(f.Machine):
 def __init__(self):super().__init__();self.cache=[];self.external=[]
 def step(self,u,pc,size,user):
  if pc==0xf278:self.external.append(u.reg_read(UC_ARM_REG_R1))
  if pc==0x6f2c:
   self.instructions+=1;self.providers[hex(pc)]=self.providers.get(hex(pc),0)+1;self.cache.append(struct.unpack('<4I',u.mem_read(u.reg_read(UC_ARM_REG_R0),16)))
   u.reg_write(UC_ARM_REG_R0,0);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
  return super().step(u,pc,size,user)

def prepare(blob,width,height,port,cores,enabled,command):
 m=Firmware();D=f.DATA;m.call(0x7998,phase='chip-info');m.payload=D+0x10000;wire=bytearray(1216)
 for p in [0,port]:
  off=p*84;struct.pack_into('<III',wire,off,20,width,height);struct.pack_into('<4I',wire,off+52,width,height,width,height//2)
 struct.pack_into('<I',wire,1192,1);m.write32(m.payload,5);m.u.mem_write(m.payload+8,bytes(wire));m.write32(D,D+0xc000)
 assert m.call(0x16534,D,phase='config')==0 and m.read32(m.payload+4)==0
 frame=bytearray(3816);stripe=D+0x30000;iq=D+0x40000;arrays=D+0x48000;bl=D+0x60000
 struct.pack_into('<4I',frame,0,stripe,iq,D+0x45000,48);struct.pack_into('<4I',frame,24,bl,0x80000-32,cores,100000000)
 struct.pack_into('<I',frame,48,32)
 struct.pack_into('<II',frame,84,1,1);struct.pack_into('<II',frame,92,0x20000000,0x20000000+width*height);struct.pack_into('<II',frame,92+port*16,0x24000000,0x24000000+width*height)
 m.u.mem_write(stripe,blob)
 for off in [52,68,244,260]:m.write32(iq+off,1)
 m.write32(iq+2188,enabled);m.u.mem_write(arrays,bytes(256))
 # Empty common array at offset0; one external generic post-LTM program at32.
 m.u.mem_write(arrays+32,struct.pack('<8I',0,1,arrays+128,(len(command)-1)<<12,0,0,0,0));m.u.mem_write(arrays+128,command)
 m.payload=D+0x20000;m.write32(m.payload,6);m.u.mem_write(m.payload+8,bytes(frame))
 # ProcessAsyncCommand normally fixes these offsets before the queued handler.
 # Here the complete handler is called directly, with all offsets already fixed.
 for off in range(44,84,4):m.write32(m.payload+8+off,arrays+(32 if off==48 else 0))
 m.call(0x17f30,D,phase='complete-frame-preparation',stop=0x220a2)
 assert m.read32(m.payload+4)==0
 job=bytes(m.u.mem_read(m.u.reg_read(UC_ARM_REG_R1),32));commands=bytes(m.u.mem_read(bl,0x80000))
 return m,job,commands

if __name__=='__main__':
 command=(P/'cc-actual-private.bin').read_bytes()[:44];rows=[]
 for width,height,port,cores in [(640,480,8,1),(640,480,9,2)]:
  off,bl,n=striping(width,height,port,cores,0);on,onbl,n2=striping(width,height,port,cores,1)
  m,job,commands=prepare(on,width,height,port,cores,1,command)
  slug=f'{width}x{height}-p{port}-c{cores}';(P/(slug+'-cc-bl-private.bin')).write_bytes(commands);(P/(slug+'-cc-job-private.bin')).write_bytes(job)
  rows.append(dict(width=width,height=height,port=port,cores=cores,stripe_differences=sum(a!=b for a,b in zip(off,on)),bl_before=bl,bl_after=onbl,external_arrays=m.external,cache=m.cache,job_words=struct.unpack('<8I',job),instructions=m.instructions,providers=m.providers,allocations=m.allocated))
 (P/'routing-probe-private.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))
