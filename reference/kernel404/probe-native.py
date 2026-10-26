"""Compare actual native prototype and original HAL through complete FW."""
from pathlib import Path
import ast,importlib.util,json,re,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
tree=ast.parse((HERE.parent/'kernel384/check-serializer.py').read_text());prefix=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='prefix' for t in n.targets))
prefix+='\nstruct camss_a5_ipe_ltm_geometry {bool data_collection,image_processing,mask_filter;};\n'
text=(P/'camss-icp-a5-ipe.c.proposed').read_text();functions=[]
for name in ['ipe_partitions','camss_a5_ipe_bypass_partitions','camss_a5_ipe_ltm_partitions','camss_a5_ipe_bypass_size','bypass_module_1d','camss_a5_ipe_ltm_size','ipe_encode_striping','camss_a5_ipe_encode_ltm_striping']:
 match=re.search(r'(?:static )?(?:int|void)\s+'+name+r'\([^;]+?\n\{.*?^\}\n',text,re.S|re.M);assert match,name;functions.append(match[0])
main='''int main(void){u32 in[7],used;u8 out[32768];while(fread(in,sizeof in,1,stdin)==1){struct camss_a5_ipe_io io={.input={in[0],in[1],in[0],in[1],in[6]},.output={in[0],in[1],in[0],in[1],in[6]},.output_port=in[2]};struct camss_a5_ipe_ltm_geometry ltm={in[4],in[5],true};assert(!camss_a5_ipe_encode_ltm_striping(out,sizeof out,&io,in[3],&ltm,&used));assert(fwrite(&used,4,1,stdout)==1 && fwrite(out,1,used,stdout)==used);}return 0;}'''
(P/'native-ltm-model.c').write_text(prefix+'\n'.join(functions)+main);q=subprocess.run(['gcc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-no-pie',str(P/'native-ltm-model.c'),'-o',str(P/'native-ltm-model')],capture_output=True);assert not q.returncode,q.stderr.decode()
s=importlib.util.spec_from_file_location('oracle404',HERE/'oracle.py');o=importlib.util.module_from_spec(s);s.loader.exec_module(o)
cases=[(640,480,8,1,1,1,0),(640,480,8,1,0,1,0),(128,128,8,1,1,1,0),(326,480,8,1,1,1,0)]
q=subprocess.run([str(P/'native-ltm-model')],input=b''.join(struct.pack('<7I',*c) for c in cases),capture_output=True);assert not q.returncode,q.stderr.decode();pos=0;rows=[]
for w,h,p,c,dc,ip,swap in cases:
 size=struct.unpack_from('<I',q.stdout,pos)[0];pos+=4;native=q.stdout[pos:pos+size];pos+=size;iq=o.iq_blob(dc,ip);slug=f'{w}x{h}-p{p}-c{c}-dc{dc}-ip{ip}'
 gold=(P.parent/'kernel403'/(slug+'-original-stripe-private.bin')).read_bytes();original_cdm=(P.parent/'kernel403'/(slug+'-original-cdm-private.bin')).read_bytes();original_job=(P.parent/'kernel403'/(slug+'-original-job-private.bin')).read_bytes()
 m,job,commands=o.prepare(native,w,h,p,c,iq);assert len(commands)==len(original_cdm)
 (P/(slug+'-native-stripe-private.bin')).write_bytes(native);(P/(slug+'-native-cdm-private.bin')).write_bytes(commands)
 diff=[i for i,(a,b) in enumerate(zip(commands,original_cdm)) if a!=b]
 rows.append(dict(width=w,height=h,port=p,cores=c,dc=dc,ip=ip,different_cdm_bytes=len(diff),different_cdm_offsets=diff,job_equal=job==original_job,different_stripe_halfwords=[(i,struct.unpack_from('<H',native,i)[0],struct.unpack_from('<H',gold,i)[0]) for i in range(0,min(len(native),len(gold))//2*2,2) if native[i:i+2]!=gold[i:i+2]]));print(json.dumps({k:v for k,v in rows[-1].items() if k!='different_stripe_halfwords'}),flush=True)
(P/'native-probe-private.json').write_text(json.dumps(rows,indent=2)+'\n')
