"""Compare the final native pass distributor/BL generator for larger frames."""
from pathlib import Path
import json,struct
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;storage.mount.mounted_build()
assert json.loads((HERE/'geometry-prototype-validation.json').read_text())['passed']
old=HERE.parent/'kernel430/probe-native-bl.py';text=old.read_text().split('fw.r.Firmware=NativeBL',1)[0]
scope={'__file__':str(old),'__name__':'native_bl441_reuse'};exec(compile(text,str(old),'exec'),scope)
fw=scope['fw'];NativeBL=scope['NativeBL'];prepare_text=scope['_prepare_text'].replace('ref_iova=0):','ref_iova=0,width=640,height=480):').replace('640*480','width*height')
binding=dict(scope['_scope']);exec(compile(prepare_text,'retained-native-frame-prepare-variable-geometry','exec'),binding)
fw.r.Firmware=NativeBL
def execute(config,stripe,iq,width,height):
 m,job,commands,scratch=binding['prepare'](config,stripe,iq,1,width=width,height=height)
 D=fw.f.DATA;u=m.u;passes=m.read32(m.config+2896)
 core_infos=m.call(0x20f8a,1,phase='original-core-infos');cores=m.call(0x20f6a,1,phase='original-num-cores');sp=0x020f0000
 for offset,value in [(24,1),(36,0x100ab8),(48,cores),(52,core_infos)]:m.write32(sp+offset,value)
 u.reg_write(scope['UC_ARM_REG_R8'],1);m.call(0x2040c,phase='original-bl-context-initialization',stop=0x20530);generator=u.reg_read(scope['UC_ARM_REG_R8'])
 assert m.read32(generator)==1 and m.read32(generator+4)==cores and m.read32(generator+3608)==0x100ab8
 scheduler=D+0x190000;work=D+0x191000;u.mem_write(scheduler,bytes(688));u.mem_write(work,bytes(200));u.mem_write(work+4,job)
 m.write32(scheduler+632,generator);m.write32(work+180,1);mutex=D+0x192000;m.write32(mutex,mutex);m.write32(0x131d68,mutex)
 m.call(0x22dc0,scheduler,work,phase='original-pass-distribution');distribution=[list(struct.unpack('<2I',u.mem_read(work+48+i*8,8))) for i in range(passes)]
 for index in range(cores):m.queues[scheduler+508+index*44]=dict(bytes=8,capacity=128,rows=[])
 result=m.call(0x1ee8a,generator,work,scheduler+508,phase='original-native-bl-generation');assert result==0
 blobs={'program':bytes(u.mem_read(D+0x100000,0x80000)),'heap':bytes(u.mem_read(0x05000000,0x200000)),'context':bytes(u.mem_read(generator,3616)),'work':bytes(u.mem_read(work,200))}
 for address,size in m.allocated.items():blobs[f'allocation-{address:08x}']=bytes(u.mem_read(address,size))
 queues={hex(a):[v.hex() for v in q['rows']] for a,q in m.queues.items()}
 return blobs,dict(distribution=distribution,scratch_bytes=scratch,queue_entries=queues,return_code=result)
rows=[]
try:
 for width,height in [(640,480),(1280,720),(1920,1080)]:
  slug=f'{width}x{height}';config=(P/f'{slug}-config-private.bin').read_bytes();iq=(P/f'{slug}-iq-private.bin').read_bytes()
  actual,ar=execute(config,(P/f'{slug}-actual-c-stripe-private.bin').read_bytes(),iq,width,height)
  gold,gr=execute(config,(P/f'{slug}-stripe-private.bin').read_bytes(),iq,width,height)
  assert actual.keys()==gold.keys();different=[n for n in actual if actual[n]!=gold[n]]
  assert ar==gr
  counts=[struct.unpack_from('<H',(P/f'{slug}-stripe-private.bin').read_bytes(),428+412*i)[0] for i in range(2)]
  assert ar['distribution']==[[(1<<count)-1,0] for count in counts]
  for name,blob in actual.items():(P/f'{slug}-final-{name}-private.bin').write_bytes(blob)
  row=dict(width=width,height=height,native_pass_masks=ar['distribution'],scratch_bytes=ar['scratch_bytes'],compared_binary_objects=len(actual),final_program_bytes=0x80000,whole_heap_bytes=0x200000,queued_commands_equal=ar['queue_entries']==gr['queue_entries'],different_objects=different,passed=not different);rows.append(row);print(json.dumps(row),flush=True)
finally:fw.r.Firmware=scope['old']
report=dict(stage=441,rows=rows,final_native_pass_distribution_and_bl_generation_executed=True,authored_c_geometry_matches_native_all_live_allocations=True,queue_and_os_providers_are_fixture_not_original_os_execution=True,hardware_executed=False,phone_accessed=False,passed=all(r['passed'] for r in rows))
(HERE/'native-bl-validation.json').write_text(json.dumps(report,indent=2)+'\n');assert report['passed']
