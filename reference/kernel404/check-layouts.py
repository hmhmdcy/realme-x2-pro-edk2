"""Exercise padded input/output layouts and the shared bypass API."""
from pathlib import Path
import json,struct,subprocess
import host
import oracle as o
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
code=(P/'serializer-model.c').read_text();prefix=code[:code.index('int main(void)')]
main=r'''
int main(void){u32 in[11],used,legacy;u8 out[32768],plain[32768];while(fread(in,sizeof in,1,stdin)==1){
struct camss_a5_ipe_io io={.input={in[0],in[1],in[7],in[8],in[6]},.output={in[0],in[1],in[9],in[10],in[6]},.output_port=in[2]},tight=io;
struct camss_a5_ipe_ltm_geometry ltm={in[4],in[5],true};assert(!camss_a5_ipe_encode_ltm_striping(out,sizeof out,&io,in[3],&ltm,&used));
tight.input.stride=tight.output.stride=in[0];tight.input.slice_height=tight.output.slice_height=in[1];
assert(!camss_a5_ipe_encode_ltm_striping(plain,sizeof plain,&tight,in[3],&ltm,&legacy) && used==legacy && !memcmp(out,plain,used));
if(!in[4]&&!in[5])assert(!camss_a5_ipe_encode_bypass_striping(plain,sizeof plain,&io,in[3],&legacy) && used==legacy && !memcmp(out,plain,used));
assert(fwrite(&used,4,1,stdout)==1 && fwrite(out,1,used,stdout)==used);}return 0;}
'''
(P/'layout-model.c').write_text(prefix+main)
cases=[(w,h,p,c,dc,ip,swap,w+32,h+16,w+64,h+32) for w,h,p,c,swap in [(640,480,8,1,0),(1920,1080,9,2,1),(326,210,9,1,1),(650,212,8,2,0)] for dc,ip in [(0,0),(0,1),(1,0),(1,1)]]
inputs=b''.join(struct.pack('<11I',*c) for c in cases);outputs=[]
for arch,cc,flags,launch in [('host','gcc',['-fsanitize=address,undefined','-no-pie'],[]),('aarch64','aarch64-linux-gnu-gcc',['-static'],['qemu-aarch64'])]:
 binary=P/('layouts-'+arch);q=subprocess.run([cc,'-std=gnu11','-O2','-Wall','-Wextra','-Werror',*flags,str(P/'layout-model.c'),'-o',str(binary)],capture_output=True);assert not q.returncode,q.stderr.decode()
 q=subprocess.run([*launch,str(binary)],input=inputs,capture_output=True);assert not q.returncode,q.stderr.decode();outputs.append(q.stdout)
assert outputs[0]==outputs[1];pos=0;rows=[]
for w,h,p,c,dc,ip,swap,ins,inh,outs,outh in cases:
 size=struct.unpack_from('<I',outputs[0],pos)[0];pos+=4;native=outputs[0][pos:pos+size];pos+=size;iq=o.iq_blob(dc,ip);layouts=((ins,inh,ins,inh//2),(outs,outh,outs,outh//2))
 gold,_,instructions=o.striping(w,h,p,c,iq,bool(swap),layouts=layouts)
 _,job,cdm=o.prepare(gold,w,h,p,c,iq,bool(swap),layouts=layouts);_,nj,nc=o.prepare(native,w,h,p,c,iq,bool(swap),layouts=layouts)
 different=sum(a!=b for a,b in zip(cdm,nc));assert not different and nj==job and len(gold)==size,(w,h,p,c,dc,ip,different)
 rows.append(dict(width=w,height=h,port=p,cores=c,data_collection=dc,image_processing=ip,uv_swap=bool(swap),input_stride=ins,input_slice=inh,output_stride=outs,output_slice=outh,whole_cdm_bytes=len(cdm),different_cdm_bytes=different,job_equal=True,passed=True));print(json.dumps(rows[-1]),flush=True)
report=dict(stage=404,cases=rows,actual_native_c=True,host_asan_ubsan=True,aarch64_qemu=True,padded_input_output_layouts=True,bypass_wrapper_compared=True,zero_luts_offline_geometry_only=True,original_full_hal_and_firmware=True,phone_accessed=False,passed=True)
(HERE/'layouts-validation.json').write_text(json.dumps(report,indent=2)+'\n')
