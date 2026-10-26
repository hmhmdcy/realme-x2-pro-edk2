"""Execute the candidate production C body with sanitizers and original FW."""
from pathlib import Path
import importlib.util,json,struct,subprocess,sys
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent/'kernel383'))
from engine_model import prepare
P=Path('/mnt/e/edk2-samurai-out/kernel384');work=P/'serializer-model';work.mkdir(exist_ok=True)
prefix='''#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
typedef uint8_t u8;typedef uint16_t u16;typedef uint32_t u32;typedef int32_t s32;
#define EXPORT_SYMBOL_GPL(x)
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define max(a,b) ((a)>(b)?(a):(b))
struct camss_a5_nv12_layout {u32 width,height,stride,slice_height;bool uv_swap;};
struct camss_a5_ipe_io {struct camss_a5_nv12_layout input,output;u32 output_port;};
struct camss_a5_ipe_partition {u16 fetch_first,fetch_last,output_first,output_last;};
static void put_unaligned_le16(u16 v,void *p){u8 *d=p;d[0]=v;d[1]=v>>8;}
static void put_unaligned_le32(u32 v,void *p){u8 *d=p;for(unsigned i=0;i<4;i++)d[i]=v>>(8*i);}
'''
main='''
int main(void){u8 out[32768],saved[32768];u32 used=0xdeadbeef,bytes=0xdeadbeef;
struct camss_a5_ipe_io io={.input={640,480,640,480,false},.output={640,480,640,480,false},.output_port=8},bad;
memset(out,0xa5,sizeof(out));memcpy(saved,out,sizeof(out));
assert(camss_a5_ipe_bypass_size(NULL,1,&bytes)==-EINVAL && bytes==0xdeadbeef);
assert(camss_a5_ipe_bypass_size(&io,1,NULL)==-EINVAL);
assert(camss_a5_ipe_encode_bypass_striping(NULL,sizeof(out),&io,1,&used)==-EINVAL);
assert(camss_a5_ipe_encode_bypass_striping(out,sizeof(out),&io,1,NULL)==-EINVAL);
for(unsigned i=0;i<18;i++){
bad=io;u32 cores=1,capacity=sizeof(out);
switch(i){case 0:bad.input.width=126;break;case 1:bad.input.width=8194;break;case 2:bad.input.height=126;break;
case 3:bad.input.height=8194;break;case 4:bad.input.width=641;break;case 5:bad.input.height=481;break;
case 6:bad.output.width=642;break;case 7:bad.output.height=482;break;case 8:bad.output.uv_swap=true;break;
case 9:bad.output_port=7;break;case 10:cores=0;break;case 11:cores=3;break;case 12:bad.input.stride=639;break;
case 13:bad.output.stride=638;break;case 14:bad.input.slice_height=478;break;case 15:bad.output.slice_height=479;break;
case 16:capacity=3515;break;case 17:bad.input.width=0xffffffff;break;}
int ret=camss_a5_ipe_encode_bypass_striping(out,capacity,&bad,cores,&used);
assert(ret==(i==16?-ENOSPC:-EINVAL) && used==0xdeadbeef && !memcmp(out,saved,sizeof(out)));
}
u32 in[5];while(fread(in,sizeof(in),1,stdin)==1){
io=(struct camss_a5_ipe_io){.input={in[0],in[1],in[0],in[1],in[4]},.output={in[0],in[1],in[0],in[1],in[4]},.output_port=in[2]};
assert(!camss_a5_ipe_bypass_size(&io,in[3],&bytes));memset(out,0xa5,sizeof(out));
assert(!camss_a5_ipe_encode_bypass_striping(out,bytes,&io,in[3],&used) && used==bytes);
assert(!memcmp(out+bytes,saved+bytes,sizeof(out)-bytes));
assert(fwrite(&used,4,1,stdout)==1 && fwrite(out,1,used,stdout)==used);
}return 0;}
'''
production=(HERE.parent/'kernel383/bypass-partitions.c').read_text()+'\n'+(HERE/'bypass-striping.c').read_text()
(work/'probe.c').write_text(prefix+production+main)
q=subprocess.run(['cc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(work/'probe.c'),'-o',str(work/'probe')],capture_output=True);assert not q.returncode,q.stderr.decode()
cases=[]
for w,h in [(640,480),(1920,1080),(4608,3456)]:
 for p in [8,9]:
  for c in [1,2]:cases.append((w,h,p,c,False,P.parent/'kernel383'))
for r in json.loads((P/'extra-prototype-result-private.json').read_text()):cases.append((r['width'],r['height'],r['port'],r['cores'],False,P))
q=subprocess.run([str(work/'probe')],input=b''.join(struct.pack('<5I',*r[:5]) for r in cases),capture_output=True);assert not q.returncode,q.stderr.decode()
rows=[];pos=0
for w,h,p,c,swap,gold_dir in cases:
 size=struct.unpack_from('<I',q.stdout,pos)[0];pos+=4;native=q.stdout[pos:pos+size];pos+=size
 slug=f'{w}x{h}-p{p}-c{c}';gold=(gold_dir/(slug+'-canonical-stripe-private.bin')).read_bytes();assert size==len(gold)
 _,gj,gc,_=prepare(gold,w,h,p,c);_,nj,nc,_=prepare(native,w,h,p,c)
 expected=(gold_dir/(slug+'-original-cdm-private.bin')).read_bytes();assert gc==expected
 diff=sum(x!=y for x,y in zip(gc,nc));assert not diff and gj==nj,(slug,diff)
 (P/(slug+'-native-stripe-private.bin')).write_bytes(native)
 rows.append(dict(width=w,height=h,output_port=p,max_cores=c,bytes=size,whole_cdm_bytes_compared=len(gc),different_cdm_bytes=diff,job_equal=gj==nj,passed=True))
 print(json.dumps(rows[-1]),flush=True)
assert pos==len(q.stdout)
report=dict(stage=384,actual_candidate_production_c_body=True,asan_ubsan=True,invalid_inputs_and_short_capacity_preserve_output_and_used=True,
 full_original_firmware_preparation_not_geometry_stubs=True,whole_cdm_and_job_matches_original_hal=True,cases=rows,
 scope='one full-frame 1:1 pass; IQ disabled; linear 8-bit YUV',hardware_execution=False,passed=True)
(HERE/'serializer-validation.json').write_text(json.dumps(report,indent=2)+'\n');print('All candidate C serializer cases passed.')
