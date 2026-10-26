"""Execute the retained native BL initializer/distributor/generator, without hardware."""
from pathlib import Path
import importlib.util,json,struct,sys
from unicorn import UC_HOOK_MEM_READ
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_R8,UC_ARM_REG_SP,UC_ARM_REG_PC,UC_ARM_REG_LR
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
module('storage430',HERE.parent/'kernel284/storage.py').mounted_build()
fw=module('fw429',HERE.parent/'kernel429/firmware-model.py');old=fw.r.Firmware
_prepare_text=(HERE.parent/'kernel429/firmware-model.py').read_text().split('def prepare(')[1]
_prepare_text='def prepare('+_prepare_text
_prepare_text=_prepare_text.replace('pd10_iova=0x20800000):','pd10_iova=0x20800000,ref_iova=0):')
_prepare_text=_prepare_text.replace(' and m.read32(m.config+2896)==2','')
_prepare_text=_prepare_text.replace('m.u.mem_write(stripe_addr,stripe);','struct.pack_into(\'<I\',frame,92+11*16,ref_iova)\n m.u.mem_write(stripe_addr,stripe);')
_scope=dict(fw.__dict__);exec(compile(_prepare_text,'original-frame-prepare-with-optional-ref','exec'),_scope)
class NativeBL(old):
 last=None
 def __init__(self):
  super().__init__();self.queues={};self.bl_events=[];self.queue_events=[];self.stripe_reads=set();NativeBL.last=self
  if '--observe' in sys.argv:
   base=fw.f.DATA+0x30000
   def reading(u,access,address,size,value,user):self.stripe_reads.update(range(max(base,address)-base,min(base+4140,address+size)-base))
   self.u.hook_add(UC_HOOK_MEM_READ,reading,begin=base,end=base+4140-1)
 def step(self,u,pc,size,user):
  a,b,c,d=[u.reg_read(r) for r in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]]
  if pc in [0x6576,0x65fa,0x6636,0x6682,0x65e0,0x79c,0x7c4,0x532,0x4e6c]:
   if pc==0x6576:
    self.queues[a]=dict(bytes=b,capacity=c,rows=[]);u.mem_write(a,bytes(44));self.write32(a+4,0x6d15);result=1
   elif pc==0x65fa:
    q=self.queues[a];assert len(q['rows'])<q['capacity'];q['rows'].append(bytes(u.mem_read(b,q['bytes'])));result=1
    self.queue_events.append(dict(queue=hex(a),source=hex(b),row=q['rows'][-1].hex(),caller=hex(u.reg_read(UC_ARM_REG_LR))))
   elif pc in [0x6636,0x6682]:
    q=self.queues[a];result=bool(q['rows'])
    if result:
     if pc==0x6636:q['rows'].pop(0)
     else:
      if 'peek' not in q:q['peek']=fw.f.DATA+0x1a0000+list(self.queues).index(a)*0x1000
      u.mem_write(q['peek'],q['rows'][0]);self.write32(b,q['peek'])
   elif pc==0x65e0:del self.queues[a];result=1
   else:result=0
   self.providers[hex(pc)]=self.providers.get(hex(pc),0)+1;u.reg_write(UC_ARM_REG_R0,result);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
  if pc in [0x1fea8,0x1ff82,0x1ecd6]:
   row=dict(pc=hex(pc),caller=hex(u.reg_read(UC_ARM_REG_LR)&~1),args=[a,b,c,d],stack=struct.unpack('<4I',u.mem_read(u.reg_read(UC_ARM_REG_SP),16)))
   if pc==0x1ff82 and 0<c<=4096:row['command_hex']=bytes(u.mem_read(b,c)).hex()
   if pc==0x1fea8 and d:
    ptr=self.read32(u.reg_read(UC_ARM_REG_SP));row['values']=list(struct.unpack('<'+'I'*d,u.mem_read(ptr,d*4)))
   self.bl_events.append(row)
  return super().step(u,pc,size,user)
fw.r.Firmware=NativeBL
case=sys.argv[1] if len(sys.argv)>1 else 'actual';assert case in ['actual','native','native-ref','native-topology','native-topology1','native-topology2','actual-topology','proposed-topology','maintained'];out=P/('bl-'+case+('-observed' if '--observe' in sys.argv else ''));out.mkdir(exist_ok=True)
config=(P.parent/'kernel425/width-640-dc-1-config-private.bin').read_bytes();iq=(P.parent/'kernel424/coarse-width-640-dc-1-iq-private.bin').read_bytes();stripe=(P.parent/'kernel429/actual-c-stripe-private.bin').read_bytes()
if case=='native-ref':
 config=bytearray(config);config[11*84:12*84]=config[84:168];config=bytes(config)
if case.startswith('native-topology') or case in ['actual-topology','proposed-topology']:
 config=bytearray(config);struct.pack_into('<I',config,1200,int(case[-1]) if case[-1].isdigit() else 3);config=bytes(config)
if case not in ['actual','actual-topology','proposed-topology','maintained']:
 native=module('native425',HERE.parent/'kernel425/native-model.py').Native();stripe,_,_=native.striping(config,640,480,1,iq)
if case=='proposed-topology':
 stripe=bytearray(stripe)
 for offset,value in [(24+270,119),(24+274,59),(24+376,119),(2268+30,159),(2268+318,159),(2268+322,159)]:struct.pack_into('<H',stripe,offset,value)
 stripe=bytes(stripe)
if case=='maintained':config=(P/'actual-c-config-private.bin').read_bytes();stripe=(P/'actual-c-stripe-private.bin').read_bytes()
_scope['r'].Firmware=NativeBL
try:m,job,commands,scratch=_scope['prepare'](config,stripe,iq,1,ref_iova=0x24800000 if case=='native-ref' else 0)
except BaseException:
 (out/'failed-frame-logs-private.json').write_text(json.dumps(NativeBL.last.logs,indent=2)+'\n')
 raise
D=fw.f.DATA;u=m.u;pass_count=m.read32(m.config+2896)
(out/'config-private.bin').write_bytes(config);(out/'striping-private.bin').write_bytes(stripe);(out/'programs-private.bin').write_bytes(commands)
core_infos=m.call(0x20f8a,1,phase='original-core-infos');num_cores=m.call(0x20f6a,1,phase='original-num-cores')
sp=0x020f0000
for offset,value in [(24,1),(36,0x100ab8),(48,num_cores),(52,core_infos)]:m.write32(sp+offset,value)
u.reg_write(UC_ARM_REG_R8,1)
m.call(0x2040c,phase='original-bl-context-initialization',stop=0x20530);generator=u.reg_read(UC_ARM_REG_R8)
assert m.read32(generator)==1 and m.read32(generator+4)==num_cores and m.read32(generator+3608)==0x100ab8
# Only the queue/scheduler/OS fixture is supplied; the native pass distribution
# and command construction execute original instructions unchanged.
scheduler=D+0x190000;work=D+0x191000;u.mem_write(scheduler,bytes(688));u.mem_write(work,bytes(200));u.mem_write(work+4,job)
m.write32(scheduler+632,generator);m.write32(work+180,1)
mutex=D+0x192000;m.write32(mutex,mutex);m.write32(0x131d68,mutex)
m.call(0x22dc0,scheduler,work,phase='original-pass-distribution')
distribution=[list(struct.unpack('<2I',u.mem_read(work+48+i*8,8))) for i in range(pass_count)]
for index in range(num_cores):m.queues[scheduler+508+index*44]=dict(bytes=8,capacity=128,rows=[])
result=m.call(0x1ee8a,generator,work,scheduler+508,phase='original-native-bl-generation')
(out/'events-private.json').write_text(json.dumps(m.bl_events,indent=2)+'\n')
(out/'stripe-reads-private.json').write_text(json.dumps(sorted(m.stripe_reads))+'\n')
(out/'queue-events-private.json').write_text(json.dumps(m.queue_events,indent=2)+'\n')
(out/'context-private.bin').write_bytes(u.mem_read(generator,3616))
(out/'work-private.bin').write_bytes(u.mem_read(work,200))
(out/'queues-private.json').write_text(json.dumps({hex(a):[v.hex() for v in q['rows']] for a,q in m.queues.items()},indent=2)+'\n')
for a,n in m.allocated.items():(out/f'allocation-{a:08x}-private.bin').write_bytes(u.mem_read(a,n))
(out/'heap-private.bin').write_bytes(u.mem_read(0x05000000,0x200000))
summary=dict(case=case,native_num_cores=num_cores,return_code=result,events=len(m.bl_events),native_striping_passes=struct.unpack_from('<I',stripe,20)[0],firmware_passes=pass_count,scratch_bytes=scratch,pass_stripe_masks=distribution,queue_entries={hex(a):len(q['rows']) for a,q in m.queues.items()},providers=m.providers,hardware_executed=False)
(out/'summary-private.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary),flush=True)
fw.r.Firmware=old
