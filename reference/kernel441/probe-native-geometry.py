"""Reuse retained native HAL to recover DC/full-pass geometry for video sizes."""
from pathlib import Path
import hashlib,importlib.util,json,struct,time,sys
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;storage.mount.mounted_build()
s=importlib.util.spec_from_file_location('native425',HERE.parent/'kernel425/native-model.py');n=importlib.util.module_from_spec(s);s.loader.exec_module(n)
baseline=(P.parent/'kernel425/width-640-dc-1-config-private.bin').read_bytes();iq=(P.parent/'kernel424/coarse-width-640-dc-1-iq-private.bin').read_bytes()
rows=[];edges='--edges' in sys.argv
for width,height in ([(1296,720),(1304,720),(1600,900)] if edges else [(640,480),(1280,720),(1920,1080)]):
 native=n.Native();qw,qh=((width+7)//4)&~1,((height+7)//4)&~1
 image,descriptor=native.pd10(qw,qh)
 config=bytearray(baseline)
 for port in [0,8]:
  at=port*84;struct.pack_into('<2I',config,at+4,width,height);struct.pack_into('<4I',config,at+52,width,height,width,height//2)
 config[84:168]=descriptor;struct.pack_into('<I',config,1200,3)
 begin=time.monotonic();stripe,bl,capacity=native.striping(bytes(config),width,height,1,iq)
 passes=struct.unpack_from('<I',stripe,20)[0];assert passes==2
 pass_rows=[]
 for index in range(passes):
  at=20+412*index;count=struct.unpack_from('<H',stripe,at+408)[0];relative=struct.unpack_from('<I',stripe,at+412)[0]
  # Header-relative stripe array; each pass has its own 412-byte record.
  first=at+relative;assert first+count*624<=len(stripe)
  axis=at+4
  def read16(off):return struct.unpack_from('<H',stripe,axis+off)[0]
  parts=[]
  for j in range(count):
   a=first+j*624;part={str(off):struct.unpack_from('<H',stripe,a+off)[0] for off in [4,6,12,14,20,22,30,44,48+34,48+60,48+64,48+66,48+76,48+80,48+84,48+86,48+88,48+90,48+276,48+278,48+282,318,322,604]}
   part['area']=struct.unpack_from('<I',stripe,a+600)[0];parts.append(part)
  pass_rows.append(dict(index=index,stripes=count,array_offset=first,vertical={str(off):read16(off) for off in [34,60,64,66,84,86,270,274,278,282,352,360,376,390,404]},parts=parts))
 slug=f'{width}x{height}'
 for name,raw in [('config',bytes(config)),('stripe',stripe),('iq',iq)]: (P/f'{slug}-{name}-private.bin').write_bytes(raw)
 row=dict(width=width,height=height,cores=1,quarter_width=qw,quarter_height=qh,pd10_stride=struct.unpack_from('<I',descriptor,52)[0],pd10_slice=struct.unpack_from('<I',descriptor,56)[0],passes=pass_rows,used_bytes=len(stripe),capacity=capacity,native_minimum_bl_bytes=bl,native_instructions=native.instructions,seconds=round(time.monotonic()-begin,2));rows.append(row)
 (P/'native-geometry-progress-private.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps({k:v for k,v in row.items() if k!='passes'}|{'stripes_per_pass':[r['stripes'] for r in pass_rows]}),flush=True)
report=dict(stage=441,source='retained original ARM64 HAL full Create/Execute/Destroy,format InitializeFormatParams/SetConfigIOData',coarse_topology=3,rows=rows,original_ltm_iq_reused_from_stage424=True,geometry_probe_only_not_new_iq_math_or_pixel_acceptance=True,phone_accessed=False,hardware_executed=False,passed=True)
(P/('native-geometry-edges-private.json' if edges else 'native-geometry-private.json')).write_text(json.dumps(report,indent=2)+'\n')
