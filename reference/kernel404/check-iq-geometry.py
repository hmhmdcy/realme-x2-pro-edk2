"""Ensure native geometry survives independent legal LTM IQ field changes."""
from pathlib import Path
import ast,json,random,re,struct,subprocess
import host
import oracle as o
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
fields=json.loads((HERE.parent/'kernel403/contract-validation.json').read_text())['iq_fields'];rng=random.Random(404)
cases=[]
for w,h,p,c,swap in [(640,480,8,1,0),(650,210,9,2,1),(128,128,9,2,0),(8192,128,8,1,1)]:
 for dc,ip in [(0,0),(0,1),(1,0),(1,1)]:
  iq=bytearray(o.iq_blob(dc,ip))
  for field in fields[1:-2]:struct.pack_into('<I',iq,field['offset'],rng.randrange(1<<field['width']))
  cases.append(((w,h,p,c,dc,ip,swap,struct.unpack_from('<I',iq,2108)[0]),bytes(iq)))
for w,h,p,c,swap in [(640,480,8,1,0),(650,210,9,2,1)]:
 for dc in [0,1]:
  for ip in [0,1]:
   for mask in [0,1]:
    iq=bytearray(o.iq_blob(dc,ip));struct.pack_into('<I',iq,2108,mask);cases.append(((w,h,p,c,dc,ip,swap,mask),bytes(iq)))
tree=ast.parse((HERE.parent/'kernel384/check-serializer.py').read_text());prefix=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='prefix' for t in n.targets))
prefix+='\nstruct camss_a5_ipe_ltm_geometry {bool data_collection,image_processing,mask_filter;};\n'
source=(P/'camss-icp-a5-ipe.c.proposed').read_text();functions=[]
for name in ['ipe_partitions','camss_a5_ipe_bypass_partitions','camss_a5_ipe_ltm_partitions','camss_a5_ipe_bypass_size','bypass_module_1d','camss_a5_ipe_ltm_size','ipe_encode_striping','camss_a5_ipe_encode_ltm_striping']:
 match=re.search(r'(?:static )?(?:int|void)\s+'+name+r'\([^;]+?\n\{.*?^\}\n',source,re.S|re.M);assert match,name;functions.append(match[0])
main='''int main(void){u32 in[8],used;u8 out[32768];while(fread(in,sizeof in,1,stdin)==1){struct camss_a5_ipe_io io={.input={in[0],in[1],in[0],in[1],in[6]},.output={in[0],in[1],in[0],in[1],in[6]},.output_port=in[2]};struct camss_a5_ipe_ltm_geometry ltm={in[4],in[5],in[7]};assert(!camss_a5_ipe_encode_ltm_striping(out,sizeof out,&io,in[3],&ltm,&used));assert(fwrite(&used,4,1,stdout)==1 && fwrite(out,1,used,stdout)==used);}return 0;}'''
(P/'iq-geometry-model.c').write_text(prefix+'\n'.join(functions)+main)
outputs=[]
for arch,cc,flags,launch in [('host','gcc',['-fsanitize=address,undefined','-no-pie'],[]),('aarch64','aarch64-linux-gnu-gcc',['-static'],['qemu-aarch64'])]:
 binary=P/('iq-geometry-'+arch);q=subprocess.run([cc,'-std=gnu11','-O2','-Wall','-Wextra','-Werror',*flags,str(P/'iq-geometry-model.c'),'-o',str(binary)],capture_output=True);assert not q.returncode,q.stderr.decode()
 q=subprocess.run([*launch,str(binary)],input=b''.join(struct.pack('<8I',*c) for c,iq in cases),capture_output=True);assert not q.returncode,q.stderr.decode();outputs.append(q.stdout)
assert outputs[0]==outputs[1];pos=0;rows=[]
for index,((w,h,p,c,dc,ip,swap,mask),iq) in enumerate(cases):
 size=struct.unpack_from('<I',outputs[0],pos)[0];pos+=4;native=outputs[0][pos:pos+size];pos+=size
 gold,_,instructions=o.striping(w,h,p,c,iq,bool(swap));_,job,cdm=o.prepare(gold,w,h,p,c,iq,bool(swap));_,nj,nc=o.prepare(native,w,h,p,c,iq,bool(swap))
 diff=sum(a!=b for a,b in zip(cdm,nc));row=dict(case=index,width=w,height=h,port=p,cores=c,data_collection=dc,image_processing=ip,mask_filter=mask,uv_swap=bool(swap),native_bytes=size,original_bytes=len(gold),different_cdm_bytes=diff,job_equal=job==nj,passed=not diff and job==nj and size==len(gold));rows.append(row);print(json.dumps(row),flush=True)
 if not row['passed']:
  for kind,data in [('iq',iq),('original-stripe',gold),('native-stripe',native),('original-cdm',cdm),('native-cdm',nc)]: (P/f'iq-case{index}-{kind}-private.bin').write_bytes(data)
report=dict(stage=404,cases=rows,random_seed=404,independent_valid_iq_values=True,explicit_dc_ip_mask_boolean_combinations=True,host_asan_ubsan=True,aarch64_qemu=True,geometry_native_actual_c=True,complete_original_hal_and_firmware=True,zero_luts_offline_only=True,phone_accessed=False,passed=all(r['passed'] for r in rows))
(HERE/'iq-geometry-validation.json').write_text(json.dumps(report,indent=2)+'\n');assert report['passed']
