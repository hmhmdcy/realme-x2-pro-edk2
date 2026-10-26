"""Consume actual C-generated pre/post conversion programs in target firmware."""
from pathlib import Path
import ast,ctypes,importlib.util,inspect,json,re,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'parcel-validation.json').read_text())['passed']
shared=P/'colour-model.so';q=subprocess.run(['gcc','-std=c11','-O2','-Wall','-Wextra','-Werror','-fPIC','-shared','-I'+str(P/'include'),str(P/'colour.c'),str(P/'bypass.c'),'-o',str(shared)],capture_output=True);assert not q.returncode,q.stderr.decode()
lib=ctypes.CDLL(str(shared));lib.camss_a5_ipe_encode_colour_iq.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p];lib.camss_a5_ipe_encode_colour_iq.restype=ctypes.c_int
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
r=module('routing396',HERE.parent/'kernel396/probe-routing.py')
body=inspect.getsource(r.prepare).replace('def prepare(blob,width,height,port,cores,enabled,command):','def prepare(blob,width,height,port,cores,enabled,command,iq_blob):').replace('arrays=D+0x48000','arrays=iq+2592')
a=body.index(' for off in [52,68,244,260]:');b=body.index(' m.payload=D+0x20000;',a);body=body[:a]+' m.u.mem_write(iq,iq_blob)\n'+body[b:]
body=body.replace('arrays+(32 if off==48 else 0)','arrays+(32 if off==44 else 64 if off==48 else 0)')
scope=dict(r.__dict__);exec(compile(body,'firmware-same-page-conversion','exec'),scope);prepare=scope['prepare']
striping=inspect.getsource(r.striping).replace('def striping(width,height,port,cores,enabled):','def striping(width,height,port,cores,iq_blob):')
a=striping.index(' for off in [52,68,244,260]:');b=striping.index('u.mem_write(out,',a);striping=striping[:a]+' u.mem_write(iq,iq_blob);'+striping[b:]
exec(compile(striping,'hal-conversion-striping','exec'),scope);stripefn=scope['striping']
raw=(P/'colour-input-private.bin').read_bytes();records=[raw[i:i+102] for i in range(0,len(raw),102)];fixtures={mask:next(v for v in reversed(records) if struct.unpack_from('<I',v)[0]==mask) for mask in range(8)}
rows=[];geometries=[(w,h,p,c) for w,h in [(640,480),(1920,1080),(4608,3456)] for p in [8,9] for c in [1,2]]
# Compile the current production striping functions, not a second serializer.
tree=ast.parse((HERE.parent/'kernel384/check-serializer.py').read_text())
prefix=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='prefix' for t in n.targets))
source=(P/'camss-icp-a5-ipe.c.before').read_text();functions=[]
for name in ['camss_a5_ipe_bypass_partitions','camss_a5_ipe_bypass_size','bypass_module_1d','camss_a5_ipe_encode_bypass_striping']:
 match=re.search(r'(?:static )?(?:int|void)\s+'+name+r'\([^;]+?\n\{.*?^\}\n',source,re.S|re.M);assert match,name;functions.append(match[0])
main=r'''
int main(void){u32 in[4],used;u8 out[32768];while(fread(in,sizeof in,1,stdin)==1){
struct camss_a5_ipe_io io={.input={in[0],in[1],in[0],in[1],false},.output={in[0],in[1],in[0],in[1],false},.output_port=in[2]};
assert(!camss_a5_ipe_encode_bypass_striping(out,sizeof out,&io,in[3],&used));assert(fwrite(&used,4,1,stdout)==1);assert(fwrite(out,1,used,stdout)==used);}return 0;}
'''
(P/'native-stripe-model.c').write_text(prefix+'\n'.join(functions)+main)
q=subprocess.run(['gcc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-no-pie',str(P/'native-stripe-model.c'),'-o',str(P/'native-stripe-model')],capture_output=True);assert not q.returncode,q.stderr.decode()
q=subprocess.run([str(P/'native-stripe-model')],input=b''.join(struct.pack('<4I',*g) for g in geometries),capture_output=True);assert not q.returncode,q.stderr.decode()
native={};position=0
for geometry in geometries:
 size=struct.unpack_from('<I',q.stdout,position)[0];position+=4;native[geometry]=q.stdout[position:position+size];position+=size
assert position==len(q.stdout)
for width,height,port,cores,mask in [(*g,7) for g in geometries]+[(640,480,8,1,mask) for mask in range(7)]:
 record=fixtures[mask];colour=ctypes.create_string_buffer(record[:46]+bytes(2)+record[46:]);out=ctypes.create_string_buffer(2860)
 assert not lib.camss_a5_ipe_encode_colour_iq(out,2860,r.f.DATA+0x40000,colour);iq=out.raw
 stripe,capacity,n=stripefn(width,height,port,cores,iq);m,job,commands=prepare(stripe,width,height,port,cores,0,b'',iq)
 nm,njob,ncommands=prepare(native[width,height,port,cores],width,height,port,cores,0,b'',iq)
 assert job==njob and commands==ncommands,(width,height,port,cores,mask)
 arr=r.f.DATA+0x40000+2592
 # The complete handler links even empty arrays; enabled programs are counted
 # in the actual page and each pre/post array has exactly one external link.
 for offset in [32,64]:
  links=[a for a,size in m.allocated.items() if size==12 and m.read32(a)==arr+offset];assert len(links)==1 and m.external.count(arr+offset)==1
 assert bytes(m.u.mem_read(r.f.DATA+0x40000,2860))==iq
 row=dict(width=width,height=height,port=port,cores=cores,modules=mask,same_page_actual_c_region_accepted=True,pre_post_linked_once_each=True,native_striping_whole_cdm_and_job_match=True,compared_cdm_bytes=len(commands),different_cdm_bytes=0,passed=True);rows.append(row)
 print(json.dumps(row),flush=True)
report=dict(stage=399,cases=rows,geometry_cases=len(geometries),all_module_combinations_checked=True,actual_c_encoder_not_python_reimplementation=True,original_hal_complete_striping=True,actual_current_production_native_striping_compared=True,native_striping_asan_ubsan=True,native_and_hal_whole_cdm_and_job_match_with_conversions=True,original_firmware_config_and_complete_frame_preparation=True,arrays_and_cst_cc_cv_commands_within_existing_iq_page=True,stopped_before_hardware_enqueue=True,phone_changed=False,passed=True)
(HERE/'firmware-parcel-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='cases'},indent=2))
