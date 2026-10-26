"""Check actual LTM initialization, DMI relocations, IQ fields and descriptor."""
from pathlib import Path
import importlib.util,json,random,struct
from unicorn.arm64_const import *
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('ltm403',HERE/'ltm-model.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);a=m.LTM();D=m.DATA;u=a.u
resource,kind=a.resource();rows=[]
for iova in [0x1000,0x07803000,0xfffff540]:
 raw,offsets=a.headers(iova);assert len(raw)==156 and max(offsets)+256==2736 and iova+2736<=1<<32
 rows.append(dict(lut_iova=iova,header_bytes=len(raw),passed=True))
assert not a.headers(0x1000,0)[0];(P/'ltm-dmi-original-private.bin').write_bytes(a.headers(0x07803000)[0])
# Actual target submitter emits one pre-LTM generic and one LTM LUT program.
descriptors=[]
for enabled in [0,1]:
 for index in [0,1,2]:
  frame=D+0x50000;node=D+0x60000;iq=D+0x30000;sp=m.h.STACK+0xe0000
  for address,size in [(frame,8192),(node,0x5000),(iq,2584)]:u.mem_write(address,bytes(size))
  u.mem_write(sp+376,struct.pack('<Q',iq));u.mem_write(sp+480,struct.pack('<Q',node));u.mem_write(iq+2096,struct.pack('<I',enabled));u.mem_write(node+16064,struct.pack('<I',13))
  for reg,value in [(UC_ARM64_REG_X26,frame),(UC_ARM64_REG_W10,index),(UC_ARM64_REG_SP,sp),(UC_ARM64_REG_W25,0)]:u.reg_write(reg,value)
  u.emu_start(0x2d8074,0x2d80c8,count=1000);assert u.reg_read(UC_ARM64_REG_PC)==0x2d80c8
  words=struct.unpack('<6I',u.mem_read(frame+4072+index*24+8,24));assert words==(0,155<<12,11 if enabled else 255,0,0,0)
  descriptors.append(dict(enabled=enabled,index=index,program_type=words[2],bytes=156,passed=True))
# Match the target's packed register -> firmware IQ fields, using all bits to
# recover exact masks, plus randomized source words; no calculation stub.
fields=[('rgamma_en',2100,544,8,1),('la_en',2104,544,11,1),('mask_en',2108,544,13,1),('dc_bin_init_count',2112,468,4,4),('rgb2y_c1',2116,480,0,6),('rgb2y_c2',2120,480,8,6),('rgb2y_c3',2124,480,16,6),('rgb2y_c4',2128,480,24,7),('lce_threshold',2132,508,0,10),('y_ratio_max',2136,508,16,10),('mask_d0',2140,512,0,3),('mask_d1',2144,512,4,3),('mask_d2',2148,512,8,3),('mask_d3',2152,512,12,2),('mask_d4',2156,512,16,2),('mask_d5',2160,512,20,2),('mask_shift',2164,516,0,5),('mask_scale',2168,516,8,12),('horizontal_termination',2172,520,18,1),('vertical_termination',2176,520,19,1),('data_collection_enabled',2180,544,9,1),('image_processing_enabled',2184,544,10,1)]
rng=random.Random(0x403);iq_cases=0
for flags in [0,1,0xffffffff]+[rng.getrandbits(32) for _ in range(40)]:
 for ignore in [0,1]:
  obj=D+0x20000;inp=D+0x22000;iq=D+0x30000;sp=m.h.STACK+0xe0000
  u.mem_write(obj,bytes(1168));u.mem_write(inp,bytes(0x6000));u.mem_write(iq,bytes([0xa7])*2584);u.mem_write(iq+440,struct.pack('<I',1));u.mem_write(obj+12,struct.pack('<I',1));u.mem_write(obj+620,struct.pack('<I',ignore));u.mem_write(inp+2584,struct.pack('<Q',iq));u.mem_write(sp+240,struct.pack('<2Q',obj,inp))
  packed={off:flags if flags in [0,1,0xffffffff] else rng.getrandbits(32) for off in [468,480,508,512,516,520,544]}
  for off,value in packed.items():u.mem_write(obj+off,struct.pack('<I',value))
  for reg,value in [(UC_ARM64_REG_X24,inp),(UC_ARM64_REG_X26,obj),(UC_ARM64_REG_SP,sp)]:u.reg_write(reg,value)
  u.emu_start(0x3669e0,0x366b4c,count=1000);assert u.reg_read(UC_ARM64_REG_PC)==0x366b4c
  assert a.read32(iq+2096)==1
  for name,off,src,shift,width in fields:
   expected=(packed[src]>>shift)&((1<<width)-1)
   if name=='rgamma_en' and ignore:expected=0
   assert a.read32(iq+off)==expected,(name,off,flags,ignore,a.read32(iq+off),expected)
  assert bytes(u.mem_read(iq+2092,4))==bytes([0xa7])*4 and bytes(u.mem_read(iq+2188,4))==bytes([0xa7])*4;iq_cases+=1
enable_rows=[]
for module in [0,1]:
 for anr in [0,1,2]:
  for topology in [0,1,2,3,4]:
   obj=D+0x20000;inp=D+0x22000;iq=D+0x30000;sp=m.h.STACK+0xe0000
   u.mem_write(obj+12,struct.pack('<I',module));u.mem_write(iq+440,struct.pack('<I',anr));u.mem_write(inp+2624,struct.pack('<I',topology));u.mem_write(inp+2584,struct.pack('<Q',iq));u.mem_write(sp+248,struct.pack('<Q',inp))
   for reg,value in [(UC_ARM64_REG_X24,inp),(UC_ARM64_REG_X26,obj),(UC_ARM64_REG_SP,sp)]:u.reg_write(reg,value)
   u.emu_start(0x3669e0,0x366a28,count=100);assert u.reg_read(UC_ARM64_REG_PC)==0x366a28
   expected=module if anr==1 or topology==3 else 0;assert a.read32(iq+2096)==expected;enable_rows.append(dict(module_enabled=module,anr=anr,topology=topology,ltm_enabled=expected,passed=True))
report=dict(stage=403,original_initialize_fragment_executed=True,resource_init_fragment_executed=True,source_cmd_type=kind,source_cmd_type_name='CDMDMI',resource_bytes=resource,lut_count=13,lut_transferred_bytes=2736,resource_untransferred_bytes=560,extra_resource_bytes_purpose_not_assumed=True,lut_offsets=list(offsets),lut_sizes=[48,256,256,256,256,256,64,64,256,256,256,256,256],dmi_register=0x5c08,dmi_opcode=1,header_bytes=156,all13_original_write_dmi_and_nested_relocations_executed=True,dmi_address_cases=rows,program_type=11,program_array='pre-LTM',actual_submit_descriptor_cases=descriptors,iq_offset=2096,iq_bytes=92,iq_field_cases=iq_cases,independent_random_source_registers=True,iq_fields=[dict(name='enable',offset=2096,width=1)]+[dict(name=n,offset=o,width=w) for n,o,src,sh,w in fields],actual_enable_cases=enable_rows,enable_requires_module_and_anr1_or_topology3=True,ignore_chromatix_rgamma_clears_only_reverse_gamma=True,original_full_ltm_execute_not_claimed=True,original_numeric_math_and_spatial_geometry_still_separate=True,phone_accessed=False,passed=True)
(HERE/'contract-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['iq_fields','actual_submit_descriptor_cases']},indent=2))
