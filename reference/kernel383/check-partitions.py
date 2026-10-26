from pathlib import Path
import importlib.util,json,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;work=P/'partitions-model';work.mkdir(exist_ok=True)
spec=importlib.util.spec_from_file_location('sl383',HERE/'trace-striping.py');sl=importlib.util.module_from_spec(spec);spec.loader.exec_module(sl)
production=(P/'camss-icp-a5-ipe.c.proposed').read_text();actual='int camss_a5_ipe_bypass_partitions('+production.split('int camss_a5_ipe_bypass_partitions(',1)[1]
prefix='''#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
typedef uint16_t u16;typedef uint32_t u32;
#define EXPORT_SYMBOL_GPL(x)
struct camss_a5_ipe_partition{u16 fetch_first,fetch_last,output_first,output_last;};
'''
main='''
int main(void){struct camss_a5_ipe_partition out[32],saved[32];u32 count=0xdeadbeef;
 memset(out,0xa5,sizeof(out));memcpy(saved,out,sizeof(out));
 assert(camss_a5_ipe_bypass_partitions(640,1,NULL,32,&count)==-EINVAL);
 assert(camss_a5_ipe_bypass_partitions(640,1,out,32,NULL)==-EINVAL);
 u32 invalid[][2]={{0,1},{126,1},{129,1},{8194,1},{0xffffffff,1},{640,0},{640,3}};
 for(unsigned i=0;i<sizeof(invalid)/sizeof(invalid[0]);i++)assert(camss_a5_ipe_bypass_partitions(invalid[i][0],invalid[i][1],out,32,&count)==-EINVAL && count==0xdeadbeef && !memcmp(out,saved,sizeof(out)));
 assert(camss_a5_ipe_bypass_partitions(640,1,out,1,&count)==-ENOSPC && count==0xdeadbeef && !memcmp(out,saved,sizeof(out)));
 u32 input[2];while(fread(input,sizeof(input),1,stdin)==1){memset(out,0xa5,sizeof(out));assert(!camss_a5_ipe_bypass_partitions(input[0],input[1],out,32,&count));
  assert(count && count<=32 && count%input[1]==0);u32 covered=0;
  for(u32 i=0;i<count;i++){assert(out[i].output_first<=out[i].output_last && !(out[i].output_first&1) && (out[i].output_last&1));assert(out[i].fetch_first<=out[i].output_first && out[i].fetch_last>=out[i].output_last && out[i].fetch_last<input[0]);if(i)assert(out[i].output_last+1==out[i-1].output_first);covered+=out[i].output_last-out[i].output_first+1;}
  assert(covered==input[0] && out[0].output_last==input[0]-1 && !out[count-1].output_first);
  for(u32 i=count;i<32;i++)assert(!memcmp(out+i,saved+i,sizeof(out[i])));
  assert(fwrite(&count,4,1,stdout)==1 && fwrite(out,sizeof(out[0]),count,stdout)==count);
 }return 0;}
'''
(work/'probe.c').write_text(prefix+actual+main)
q=subprocess.run(['cc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(work/'probe.c'),'-o',str(work/'probe')],capture_output=True);assert not q.returncode,q.stderr.decode()
cases=json.loads((P/'partition-probe-private.json').read_text());assert all(r['success'] for r in cases)
extra=[(2048,1536,1,False),(2048,1536,2,False),(4096,3072,1,False),(4096,3072,2,False),(8192,480,1,False),(8192,480,2,False),(728,416,1,False),(726,416,2,False),(326,128,1,False),(330,3456,1,False),(640,480,1,True),(1920,1080,2,True),(4608,3456,1,True),(8192,480,2,True)]
for width,height,cores,swap in extra:
 blob,_,_,info=sl.execute(width,height,9,cores,uv_swap=swap);parts=[]
 for i in range(info['stripes'][0]):
  off=2268+i*624;parts.append(dict(fetch=list(struct.unpack_from('<HH',blob,off+4)),output=list(struct.unpack_from('<HH',blob,off+24))))
 cases.append(dict(width=width,cores=cores,height=height,uv_swap=swap,parts=parts,success=True))
q=subprocess.run([str(work/'probe')],input=b''.join(struct.pack('<II',r['width'],r['cores']) for r in cases),capture_output=True);assert not q.returncode,q.stderr.decode()
pos=0
for row in cases:
 count=struct.unpack_from('<I',q.stdout,pos)[0];pos+=4;assert count==len(row['parts'])
 for expected in row['parts']:
  actual_values=struct.unpack_from('<4H',q.stdout,pos);pos+=8;assert actual_values==tuple(expected['fetch']+expected['output']),(row,actual_values,expected)
assert pos==len(q.stdout)
report=dict(stage=383,actual_production_partition_function_body=True,compared_to_complete_original_hal_striping_algorithm=True,
 cases=len(cases),width_range=[128,8192],threshold_neighbors_328_330_and_656_658_checked=True,cores=[1,2],
 chroma_aligned_inclusive_descending_ranges_and_four_pixel_fetch_halo=True,range_coverage_no_holes_no_overlaps=True,nv12_and_nv21_layouts_compared=True,
 invalid_or_short_output_does_not_modify_buffers_or_count=True,asan_ubsan=True,full_firmware_blob_not_generated=True,
 hardware_execution=False,passed=True)
(HERE/'partitions-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
