"""Compare actual proposed C partition functions with original HAL outputs."""
from pathlib import Path
import json,re,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;production=(P/'camss-icp-a5-ipe.c.proposed').read_text();functions=[]
for name in ['ipe_partitions','camss_a5_ipe_bypass_partitions','camss_a5_ipe_ltm_partitions']:
 match=re.search(r'(?:static )?int '+name+r'\([^;]+?\n\{.*?^\}\n',production,re.S|re.M);assert match,name;functions.append(match[0])
prefix='''#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
typedef uint16_t u16;typedef uint32_t u32;
struct camss_a5_ipe_partition {u16 fetch_first,fetch_last,output_first,output_last;};
'''
main=r'''
int main(void){struct camss_a5_ipe_partition out[32],saved[32];u32 count=0xdeadbeef;u32 invalid[][2]={{0,1},{126,1},{129,1},{8194,1},{0xffffffff,1},{640,0},{640,3}};
for(unsigned mode=0;mode<2;mode++){
 int (*fn)(u32,u32,struct camss_a5_ipe_partition*,u32,u32*)=mode?camss_a5_ipe_ltm_partitions:camss_a5_ipe_bypass_partitions;memset(out,0xa5,sizeof out);memcpy(saved,out,sizeof out);
 assert(fn(640,1,NULL,32,&count)==-EINVAL && fn(640,1,out,32,NULL)==-EINVAL);
 for(unsigned i=0;i<sizeof invalid/sizeof invalid[0];i++)assert(fn(invalid[i][0],invalid[i][1],out,32,&count)==-EINVAL && count==0xdeadbeef && !memcmp(out,saved,sizeof out));
 assert(fn(640,1,out,1,&count)==-ENOSPC && count==0xdeadbeef && !memcmp(out,saved,sizeof out));
}
u32 input[3];while(fread(input,sizeof input,1,stdin)==1){memset(out,0xa5,sizeof out);int ret=input[2]?camss_a5_ipe_ltm_partitions(input[0],input[1],out,32,&count):camss_a5_ipe_bypass_partitions(input[0],input[1],out,32,&count);assert(!ret && count<=32);for(unsigned i=count;i<32;i++)assert(!memcmp(out+i,saved+i,sizeof out[i]));assert(fwrite(&count,4,1,stdout)==1 && fwrite(out,sizeof out[0],count,stdout)==count);}
return 0;}
'''
(P/'native-partition-model.c').write_text(prefix+'\n'.join(functions)+main)
cases=[]
for name in ['striping-probe.json','striping-boundary-probe.json','striping-extreme-probe.json']:
 for row in json.loads((HERE/name).read_text())['cases']:
  w,h,p,c,dc,ip=[row[k] for k in ['width','height','port','cores','data_collection','image_processing']];blob=(P/f'{w}x{h}-p{p}-c{c}-dc{dc}-ip{ip}-original-stripe-private.bin').read_bytes();count=struct.unpack_from('<H',blob,428)[0]
  gold=struct.pack('<I',count)+b''.join(blob[2268+624*i+4:2268+624*i+8]+blob[2268+624*i+(24 if p==9 else 20):2268+624*i+(28 if p==9 else 24)] for i in range(count));cases.append((w,c,ip,gold))
for row in json.loads((P.parent/'kernel383/partition-probe-private.json').read_text()):
 assert row['success'];cases.append((row['width'],row['cores'],0,struct.pack('<I',len(row['parts']))+b''.join(struct.pack('<4H',*(p['fetch']+p['output'])) for p in row['parts'])))
rows=[];inputs=b''.join(struct.pack('<3I',w,c,ip) for w,c,ip,gold in cases);gold=b''.join(row[3] for row in cases)
for arch,compiler,flags,launch in [('host','gcc',['-fsanitize=address,undefined','-no-pie'],[]),('aarch64','aarch64-linux-gnu-gcc',['-static'],['qemu-aarch64'])]:
 binary=P/('native-partitions-'+arch);q=subprocess.run([compiler,'-std=gnu11','-O2','-Wall','-Wextra','-Werror',*flags,str(P/'native-partition-model.c'),'-o',str(binary)],capture_output=True);assert not q.returncode,q.stderr.decode();q=subprocess.run([*launch,str(binary)],input=inputs,capture_output=True);assert not q.returncode,q.stderr.decode();assert q.stdout==gold
 rows.append(dict(architecture=arch,cases=len(cases),compared_bytes=len(gold),different_bytes=0,passed=True))
report=dict(stage=403,actual_proposed_production_c_functions=True,original_hal_ltm_and_retained_bypass_oracles=True,ltm_cases=sum(bool(row[2]) for row in cases),bypass_cases=sum(not row[2] for row in cases),host_asan_ubsan=True,aarch64_qemu=True,invalid_short_capacity_and_tail_preserve_outputs=True,architectures=rows,only_partition_primitive_not_full_ltm_serializer=True,phone_accessed=False,passed=True)
(HERE/'native-partitions-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
