"""Compare native LTM geometry through complete target FW, with original HAL."""
from pathlib import Path
import ast,hashlib,json,re,struct,subprocess
import host
import oracle as o
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
tree=ast.parse((HERE.parent/'kernel384/check-serializer.py').read_text());prefix=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='prefix' for t in n.targets))
prefix+='\nstruct camss_a5_ipe_ltm_geometry {bool data_collection,image_processing,mask_filter;};\n'
text=(P/'camss-icp-a5-ipe.c.proposed').read_text();functions=[]
for name in ['ipe_partitions','camss_a5_ipe_bypass_partitions','camss_a5_ipe_ltm_partitions','camss_a5_ipe_bypass_size','bypass_module_1d','camss_a5_ipe_ltm_size','ipe_encode_striping','camss_a5_ipe_encode_bypass_striping','camss_a5_ipe_encode_ltm_striping']:
 match=re.search(r'(?:static )?(?:int|void)\s+'+name+r'\([^;]+?\n\{.*?^\}\n',text,re.S|re.M);assert match,name;functions.append(match[0])
main=r'''
int main(void){u32 in[7],used,size;u8 out[32768],saved[32768];
struct camss_a5_ipe_io valid={.input={640,480,640,480,false},.output={640,480,640,480,false},.output_port=8};
for(unsigned flags=0;flags<8;flags++){
struct camss_a5_ipe_ltm_geometry ltm={flags&1,!!(flags&2),!!(flags&4)};
memset(out,0xa5,sizeof out);memcpy(saved,out,sizeof out);used=size=0xdeadbeef;
assert(camss_a5_ipe_ltm_size(NULL,1,&ltm,&size)==-EINVAL && size==0xdeadbeef);
assert(camss_a5_ipe_ltm_size(&valid,1,NULL,&size)==-EINVAL && size==0xdeadbeef);
assert(camss_a5_ipe_ltm_size(&valid,1,&ltm,NULL)==-EINVAL);
assert(camss_a5_ipe_encode_ltm_striping(NULL,sizeof out,&valid,1,&ltm,&used)==-EINVAL);
assert(camss_a5_ipe_encode_ltm_striping(out,sizeof out,&valid,1,&ltm,NULL)==-EINVAL);
assert(camss_a5_ipe_encode_ltm_striping(out,sizeof out,&valid,1,NULL,&used)==-EINVAL);
for(unsigned i=0;i<21;i++){
struct camss_a5_ipe_io bad=valid;u32 core=1,cap=sizeof out;
switch(i){case 0:bad.input.width=126;break;case 1:bad.input.width=8194;break;case 2:bad.input.height=126;break;case 3:bad.input.height=8194;break;
case 4:bad.input.width=641;break;case 5:bad.input.height=481;break;case 6:bad.output.width=642;break;case 7:bad.output.height=482;break;
case 8:bad.output.uv_swap=true;break;case 9:bad.output_port=7;break;case 10:core=0;break;case 11:core=3;break;
case 12:bad.input.stride=639;break;case 13:bad.output.stride=638;break;case 14:bad.input.slice_height=478;break;case 15:bad.output.slice_height=479;break;
case 16:cap=3515;break;case 17:bad.input.width=0xffffffff;break;case 18:bad.input.slice_height=0xffffffff;break;
case 19:bad.output_port=10;break;case 20:bad.input.height=0;break;}
int ret=camss_a5_ipe_encode_ltm_striping(out,cap,&bad,core,&ltm,&used);
assert(ret==(i==16?-ENOSPC:-EINVAL) && used==0xdeadbeef && !memcmp(out,saved,sizeof out));
}
}
while(fread(in,sizeof in,1,stdin)==1){struct camss_a5_ipe_io io={.input={in[0],in[1],in[0],in[1],in[6]},.output={in[0],in[1],in[0],in[1],in[6]},.output_port=in[2]};
struct camss_a5_ipe_ltm_geometry ltm={in[4],in[5],true};memset(out,0xa5,sizeof out);
assert(!camss_a5_ipe_ltm_size(&io,in[3],&ltm,&size));assert(!camss_a5_ipe_encode_ltm_striping(out,sizeof out,&io,in[3],&ltm,&used) && used==size);
for(unsigned i=used;i<sizeof out;i++)assert(out[i]==0xa5);
if(!in[4] && !in[5]){u32 legacy;assert(!camss_a5_ipe_encode_bypass_striping(saved,sizeof saved,&io,in[3],&legacy) && legacy==used && !memcmp(out,saved,used));}
assert(fwrite(&used,4,1,stdout)==1 && fwrite(out,1,used,stdout)==used);}return 0;}
'''
(P/'serializer-model.c').write_text(prefix+'\n'.join(functions)+main)
cases=[]
for filename in ['striping-probe.json','striping-boundary-probe.json','striping-extreme-probe.json']:
 for row in json.loads((HERE.parent/'kernel403'/filename).read_text())['cases']:cases.append(tuple(row[k] for k in ['width','height','port','cores','data_collection','image_processing'])+(0,))
cases += [(w,h,8,c,1,1,0) for w,h in [(286,214),(288,214),(286,216),(288,216),(290,218),(144,128),(142,128),(128,8192),(8192,8192),(280,208),(282,208),(280,210),(282,210),(284,212),(128,210),(282,128)] for c in [1,2]]
cases += [(w,h,p,c,dc,ip,1) for w,h,p,c in [(640,480,8,1),(1920,1080,9,2),(326,216,9,1),(650,218,8,2)] for dc,ip in [(0,0),(0,1),(1,0),(1,1)]]
inputs=b''.join(struct.pack('<7I',*c) for c in cases);outputs=[];architectures=[]
for arch,compiler,flags,launch in [('host','gcc',['-fsanitize=address,undefined','-no-pie'],[]),('aarch64','aarch64-linux-gnu-gcc',['-static'],['qemu-aarch64'])]:
 binary=P/('serializer-'+arch);q=subprocess.run([compiler,'-std=gnu11','-O2','-Wall','-Wextra','-Werror',*flags,str(P/'serializer-model.c'),'-o',str(binary)],capture_output=True);assert not q.returncode,q.stderr.decode()
 q=subprocess.run([*launch,str(binary)],input=inputs,capture_output=True);assert not q.returncode,q.stderr.decode();outputs.append(q.stdout);architectures.append(dict(architecture=arch,cases=len(cases),output_bytes=len(q.stdout),passed=True))
assert outputs[0]==outputs[1];pos=0;rows=[]
for w,h,p,c,dc,ip,swap in cases:
 size=struct.unpack_from('<I',outputs[0],pos)[0];pos+=4;native=outputs[0][pos:pos+size];pos+=size;iq=o.iq_blob(dc,ip);slug=f'{w}x{h}-p{p}-c{c}-dc{dc}-ip{ip}'
 old=P.parent/'kernel403'/(slug+'-original-stripe-private.bin')
 if old.exists() and not swap:
  gold=old.read_bytes();cdm=(old.parent/(slug+'-original-cdm-private.bin')).read_bytes();job=(old.parent/(slug+'-original-job-private.bin')).read_bytes();instructions=None
 else:
  gold,_,instructions=o.striping(w,h,p,c,iq,bool(swap));_,job,cdm=o.prepare(gold,w,h,p,c,iq,bool(swap))
 _,native_job,native_cdm=o.prepare(native,w,h,p,c,iq,bool(swap));diff=[i for i,(a,b) in enumerate(zip(cdm,native_cdm)) if a!=b]
 row=dict(width=w,height=h,port=p,cores=c,data_collection=dc,image_processing=ip,uv_swap=bool(swap),stripe_bytes=size,original_stripe_bytes=len(gold),different_cdm_bytes=len(diff),job_equal=job==native_job,hal_instructions=instructions)
 rows.append(row)
 if diff or job!=native_job or len(gold)!=len(native):
  (P/(slug+f'-swap{swap}-failure-native-stripe-private.bin')).write_bytes(native);(P/(slug+f'-swap{swap}-failure-original-stripe-private.bin')).write_bytes(gold)
  (P/(slug+f'-swap{swap}-failure-private.json')).write_text(json.dumps(dict(**row,diff=diff),indent=2)+'\n')
 print(json.dumps(row),flush=True)
passed=all(not r['different_cdm_bytes'] and r['job_equal'] and r['stripe_bytes']==r['original_stripe_bytes'] for r in rows)
report=dict(stage=404,cases=rows,architectures=architectures,native_source_sha256=hashlib.sha256((P/'camss-icp-a5-ipe.c.proposed').read_bytes()).hexdigest(),mask_filter_enabled_for_these_cases=True,host_asan_ubsan=True,aarch64_qemu=True,invalid_inputs_preserve_outputs=True,output_tail_canary=True,actual_native_c=True,original_complete_hal_and_firmware=True,zero_luts_offline_geometry_only=True,phone_accessed=False,passed=passed)
(HERE/'serializer-validation.json').write_text(json.dumps(report,indent=2)+'\n');assert passed
