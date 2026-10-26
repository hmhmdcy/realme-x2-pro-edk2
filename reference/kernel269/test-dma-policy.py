"""Exercise the actual DMA guard and domain check without modeling the IOMMU allocator."""
from pathlib import Path
import hashlib,json,subprocess
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel269');out=P/'dma-tests-r2';out.mkdir(mode=0o700)
def function(s,name):
 start=s.index('static int '+name+'(');a=s.index('{',start);depth=1;b=a+1
 while depth:
  if s[b]=='{':depth+=1
  elif s[b]=='}':depth-=1
  b+=1
 return s[start:b]+'\n'
new=function((R/'source/camss-video.c').read_text(),'video_check_dma_mapping')
domain=function((R/'source/camss-cpas.c').read_text(),'camss_cpas_check_dma_domain')
old=function((P/'dma-policy-before/camss-video.c').read_text(),'video_check_dma_mapping')
prefix=r'''
#include <assert.h>
#include <errno.h>
#include <inttypes.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <stddef.h>
typedef uint64_t dma_addr_t;
typedef uint64_t u64;
#define CAMSS_8150 8150
#define IOMMU_DOMAIN_DMA 3
#define IOMMU_DOMAIN_DMA_FQ 4
struct iommu_domain { int type; };
struct device { u64 mask; struct iommu_domain *domain; };
struct resource { int version; };
struct camss { struct resource *res; struct device *dev; };
struct camss_video { struct camss *camss; };
struct scatterlist { dma_addr_t address; size_t length; };
struct sg_table { struct scatterlist *sgl; unsigned int nents; };
#define sg_dma_address(sg) ((sg)->address)
#define sg_dma_len(sg) ((sg)->length)
#define for_each_sgtable_dma_sg(t,s,i) for ((i)=0;(i)<(t)->nents && ((s)=&(t)->sgl[i],1);(i)++)
static inline u64 dma_get_mask(struct device *dev) { return dev->mask; }
static struct iommu_domain *iommu_get_domain_for_dev(struct device *dev) { return dev->domain; }
'''
main=r'''
static unsigned int cases;
static uint32_t random_state=0x12345678;
static uint32_t next_random(void) { random_state^=random_state<<13;random_state^=random_state>>17;random_state^=random_state<<5;return random_state; }
static void check(struct camss_video *v,struct sg_table *t,size_t n,int expected) {
 int ret=video_check_dma_mapping(v,t,n);assert(ret==expected);cases++;
}
int main(void) {
 struct device d={.mask=UINT32_MAX};struct resource r={CAMSS_8150};struct camss c={&r,&d};struct camss_video v={&c};
 struct scatterlist sg[4]={{0,4096}};struct sg_table t={sg,1};
 check(&v,NULL,1,-EINVAL);check(&v,&t,0,-EINVAL);t.nents=0;check(&v,&t,1,-EINVAL);t.nents=1;
 t.sgl=NULL;check(&v,&t,1,-EINVAL);t.sgl=sg;
 /* Device-mask boundaries, including ranges unrelated to RMX1931's firmware. */
 sg[0]=(struct scatterlist){0,1};check(&v,&t,1,0);
 sg[0]=(struct scatterlist){UINT32_MAX,1};check(&v,&t,1,0);check(&v,&t,2,-ERANGE);
 sg[0]=(struct scatterlist){(u64)UINT32_MAX+1,1};check(&v,&t,1,-ERANGE);
 d.mask=UINT16_MAX;sg[0]=(struct scatterlist){0x1000,4096};check(&v,&t,4096,0);
 sg[0]=(struct scatterlist){UINT16_MAX-15,16};check(&v,&t,16,0);check(&v,&t,17,-ERANGE);
 d.mask=UINT64_MAX;sg[0]=(struct scatterlist){UINT64_MAX-15,16};check(&v,&t,16,0);check(&v,&t,17,-ERANGE);
 sg[0]=(struct scatterlist){0x8000,0};check(&v,&t,1,-EINVAL);
 sg[0]=(struct scatterlist){0x8000,64};check(&v,&t,65,-EINVAL);
 t.nents=2;sg[1]=(struct scatterlist){0x8041,64};check(&v,&t,128,-EINVAL);
 sg[1].address=0x803f;check(&v,&t,128,-EINVAL);
 sg[1].address=0x8040;check(&v,&t,128,0);
 r.version=845;check(&v,NULL,0,0);r.version=CAMSS_8150;
 d.mask=UINT32_MAX;
 for(unsigned int i=0;i<10000;i++) {
  u64 address=(u64)(next_random()&0x7ffff000);size_t total=0;t.nents=4;
  for(unsigned int j=0;j<4;j++) {size_t n=1+(next_random()%8192);sg[j]=(struct scatterlist){address+total,n};total+=n;}
  check(&v,&t,total,0);check(&v,&t,total+1,-EINVAL);
  unsigned int j=1+(next_random()%3);sg[j].address++;check(&v,&t,total,-EINVAL);sg[j].address--;
  sg[j].length=0;check(&v,&t,total,-EINVAL);
 }
 assert(camss_cpas_check_dma_domain(&d)==-ENODEV);cases++;
 struct iommu_domain domain={IOMMU_DOMAIN_DMA};d.domain=&domain;
 assert(camss_cpas_check_dma_domain(&d)==0);cases++;
 domain.type=IOMMU_DOMAIN_DMA_FQ;assert(camss_cpas_check_dma_domain(&d)==0);cases++;
 domain.type=0;assert(camss_cpas_check_dma_domain(&d)==-ENODEV);cases++;
 domain.type=99;assert(camss_cpas_check_dma_domain(&d)==-ENODEV);cases++;
 printf("{\"cases\":%u,\"random_scatterlists\":10000,\"domain_cases\":5}\n",cases);
 return 0;
}
'''
results={}
for name,guard in [('actual',new),('old-negative',old)]:
 p=out/(name+'.c');p.write_text(prefix+guard+domain+main)
 q=subprocess.run(['gcc','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(p),'-o',str(out/name)],capture_output=True)
 (out/(name+'-compile-private.log')).write_bytes(q.stdout+q.stderr);assert q.returncode==0
 q=subprocess.run([str(out/name)],capture_output=True,timeout=20)
 (out/(name+'-private.log')).write_bytes(q.stdout+q.stderr)
 if name=='actual':assert q.returncode==0;results[name]=json.loads(q.stdout)
 else:assert q.returncode!=0 and b'Assertion' in q.stderr;results[name]=dict(old_board_constants_rejected=True)
report=dict(stage=269,actual_functions_extracted=True,asan_ubsan=True,results=results,
 guard_sha256=hashlib.sha256(new.encode()).hexdigest(),domain_sha256=hashlib.sha256(domain.encode()).hexdigest(),
 iommu_allocator_not_modeled=True,dt_and_on_device_reservation_verification_still_required=True)
(R/'dma-test-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
