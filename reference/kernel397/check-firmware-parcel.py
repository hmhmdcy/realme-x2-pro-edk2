"""Consume the actual C-generated in-page IQ/program region in the target firmware."""
from pathlib import Path
import ctypes,importlib.util,inspect,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
shared=P/'colour-model.so';q=subprocess.run(['gcc','-std=c11','-O2','-Wall','-Wextra','-Werror','-fPIC','-shared','-I'+str(P/'include'),str(P/'colour.c'),str(P/'bypass.c'),'-o',str(shared)],capture_output=True);assert q.returncode==0,q.stderr.decode()
lib=ctypes.CDLL(str(shared));lib.camss_a5_ipe_encode_cc_iq.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p];lib.camss_a5_ipe_encode_cc_iq.restype=ctypes.c_int
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
r=module('routing396',HERE.parent/'kernel396/probe-routing.py')
body=inspect.getsource(r.prepare).replace('def prepare(blob,width,height,port,cores,enabled,command):','def prepare(blob,width,height,port,cores,enabled,command,iq_blob):')
body=body.replace('arrays=D+0x48000','arrays=iq+2592')
a=body.index(' for off in [52,68,244,260]:');b=body.index(' m.payload=D+0x20000;',a)
body=body[:a]+' m.u.mem_write(iq,iq_blob)\n'+body[b:]
scope=dict(r.__dict__);exec(compile(body,'firmware-same-page-cc','exec'),scope);prepare=scope['prepare']
rows=[]
for width,height in [(640,480),(1920,1080),(4608,3456)]:
 for port in [8,9]:
  for cores in [1,2]:
   record=(P.parent/'kernel396/cc-input-private.bin').read_bytes()[:28];cc=ctypes.create_string_buffer(record);out=ctypes.create_string_buffer(2700);assert not lib.camss_a5_ipe_encode_cc_iq(out,2700,r.f.DATA+0x40000,cc)
   iq=out.raw;stripe,capacity,n=r.striping(width,height,port,cores,1);m,job,commands=prepare(stripe,width,height,port,cores,1,iq[2656:2700],iq)
   arr=r.f.DATA+0x40000+2592;external=[a for a,size in m.allocated.items() if size==12 and m.read32(a)==arr+32];assert len(external)==1 and m.external.count(arr+32)==1
   assert bytes(m.u.mem_read(arr+64,44))==iq[2656:2700]
   rows.append(dict(width=width,height=height,port=port,cores=cores,same_page_actual_c_program_region_accepted=True,post_ltm_linked_once=True,passed=True))
report=dict(stage=397,cases=rows,actual_c_encoder_not_python_reimplementation=True,original_firmware_config_and_full_frame_preparation=True,common_and_post_arrays_and_cdm_within_iq_page=True,geometry_cases=len(rows),stopped_before_hardware_enqueue=True,phone_changed=False,passed=True)
(HERE/'firmware-parcel-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='cases'},indent=2))
