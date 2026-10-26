"""Exercise actual third-buffer release and retained-ownership predicates."""
from pathlib import Path
import importlib.util,json,re,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
d=m.mounted_build().parent/'source354/drivers/media/platform/qcom/camss';boot=(d/'camss-icp-a5-boot.c').read_text();adapter=(d/'camss-icp-a5-m2m.c').read_text()
def fun(text,name):
 q=re.search(r'(?:static )?(?:int|bool)\s+'+name+r'\([^;]+?\n\{.*?^\}\n',text,re.S|re.M);assert q,name;return q[0]
prefix=r'''
#include <assert.h>
#include <stdbool.h>
#include <errno.h>
#include <stdio.h>
struct memory {void *cpu;unsigned mapped;};
struct camss_a5_dma_image {void *buffer;unsigned id;};
struct camss_a5 {
 struct memory firmware,shared,heap,config,request,image_input,image_output;
 struct camss_a5_dma_image dma_input,dma_output,dma_coarse;
 bool session_uncertain,ipe_dma_pending,config_fw_mapped,request_fw_mapped;
 void *request_owner;unsigned watchdogs,protocol_errors;
};
static unsigned calls,failed,order[3];
static int camss_a5_dma_image_release(struct camss_a5_dma_image *image){
 order[calls++]=image->id;if(image->id==failed)return -EIO;image->buffer=0;return 0;
}
'''
tests=r'''
int main(void){
 struct camss_a5 a={};
 assert(transfer_released(&a) && !camss_a5_backing_owned(&a) && !image_transfer_owned(&a));
 a.dma_coarse.buffer=&a;
 assert(!transfer_released(&a) && camss_a5_backing_owned(&a) && image_transfer_owned(&a));
 for(unsigned fail=0;fail<=3;fail++){
  a=(struct camss_a5){.dma_coarse={&a,1},.dma_output={&a,2},.dma_input={&a,3}};
  calls=0;failed=fail;int ret=free_imported_images(&a);
  assert(ret==(fail?-EIO:0) && calls==(fail?fail:3));
  for(unsigned i=0;i<calls;i++)assert(order[i]==i+1);
  if(fail){
   assert(camss_a5_backing_owned(&a) && !transfer_released(&a));
   calls=0;failed=0;assert(!free_imported_images(&a));
  }
  assert(transfer_released(&a) && !camss_a5_backing_owned(&a));
 }
 for(unsigned mapped=0;mapped<2;mapped++){
  a=(struct camss_a5){.dma_coarse={&a,1},.dma_output={&a,2},.dma_input={&a,3},
   .ipe_dma_pending=!mapped,.request_fw_mapped=mapped};calls=0;failed=0;
  assert(free_imported_images(&a)==-EBUSY && !calls && a.dma_coarse.buffer && a.dma_input.buffer && a.dma_output.buffer);
 }
 puts("THIRD_BUFFER_OWNER passed=1");return 0;
}
'''
code=prefix+fun(boot,'free_imported_images')+fun(boot,'camss_a5_backing_owned')+fun(boot,'transfer_released')+fun(adapter,'image_transfer_owned')+tests
(P/'owner-model.c').write_text(code)
for arch,cc,flags,launch in [('host','gcc',['-fsanitize=address,undefined','-no-pie'],[]),('aarch64','aarch64-linux-gnu-gcc',['-static'],['qemu-aarch64'])]:
 binary=P/('owner-'+arch);q=subprocess.run([cc,'-std=gnu11','-O2','-Wall','-Wextra','-Werror',*flags,str(P/'owner-model.c'),'-o',str(binary)],capture_output=True)
 assert not q.returncode,q.stderr.decode();q=subprocess.run([*launch,str(binary)],capture_output=True);assert not q.returncode,q.stderr.decode()
r=dict(stage=429,actual_retained_ownership_and_free_functions=True,host_asan_ubsan=True,aarch64_static_qemu=True,
 coarse_only_backing_detected_by_core_and_adapter=True,each_release_failure_retains_remaining_ownership=True,
 pending_or_firmware_mapped_transfer_releases_nothing=True,successful_retry_releases_third_and_full_buffers=True,passed=True)
(HERE/'owner-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
