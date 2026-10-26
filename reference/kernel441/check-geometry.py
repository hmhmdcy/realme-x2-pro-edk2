"""Compile authored geometry and compare full original firmware programs."""
from pathlib import Path
import ast,importlib.util,json,re,struct,subprocess,sys
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;v=storage.mount.mounted_build().parent;k=v/'source354/drivers/media/platform/qcom/camss'
def function(text,name):
 m=re.search(r'(?:static )?(?:int|bool|void)\s+'+name+r'\([^;]+?\n\{.*?^\}\n',text,re.S|re.M);assert m,name;return m[0]
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
tree=ast.parse((HERE.parent/'kernel384/check-serializer.py').read_text());prefix=next(ast.literal_eval(x.value) for x in tree.body if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='prefix' for t in x.targets))
prefix+='''
#include <stdlib.h>
typedef uint64_t u64;
#define U32_MAX UINT32_MAX
#define IPE_IO_CONFIG_BYTES 1216
#define min(a,b) ((a)<(b)?(a):(b))
static u16 get_unaligned_le16(const void *p){u16 x;memcpy(&x,p,2);return x;}
struct camss_a5_pd10_layout {u32 width,height,stride,slice_height,bytes;};
struct camss_a5_ipe_ltm_geometry {bool data_collection,image_processing,mask_filter;};
'''
ipe=(k/'camss-icp-a5-ipe.c').read_text();boot=(k/'camss-icp-a5-boot.c').read_text()
names=['camss_a5_ipe_pd10_quarter','ipe_partitions','camss_a5_ipe_bypass_partitions','camss_a5_ipe_ltm_partitions','camss_a5_ipe_bypass_size','bypass_module_1d','camss_a5_ipe_ltm_size','ipe_encode_striping','camss_a5_ipe_encode_ltm_striping']
code=prefix+'\n'.join(function(ipe,n) for n in names)+'\n'+'\n'.join(function(boot,n) for n in ['nv12_layout_valid','encode_nv12_image','camss_a5_ipe_encode_io'])+'\n'+(HERE/'pd10-striping.c').read_text()+r'''
int main(void){
 u32 input[3],used;u8 output[32768],config[1216];struct camss_a5_pd10_layout coarse;
 struct camss_a5_ipe_ltm_geometry ltm={true,true,true};
 while(fread(input,sizeof(input),1,stdin)==1){
  struct camss_a5_ipe_io io={.input={input[0],input[1],input[0],input[1],false},.output={input[0],input[1],input[0],input[1],false},.output_port=8};
  assert(!camss_a5_ipe_pd10_quarter(&io.input,&coarse));assert(!camss_a5_ipe_encode_io(config,sizeof(config),&io,&coarse));
  memset(output,0xa5,sizeof(output));assert(!camss_a5_ipe_encode_ltm_pd10_striping(output,sizeof(output),&io,input[2],&ltm,&used));
  for(u32 i=used;i<sizeof(output);i++)assert(output[i]==0xa5);
  assert(fwrite(&used,4,1,stdout)==1 && fwrite(&coarse,sizeof(coarse),1,stdout)==1 && fwrite(config,sizeof(config),1,stdout)==1 && fwrite(output,used,1,stdout)==1);
 }return 0;
}
'''
reuse=(P/'geometry-model.c').is_file() and (P/'geometry-model.c').read_text()==code
(P/'geometry-model.c').write_text(code);edges='--edges' in sys.argv;cases=([(1296,720,1),(1304,720,1),(1600,900,1)] if edges else [(640,480,1),(1280,720,1),(1920,1080,1)]);inputs=b''.join(struct.pack('<3I',*row) for row in cases);outputs=[]
for arch,cc,flags,launch in [('host','gcc',['-fsanitize=address,undefined','-no-pie'],[]),('aarch64','aarch64-linux-gnu-gcc',['-static'],['qemu-aarch64'])]:
 binary=P/('geometry-'+arch)
 if not reuse or not binary.is_file():
  q=subprocess.run([cc,'-std=gnu11','-O2','-Wall','-Wextra','-Werror',*flags,str(P/'geometry-model.c'),'-o',str(binary)],capture_output=True);(P/(arch+'-geometry-build.log')).write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
 q=subprocess.run([*launch,str(binary)],input=inputs,capture_output=True);(P/(arch+'-geometry-run.log')).write_bytes(q.stderr);assert q.returncode==0,q.stderr.decode();outputs.append(q.stdout)
assert outputs[0]==outputs[1]
fw=module('fw425',HERE.parent/'kernel425/firmware-model.py');rows=[];at=0
for width,height,cores in cases:
 used=struct.unpack_from('<I',outputs[0],at)[0];layout=struct.unpack_from('<5I',outputs[0],at+4);config=outputs[0][at+24:at+1240];stripe=outputs[0][at+1240:at+1240+used];at+=1240+used
 slug=f'{width}x{height}';gold=(P/f'{slug}-stripe-private.bin').read_bytes();iq=(P/f'{slug}-iq-private.bin').read_bytes();assert config==(P/f'{slug}-config-private.bin').read_bytes()
 model,job,commands,meta=fw.prepare(config,stripe,iq,width,height,layout[4]);_,goldjob,goldcommands,_=fw.prepare(config,gold,iq,width,height,layout[4])
 differing=[i for i,(a,b) in enumerate(zip(commands,goldcommands)) if a!=b]
 for name,data in [('actual-c-stripe',stripe),('actual-c-commands',commands),('gold-commands',goldcommands)]:(P/f'{slug}-{name}-private.bin').write_bytes(data)
 row=dict(width=width,height=height,cores=cores,pd10_bytes=layout[4],striping_bytes=used,native_striping_bytes=len(gold),scratch_bytes=meta['required_scratch_bytes'],different_program_bytes=len(differing),job_equal=job==goldjob,passed=not differing and job==goldjob and used==len(gold));rows.append(row)
 (P/f'{slug}-program-diff-private.json').write_text(json.dumps(differing));print(json.dumps(row),flush=True)
assert at==len(outputs[0]);report=dict(stage=441,rows=rows,host_asan_ubsan=True,aarch64_static_qemu=True,actual_existing_io_encoder=True,authored_geometry_prototype=True,complete_native_firmware_frame_prepare=True,final_native_scheduler_and_bl_still_to_verify=True,hardware_executed=False,passed=all(row['passed'] for row in rows))
(HERE/('geometry-edges-validation.json' if edges else 'geometry-prototype-validation.json')).write_text(json.dumps(report,indent=2)+'\n')
assert report['passed']
