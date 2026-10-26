"""Reproduce the leak and check the real reservation parser after the fix."""
from pathlib import Path
import hashlib, json, subprocess

HERE=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel357')
prefix=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef uint32_t __be32;typedef uint32_t u32;typedef uint64_t phys_addr_t;
#define CONFIG_OF_ADDRESS 1
#define IS_ENABLED(x) (x)
#define IOMMU_READ 1
#define IOMMU_WRITE 2
#define IOMMU_CACHE 4
#define GFP_KERNEL 0
#define EXPORT_SYMBOL(n)
#define dev_err(...) ((void)0)
#define dev_warn(...) ((void)0)
struct device_node {int kind;};struct device {struct device_node *of_node;};
struct resource {uint64_t start,end;};struct list_head {int count;};
enum iommu_resv_type {IOMMU_RESV_RESERVED,IOMMU_RESV_DIRECT};
struct iommu_resv_region {struct list_head list;};
struct of_phandle_iterator {struct device_node *node;unsigned i;};
static struct device_node consumer={1},foreign={2},memory={3};
static int refs,put_count,finds,allocations,coherent,physical,addr_fail,no_maps,fail_alloc;
static unsigned entries;static __be32 maps_data[5];
#define of_for_each_phandle(it,err,consumer_node,key,cells,n) \
 for((it)->i=0,(err)=0;(err)==0&&(it)->i<entries&&((it)->node=&memory);(it)->i++)
static bool of_property_present(struct device_node *n,const char *k){assert(n==&memory&&!strcmp(k,"reg"));return physical;}
static int of_address_to_resource(struct device_node *n,int i,struct resource *r){assert(n==&memory&&!i);r->start=0x9ab00000;r->end=0x9affffff;return addr_fail?-1:0;}
static const __be32 *of_get_property(struct device_node *n,const char *k,int *size){assert(n==&memory&&!strcmp(k,"iommu-addresses"));*size=sizeof(maps_data);return no_maps?NULL:maps_data;}
static u32 be32_to_cpup(const __be32 *p){return *p;}
static struct device_node *of_find_node_by_phandle(u32 id){finds++;if(id!=1&&id!=2)return NULL;refs++;return id==1?&consumer:&foreign;}
static void of_node_put(struct device_node *n){assert(n==&consumer||n==&foreign);assert(refs>0);refs--;put_count++;}
static void __attribute__((unused)) clean_device_node(struct device_node **n){if(*n)of_node_put(*n);}
#define __free(name) __attribute__((cleanup(clean_##name)))
static bool of_dma_is_coherent(struct device_node *n){assert(n==&consumer);return coherent;}
static const __be32 *of_translate_dma_region(struct device_node *n,const __be32 *p,phys_addr_t *iova,size_t *len){assert(n==&consumer&&p==maps_data+1);*iova=((uint64_t)p[0]<<32)|p[1];*len=((uint64_t)p[2]<<32)|p[3];return p+4;}
static enum iommu_resv_type iommu_resv_region_get_type(struct device *d,struct resource *r,phys_addr_t i,size_t len){assert(d->of_node==&consumer&&i==0x7400000&&len==0x9600000);return r->start?IOMMU_RESV_DIRECT:IOMMU_RESV_RESERVED;}
static struct iommu_resv_region *iommu_alloc_resv_region(phys_addr_t i,size_t len,int prot,enum iommu_resv_type type,int flags){assert(i==0x7400000&&len==0x9600000&&prot==(IOMMU_READ|IOMMU_WRITE|(coherent?IOMMU_CACHE:0))&&type==(physical?IOMMU_RESV_DIRECT:IOMMU_RESV_RESERVED)&&!flags);allocations++;return fail_alloc?NULL:calloc(1,sizeof(struct iommu_resv_region));}
static void list_add_tail(struct list_head *n,struct list_head *list){list->count++;free(n);}
'''
main=r'''
int main(void){struct device d={&consumer};unsigned scenarios=0;int expected_leaked=0;
 for(unsigned k=0;k<9;k++){
  refs=put_count=finds=allocations=coherent=physical=addr_fail=no_maps=fail_alloc=0;entries=1;
  maps_data[0]=1;maps_data[1]=0;maps_data[2]=0x7400000;maps_data[3]=0;maps_data[4]=0x9600000;
  unsigned repeats=1;int expected_alloc=1;
  switch(k){
   case 1:coherent=1;break;
   case 2:entries=4;expected_alloc=4;break;
   case 3:maps_data[4]=0;expected_alloc=0;break;
   case 4:fail_alloc=1;break;
   case 5:no_maps=1;expected_alloc=0;break;
   case 6:physical=addr_fail=1;expected_alloc=0;break;
   case 7:physical=1;break;
   case 8:repeats=100;entries=4;expected_alloc=400;break;
  }
  struct list_head list={0};for(unsigned i=0;i<repeats;i++)of_iommu_get_resv_regions(&d,&list);
  assert(allocations==expected_alloc&&list.count==(fail_alloc?0:expected_alloc));
#ifdef EXPECT_LEAK
  assert(refs==(int)(no_maps||addr_fail?0:entries*repeats)&&!put_count);expected_leaked+=refs;
#else
  assert(!refs&&put_count==(int)(no_maps||addr_fail?0:entries*repeats));
#endif
  scenarios++;
 }
 printf("NODE_LIFETIME_%s scenarios=%u leaked_references=%d\n",
#ifdef EXPECT_LEAK
 "REPRODUCED",
#else
 "PASS",
#endif
 scenarios,expected_leaked);return 0;}
'''
rows=[]
for variant,path in [('before',P/'of_iommu-before-private.c'),('after',HERE/'of_iommu-after.c')]:
    source=path.read_text();body=source[source.index('void of_iommu_get_resv_regions'):]
    src=P/('node-lifetime-'+variant+'-private.c');exe=P/('node-lifetime-'+variant+'-private')
    src.write_text(prefix+body+main)
    args=['cc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-unused-parameter']
    if variant=='before':args+=['-DEXPECT_LEAK']
    q=subprocess.run(args+[str(src),'-o',str(exe)],capture_output=True)
    (P/('node-lifetime-'+variant+'-build.log')).write_bytes(q.stdout+q.stderr);q.check_returncode()
    q=subprocess.run([str(exe)],capture_output=True)
    (P/('node-lifetime-'+variant+'-run.log')).write_bytes(q.stdout+q.stderr);q.check_returncode()
    rows.append(dict(variant=variant,body_sha256=hashlib.sha256(body.encode()).hexdigest(),output=q.stdout.decode().strip()))
    print(q.stdout.decode().strip())
(HERE/'node-lifetime-validation.json').write_text(json.dumps(dict(stage=357,variants=rows,
    actual_common_parser_body=True,normal_zero_length_allocation_error_and_repeated_queries_tested=True,
    stubs_not_kernel_runtime=True,installed=False,passed=True),indent=2)+'\n')
