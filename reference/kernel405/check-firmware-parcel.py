"""Consume the native combined IQ/LUT page through complete original FW."""
from pathlib import Path
import ctypes,json,struct,subprocess,sys
import host
from oracle import module,HERE
P=host.PRIVATE;assert json.loads((HERE/'parcel-validation.json').read_text())['passed']
o=module('geometry404',HERE.parent/'kernel404/oracle.py');scope=dict(o.scope)
text=o.text.replace('64 if off==48','96 if off==48');assert text!=o.text
exec(compile(text,'ltm-combined-original-fw','exec'),scope);prepare=scope['prepare']
shared=P/'combined-colour.so';q=subprocess.run(['gcc','-std=c11','-O2','-Wall','-Wextra','-Werror','-fPIC','-shared','-I'+str(P/'include'),str(P/'colour.c'),str(P/'bypass.c'),'-o',str(shared)],capture_output=True);assert not q.returncode,q.stderr.decode()
lib=ctypes.CDLL(str(shared));lib.camss_a5_ipe_encode_ltm_iq.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p];lib.camss_a5_ipe_encode_ltm_iq.restype=ctypes.c_int
raw=(P/'ltm-input-private.bin').read_bytes();records=[raw[i:i+5988] for i in range(0,len(raw),5988)]
cases=[(650,210,8,2,swap,index) for swap in [0,1] for index in range(16)]
cases += [(128,128,9,2,0,127),(1920,1080,9,2,1,127),(4608,3456,8,2,0,127),(8192,128,9,1,1,127),(326,210,9,1,0,87)]
extra='--extra' in sys.argv
if extra:cases=[(650,210,8,2,1,index) for index in range(112,128)]+[(650,210,8,2,0,index) for index in [39,47,71,87,103,111]]
inputs=[];pages=[]
for w,h,p,c,swap,index in cases:
 record=records[index];has_colour,has_gamma,_=struct.unpack_from('<3I',record);colour=ctypes.create_string_buffer(record[12:116]);gamma=ctypes.create_string_buffer(record[116:3188]);ltm=ctypes.create_string_buffer(record[3188:]);out=ctypes.create_string_buffer(8944)
 assert not lib.camss_a5_ipe_encode_ltm_iq(out,8944,o.r.f.DATA+0x40000,colour if has_colour else None,gamma if has_gamma else None,ltm)
 iq=out.raw;dc,ip=struct.unpack_from('<2I',iq,2180);mask=struct.unpack_from('<I',iq,2108)[0];inputs.append(struct.pack('<8I',w,h,p,c,dc,ip,swap,mask));pages.append(iq)
assert (P/'camss-icp-a5-ipe.c.before').read_bytes()==(P.parent/'kernel404/camss-icp-a5-ipe.c.proposed').read_bytes()
q=subprocess.run([str(P.parent/'kernel404/iq-geometry-host')],input=b''.join(inputs),capture_output=True);assert not q.returncode,q.stderr.decode();position=0;rows=[]
for (w,h,p,c,swap,index),iq in zip(cases,pages):
 size=struct.unpack_from('<I',q.stdout,position)[0];position+=4;native=q.stdout[position:position+size];position+=size
 gold,_,instructions=o.striping(w,h,p,c,iq,bool(swap));m,job,cdm=prepare(gold,w,h,p,c,iq,bool(swap));_,nj,nc=prepare(native,w,h,p,c,iq,bool(swap))
 assert job==nj and cdm==nc,(w,h,p,c,swap,index)
 arr=o.r.f.DATA+0x40000+2592
 for offset in [32,96]:
  links=[a for a,size in m.allocated.items() if size==12 and m.read32(a)==arr+offset];assert len(links)==1 and m.external.count(arr+offset)==1
 assert bytes(m.u.mem_read(o.r.f.DATA+0x40000,8944))==iq
 row=dict(width=w,height=h,port=p,cores=c,uv_swap=bool(swap),case=index,pre_count=struct.unpack_from('<I',iq,2628)[0],post_count=struct.unpack_from('<I',iq,2692)[0],gamma_enabled=bool(struct.unpack_from('<I',iq,2192)[0]),data_collection=struct.unpack_from('<I',iq,2180)[0],image_processing=struct.unpack_from('<I',iq,2184)[0],mask_filter=struct.unpack_from('<I',iq,2108)[0],compared_cdm_bytes=len(cdm),different_cdm_bytes=0,job_equal=True,pre_post_linked_once=True,iq_lut_page_unchanged=True,passed=True);rows.append(row);print(json.dumps(row),flush=True)
if extra:
 original=json.loads((HERE/'firmware-parcel-validation.json').read_text());rows=original['cases'][:37]+rows
report=dict(stage=405,cases=rows,actual_combined_c_page=True,unchanged404_actual_native_geometry_reused=True,original_complete_hal_striping_and_firmware_frame_preparation=True,pre32_post96_offsets=True,pre_cst20_and_ltm11=True,post_cc_cv20_and_optional_gamma12=True,luts_in_same_retained_iq_region=True,hardware_enqueue_not_executed=True,phone_accessed=False,passed=True)
(HERE/'firmware-parcel-validation.json').write_text(json.dumps(report,indent=2)+'\n')
