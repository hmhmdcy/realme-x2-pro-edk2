"""Run target HAL alignment stores and striping; retain vendor outputs privately."""
from pathlib import Path
import importlib.util,json,struct
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('machine380',HERE.parent/'kernel380/hal-machine.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
P=Path('/mnt/e/edk2-samurai-out/kernel382');D=m.DATA
model=m.Machine();u=model.u;sp=m.STACK+0xf0000
u.mem_write(sp+376,struct.pack('<Q',D));u.mem_write(sp+448,struct.pack('<Q',D+0x4000))
u.reg_write(m.UC_ARM64_REG_SP,sp);u.reg_write(m.UC_ARM64_REG_X25,D)
u.emu_start(0x2e08a8,0x2e08c4,timeout=1000000,count=20)
assert u.reg_read(m.UC_ARM64_REG_PC)==0x2e08c4
iq=bytes(u.mem_read(D,2584));written=[(i,struct.unpack_from('<I',iq,i)[0]) for i in range(0,len(iq),4) if any(iq[i:i+4])]
assert written==[(52,1),(68,1),(244,1),(260,1)]
(P/'hal-default-ica-iq-private.bin').write_bytes(iq)
rows=[]
for name,fields in [('zero',[]),('ica1-align',[68]),('ica2-align',[260]),('both-align',[68,260]),('hal-four-defaults',[52,68,244,260])]:
 model=m.Machine();u=model.u;config=bytearray(1216)
 for port in [0,8]:
  off=port*84;struct.pack_into('<III',config,off,20,640,480);struct.pack_into('<4I',config,off+52,640,480,640,240)
 struct.pack_into('<I',config,1192,1);u.mem_write(D,bytes(config))
 assert model.call(0x144348,D,0,0x10705,0x10000,D+0x2000,D+0x2010,D+0x2014,phase='create')==0
 context=model.read64(D+0x2000);capacity=model.read32(D+0x2010)
 params=D+0x3000;iq_address=D+0x10000;out=D+0x20000
 u.mem_write(params,struct.pack('<5QI',iq_address,D+0x12000,D+0x14000,D+0x16000,D+0x18000,1))
 for address in [D+0x16000,D+0x18000]:u.mem_write(address,struct.pack('<6I',640,480,0,0,640,480))
 fixture=bytearray(2584)
 for off in fields:struct.pack_into('<I',fixture,off,1)
 u.mem_write(iq_address,bytes(fixture));u.mem_write(out,bytes([0xa5])*capacity)
 assert model.call(0x1448f0,context,params,out,D+0x70000,D+0x80000,phase='execute')==0
 blob=bytes(u.mem_read(out,capacity));passes=struct.unpack_from('<I',blob,20)[0];used=2268+624*sum(struct.unpack_from('<H',blob,428+412*i)[0] for i in range(passes));blob=blob[:used]
 baseline=(P.parent/'kernel380/640x480-port8-cores1-stripe-private.bin').read_bytes();assert len(blob)==len(baseline)
 diff=[dict(offset=i,before=a,after=b) for i,(a,b) in enumerate(zip(baseline,blob)) if a!=b]
 (P/(name+'-stripe-private.bin')).write_bytes(blob);(P/(name+'-iq-private.bin')).write_bytes(fixture)
 assert model.call(0x144988,D+0x2000,phase='destroy')==0 and not model.allocations
 rows.append(dict(name=name,iq_fields_set=fields,stripe_differences=diff))
(P/'alignment-probe-private.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps([dict(name=r['name'],iq_fields_set=r['iq_fields_set'],diff_count=len(r['stripe_differences']),first_differences=r['stripe_differences'][:12]) for r in rows],indent=2))
