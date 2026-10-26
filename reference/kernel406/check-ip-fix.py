"""Check the native correction and physical IP_EN via complete original FW."""
from pathlib import Path
import ast,ctypes,importlib.util,json,re,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
tree=ast.parse((HERE.parent/'kernel384/check-serializer.py').read_text());prefix=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='prefix' for t in n.targets))
prefix+='\nstruct camss_a5_ipe_ltm_geometry {bool data_collection,image_processing,mask_filter;};\n'
text=(P/'camss-icp-a5-ipe.c.proposed').read_text();functions=[]
for name in ['ipe_partitions','camss_a5_ipe_bypass_partitions','camss_a5_ipe_ltm_partitions','camss_a5_ipe_bypass_size','bypass_module_1d','camss_a5_ipe_ltm_size','ipe_encode_striping','camss_a5_ipe_encode_ltm_striping','camss_a5_ipe_encode_bypass_striping']:
 match=re.search(r'(?:static )?(?:int|void)\s+'+name+r'\([^;]+?\n\{.*?^\}\n',text,re.S|re.M);assert match,name;functions.append(match[0])
main='''int main(void){u32 in[8],used,legacy;u8 out[32768],bypass[32768];while(fread(in,sizeof in,1,stdin)==1){struct camss_a5_ipe_io io={.input={in[0],in[1],in[0],in[1],in[6]},.output={in[0],in[1],in[0],in[1],in[6]},.output_port=in[2]};struct camss_a5_ipe_ltm_geometry ltm={in[4],in[5],in[7]};memset(out,0xa5,sizeof out);assert(!camss_a5_ipe_encode_ltm_striping(out,sizeof out,&io,in[3],&ltm,&used));for(unsigned i=used;i<sizeof out;i++)assert(out[i]==0xa5);if(!in[5]){assert(!camss_a5_ipe_encode_bypass_striping(bypass,sizeof bypass,&io,in[3],&legacy) && legacy==used && !memcmp(out,bypass,used));}assert(fwrite(&used,4,1,stdout)==1 && fwrite(out,1,used,stdout)==used);}return 0;}'''
(P/'ip-enable-model.c').write_text(prefix+'\n'.join(functions)+main)
cases=[(w,h,p,c,dc,ip,swap,mask) for w,h,p,c,swap in [(128,128,8,1,0),(282,210,9,2,1),(640,480,8,2,0),(650,480,9,2,1)] for dc in [0,1] for ip in [0,1] for mask in [0,1]]
inputs=b''.join(struct.pack('<8I',*c) for c in cases);outputs=[]
for arch,cc,flags,launch in [('host','gcc',['-fsanitize=address,undefined','-no-pie'],[]),('aarch64','aarch64-linux-gnu-gcc',['-static'],['qemu-aarch64'])]:
 binary=P/('ip-enable-'+arch);q=subprocess.run([cc,'-std=gnu11','-O2','-Wall','-Wextra','-Werror',*flags,str(P/'ip-enable-model.c'),'-o',str(binary)],capture_output=True);assert not q.returncode,q.stderr.decode();q=subprocess.run([*launch,str(binary)],input=inputs,capture_output=True);assert not q.returncode,q.stderr.decode();outputs.append(q.stdout)
assert outputs[0]==outputs[1]
q=subprocess.run([str(P.parent/'kernel404/iq-geometry-host')],input=inputs,capture_output=True);assert not q.returncode,q.stderr.decode();old=q.stdout
s=importlib.util.spec_from_file_location('geometry404',HERE.parent/'kernel404/oracle.py');o=importlib.util.module_from_spec(s);s.loader.exec_module(o);scope=dict(o.scope);exec(compile(o.text.replace('64 if off==48','96 if off==48'),'ltm-ip-fixed-fw','exec'),scope);prepare=scope['prepare']
lib=ctypes.CDLL(str(P.parent/'kernel405/combined-colour.so'));lib.camss_a5_ipe_encode_ltm_iq.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p];lib.camss_a5_ipe_encode_ltm_iq.restype=ctypes.c_int
pos=oldpos=0;rows=[]
for w,h,p,c,dc,ip,swap,mask in cases:
 size=struct.unpack_from('<I',outputs[0],pos)[0];pos+=4;native=outputs[0][pos:pos+size];pos+=size;oldsize=struct.unpack_from('<I',old,oldpos)[0];oldpos+=4;previous=old[oldpos:oldpos+oldsize];oldpos+=oldsize;assert size==oldsize
 assert native[:416]==previous[:416] and native[420:]==previous[420:] and struct.unpack_from('<I',native,416)[0]==ip
 values=[0,0,mask,0,19,38,7,0,0,1023,0,0,0,0,0,0,0,0,0,0,dc,ip];typed=bytearray(2800);struct.pack_into('<22I',typed,0,*values);ltm=ctypes.create_string_buffer(bytes(typed));out=ctypes.create_string_buffer(8944)
 assert not lib.camss_a5_ipe_encode_ltm_iq(out,8944,o.r.f.DATA+0x40000,None,None,ltm);iq=out.raw
 _,oldjob,oldcmd=prepare(previous,w,h,p,c,iq,bool(swap));_,newjob,newcmd=prepare(native,w,h,p,c,iq,bool(swap));assert oldjob==newjob
 differences=[i for i in range(0,len(newcmd),4) if oldcmd[i:i+4]!=newcmd[i:i+4]];assert len(differences)<=1
 for i in differences:assert struct.unpack_from('<I',newcmd,i-4)[0]==0x5c60 and struct.unpack_from('<I',newcmd,i)[0]^struct.unpack_from('<I',oldcmd,i)[0]==0x400
 control=[struct.unpack_from('<I',newcmd,i+4)[0] for i in range(0,len(newcmd)-4,4) if struct.unpack_from('<I',newcmd,i)[0]==0x5c60];assert control and all(bool(v&0x400)==bool(ip) for v in control)
 rows.append(dict(width=w,height=h,port=p,cores=c,data_collection=dc,image_processing=ip,mask_filter=mask,uv_swap=bool(swap),only_full_pass_ip_field_may_change=True,changed_cdm_words=len(differences),only_ltm_ip_enable_bit_changes=True,hardware_ip_enable_matches_request=True,job_unchanged=True,passed=True));print(json.dumps(rows[-1]),flush=True)
report=dict(stage=406,cases=rows,host_asan_ubsan=True,aarch64_qemu=True,actual_proposed_native_functions=True,complete_original_firmware_preparation=True,intentional_divergence_from_original_hal_dc_coarse_pass_policy=True,explicit_full_frame_request_not_multipass_hal_policy=True,bypass_when_ip0_byte_identical=True,full_frame_ip_register_bit10_matches_request=True,all_other_cdm_bits_and_job_unchanged=True,hardware_pixels_pending=True,passed=True)
(HERE/'ip-enable-validation.json').write_text(json.dumps(report,indent=2)+'\n')
