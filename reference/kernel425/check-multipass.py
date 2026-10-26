"""Replay maintained C IO through whole native striping and firmware prepare."""
from pathlib import Path
import hashlib, importlib.util, json, struct
import host
HERE=Path(__file__).resolve().parent; P=host.PRIVATE

def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
module('storage284',HERE.parent/'kernel284/storage.py').mounted_build()
n=module('native425',HERE/'native-model.py');f=module('firmware425',HERE/'firmware-model.py')
cases=json.loads((HERE/'io-validation.json').read_text())['rows']
wire=(P/'aarch64-io-private.bin').read_bytes(); rows=[]
for width in [640,650]:
 index=next(i for i,c in enumerate(cases) if c['width']==width and c['height']==480 and c['port']==8 and not c['uv_swap'] and not c['padding'])
 at=index*2452;layout=struct.unpack_from('<5I',wire,at);config=wire[at+20:at+1236]
 results=[]
 for dc in [0,1]:
  iq=(P.parent/f'kernel424/coarse-width-{width}-dc-{dc}-iq-private.bin').read_bytes()
  m=n.Native();stripe,bl,capacity=m.striping(config,width,480,2,iq)
  fw,job,commands,meta=f.prepare(config,stripe,iq,width,480,layout[4]);meta.pop('frame')
  controls=[struct.unpack_from('<I',commands,i+4)[0] for i in range(0,len(commands)-4,4) if struct.unpack_from('<I',commands,i)[0]==0x5c60]
  refs=[i for i in range(0,len(commands)-3,4) if struct.unpack_from('<I',commands,i)[0]==meta['pd10_address']]
  assert meta['configured_passes']==2
  if dc: assert len(refs)>0, (width,dc,meta)
  if dc:
   relocated=0x20900000
   _,job2,commands2,meta2=f.prepare(config,stripe,iq,width,480,layout[4],relocated)
   expected=bytearray(commands)
   for off in refs:struct.pack_into('<I',expected,off,relocated)
   assert commands2==bytes(expected) and job2==job
  passes=struct.unpack_from('<I',stripe,20)[0]
  assert passes==(2 if dc else 1), (width,dc,passes)
  for name,raw in [('config',config),('stripe',stripe),('job',job),('commands',commands)]:
   (P/f'width-{width}-dc-{dc}-{name}-private.bin').write_bytes(raw)
  results.append((stripe,job,commands,controls))
  rows.append(dict(width=width,height=480,dc_requested=dc,pd10_width=layout[0],pd10_height=layout[1],pd10_stride=layout[2],pd10_slice_height=layout[3],pd10_bytes=layout[4],
   actual_candidate_c_io_used=True,whole_native_striping_and_firmware_prepare=True,configured_passes=2,executed_passes=passes,striping_bytes=len(stripe),striping_capacity=capacity,native_command_minimum_bytes=bl,
   scratch_bytes=meta['required_scratch_bytes'],native_prepared_command_bytes=fw.cache[-1][3],pd10_address_references=len(refs),ltm_control_writes=len(controls),
   pd10_iova_relocation_only_changes_native_input_address=bool(dc),
   native_instructions=m.instructions+fw.instructions,frame_enqueue_not_executed=True))
 a,b=results
 rows[-1].update(dc_changes_striping=a[0]!=b[0],dc_changes_job=a[1]!=b[1],dc_changes_commands=a[2]!=b[2],dc_changes_ltm_controls=a[3]!=b[3])
r=dict(stage=425,candidate_c_io_source_commit=json.loads((HERE/'source-state.json').read_text())['commit'],rows=rows,
 native_two_pass_preparation_proven=True,explicit_external_pd10_input_referenced=True,
 pd10_producer_not_executed_or_verified=True,dc_statistics_production_not_proven=True,
 newer_reference_internal_downscale_not_assumed_supported=True,phone_accessed=False,installed=False,passed=True)
(HERE/'multipass-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
