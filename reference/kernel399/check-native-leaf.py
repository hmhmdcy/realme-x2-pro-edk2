"""Execute the target deserializer to establish native CV field order."""
from pathlib import Path
import importlib.util,json,struct
from unicorn.arm64_const import *
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('hal380',HERE.parent/'kernel380/hal-machine.py');h=importlib.util.module_from_spec(s);s.loader.exec_module(h)
a=h.Machine();u=a.u;D=h.DATA
fields=['r_to_y','g_to_y','b_to_y','y_offset','ap','am','bp','bm','cp','cm','dp','dm','kcr','kcb']
def leaves(nodes):
 for n in nodes:
  if 'children' in n:yield from leaves(n['children'])
  else:yield n
cases=[]
for path in sorted(P.glob('*-cv12_ipe-trees-private.json')):
 for root in json.loads(path.read_text()):
  for leaf in leaves(root['core']):cases.append([*leaf['trigger'],*[leaf['data'][k] for k in fields]])
assert len(cases)==1350
cases.append([float(i+1) for i in range(16)])
for values in cases:
 src=D+0x1000;cursor=D+0x7000;out=D+0x8000;sp=h.STACK+0xf0000
 raw=b''.join(struct.pack('<fI',v,0) for v in values);assert len(raw)==128
 u.mem_write(src,raw);u.mem_write(out,bytes([0xa7])*96);u.mem_write(cursor-12,struct.pack('<IQQ',128,src,0));u.mem_write(sp+8,struct.pack('<Q',out))
 for reg,value in [(UC_ARM64_REG_SP,sp),(UC_ARM64_REG_X25,cursor),(UC_ARM64_REG_X22,8),(UC_ARM64_REG_X23,0),(UC_ARM64_REG_X8,1)]:u.reg_write(reg,value)
 u.emu_start(0x1f78d4,0x1f7ff8,timeout=1000000,count=3000);assert u.reg_read(UC_ARM64_REG_PC)==0x1f7ff8
 assert bytes(u.mem_read(out,64))==struct.pack('<16f',*values)
 assert bytes(u.mem_read(out+64,32))==bytes([0xa7])*32
 assert a.read64(cursor)==128
assert not a.providers
report=dict(stage=399,factory_regions=1350,directed_distinct_field_case=1,actual_target_parse_leaf_fragment_executed=True,fragment=['0x1f78d4','0x1f7ff8'],serialized_stride=8,native_float_stride=4,native_cct_leaf_bytes=64,native_numeric_data_offset=8,native_numeric_field_order=fields,original_deserializer_reorders_no_fields=True,target_cv_packet_low_chroma_slots='ap bp cp dp',target_cv_packet_high_chroma_slots='am bm cm dm',previous398_am_ap_semantic_labels_withdrawn=True,previous398_unnamed_numeric_comparison_retained=True,phone_changed=False,passed=True)
(HERE/'native-leaf-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
