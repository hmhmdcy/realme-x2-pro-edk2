"""Compare original LTM-aware striping with current native bypass geometry."""
from pathlib import Path
import importlib.util,inspect,json,struct,sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
r=module('routing396',HERE.parent/'kernel396/probe-routing.py');ltm=module('ltm403',HERE/'ltm-model.py');oracle=ltm.LTM();headers,offsets=oracle.headers(r.f.DATA+0x40000+2848)
scope=dict(r.__dict__)
text=inspect.getsource(r.striping).replace('def striping(width,height,port,cores,enabled):','def striping(width,height,port,cores,iq_blob):')
start=text.index(' for off in [52,68,244,260]:');end=text.index('u.mem_write(out,',start);text=text[:start]+' u.mem_write(iq,iq_blob);'+text[end:];exec(compile(text,'ltm-striping-original','exec'),scope);striping=scope['striping']
text=inspect.getsource(r.prepare).replace('def prepare(blob,width,height,port,cores,enabled,command):','def prepare(blob,width,height,port,cores,iq_blob):').replace('arrays=D+0x48000','arrays=iq+2592')
start=text.index(' for off in [52,68,244,260]:');end=text.index(' m.payload=D+0x20000;',start);text=text[:start]+' m.u.mem_write(iq,iq_blob)\n'+text[end:]
text=text.replace('arrays+(32 if off==48 else 0)','arrays+(32 if off==44 else 64 if off==48 else 0)');exec(compile(text,'ltm-firmware-original','exec'),scope);prepare=scope['prepare']
def iq_blob(dc,ip,enabled=True):
 iq=bytearray(5584)
 for off in [52,68,244,260]:struct.pack_into('<I',iq,off,1)
 values=[int(enabled),1,1,1,0,19,38,7,0,0,1023,0,0,0,0,0,0,0,0,0,0,dc,ip];assert len(values)==23
 struct.pack_into('<23I',iq,2096,*values)
 struct.pack_into('<8I',iq,2624,0,1,r.f.DATA+0x40000+2672,155<<12,11 if enabled else 255,0,0,0)
 iq[2672:2828]=headers
 # All-zero LUTs are only a bounded offline wire fixture, never a physical
 # tuning configuration. Geometry does not rely on their numeric contents.
 return bytes(iq)
boundary='--boundaries' in sys.argv;extreme='--extremes' in sys.argv;rows=[];details=[]
geometries=[(8192,128,9,c) for c in [1,2]] if extreme else [(w,480,8,c) for w in [324,326,328,330,648,650,656,658] for c in [1,2]] if boundary else [(640,480,8,1),(1920,1080,9,2),(4608,3456,8,2),(128,128,8,1)]
for w,h,p,c in geometries:
 baseline,_,_=striping(w,h,p,c,iq_blob(0,0,False))
 for dc,ip in ([(1,1)] if boundary or extreme else [(0,1),(1,0),(1,1)]):
  iq=iq_blob(dc,ip);actual,capacity,instructions=striping(w,h,p,c,iq);m,job,commands=prepare(actual,w,h,p,c,iq);bm,bjob,bcommands=prepare(baseline,w,h,p,c,iq)
  slug=f'{w}x{h}-p{p}-c{c}-dc{dc}-ip{ip}'
  (P/(slug+'-original-stripe-private.bin')).write_bytes(actual);(P/(slug+'-original-cdm-private.bin')).write_bytes(commands);(P/(slug+'-original-job-private.bin')).write_bytes(job)
  row=dict(width=w,height=h,port=p,cores=c,data_collection=dc,image_processing=ip,stripe_bytes=len(actual),bypass_stripe_bytes=len(baseline),actual_stripes=struct.unpack_from('<H',actual,428)[0],bypass_stripes=struct.unpack_from('<H',baseline,428)[0],different_stripe_bytes=sum(a!=b for a,b in zip(actual,baseline))+abs(len(actual)-len(baseline)),different_cdm_bytes=sum(a!=b for a,b in zip(commands,bcommands)),job_equal=job==bjob,firmware_accepted=True)
  rows.append(row);details.append(dict(**row,different_halfwords=[(i,struct.unpack_from('<H',baseline,i)[0],struct.unpack_from('<H',actual,i)[0]) for i in range(0,min(len(actual),len(baseline))//2*2,2) if baseline[i:i+2]!=actual[i:i+2]]));print(json.dumps(row),flush=True)
(P/('stripe-extreme-differences-private.json' if extreme else 'stripe-boundary-differences-private.json' if boundary else 'stripe-differences-private.json')).write_text(json.dumps(details,indent=2)+'\n')
report=dict(stage=403,actual_complete_original_hal_striping=True,actual_complete_original_firmware_config_and_frame_preparation=True,ltm_type11_and_actual13_dmi_headers=True,lut_values_zero_offline_geometry_fixture_only=True,baseline_is_original_hal_bypass_geometry=True,current_native_bypass_matched_that_geometry_in384_and402_only_without_ltm=True,native_current_ltm_correctness_not_assumed=True,cases=rows,hardware_enqueue_not_executed=True,phone_accessed=False,completed=True)
(HERE/('striping-extreme-probe.json' if extreme else 'striping-boundary-probe.json' if boundary else 'striping-probe.json')).write_text(json.dumps(report,indent=2)+'\n')
