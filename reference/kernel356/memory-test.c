/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef uint8_t u8;typedef uint32_t u32;typedef uint64_t u64;typedef u32 __le32;typedef u64 dma_addr_t;typedef u64 phys_addr_t;
struct firmware {size_t size;const u8 *data;};struct mutex {int unused;};
#define U32_MAX UINT32_MAX
#define PAGE_SIZE 4096U
#define GFP_KERNEL 0
#define IOMMU_READ 1
#define IOMMU_WRITE 2
#define IOMMU_CACHE 4
#define IOMMU_PRIV 8
#define EXPORT_SYMBOL_GPL(n)
#define IS_ALIGNED(n,a) (!((n)&((a)-1)))
struct list_head {struct list_head *next,*prev;};
#define LIST_HEAD(n) struct list_head n={&n,&n}
#define entry(p,t,m) ((t*)((u8*)(p)-offsetof(t,m)))
#define list_for_each_entry(p,h,m) for(p=entry((h)->next,__typeof__(*p),m);&(p)->m!=(h);p=entry((p)->m.next,__typeof__(*p),m))
enum {IOMMU_RESV_RESERVED,IOMMU_RESV_DIRECT};
struct iommu_resv_region {u64 start,length;int type;struct list_head list;};
struct iommu_domain {bool dma;};struct device {struct iommu_domain *domain;bool coherent;};
#include "actual-header-private.h"
#define PAGES (CAMSS_A5_FW_WINDOW/PAGE_SIZE)
static struct iommu_domain domain={true},other_domain={true};static struct device device={&domain,false};
static phys_addr_t pages[PAGES],alias[PAGES];static dma_addr_t dma_address;static u32 alias_base,expected_bytes;
static struct iommu_resv_region region;
static int resv_gets,resv_puts,allocs,frees,maps,unmaps,fail_map,fail_unmap,hole,bad_physical;
static bool absent_region,fail_alloc,expected_privileged;static unsigned int scenarios;
static void reset(void)
{
	memset(alias,0,sizeof(alias));for(unsigned int i=0;i<PAGES;i++)pages[i]=0x180000000ULL+(u64)i*PAGE_SIZE*3;
	dma_address=0x20000000;alias_base=0;expected_bytes=CAMSS_A5_FW_WINDOW;region=(struct iommu_resv_region){.length=CAMSS_A5_FW_WINDOW,.type=IOMMU_RESV_RESERVED};
	resv_gets=resv_puts=allocs=frees=maps=unmaps=0;fail_map=fail_unmap=hole=bad_physical=-1;absent_region=fail_alloc=false;expected_privileged=true;device.domain=&domain;device.coherent=false;domain.dma=true;scenarios++;
}
static struct iommu_domain *iommu_get_domain_for_dev(struct device *dev){return dev->domain;}
static bool iommu_is_dma_domain(struct iommu_domain *d){return d->dma;}
static bool dev_is_dma_coherent(struct device *dev){return dev->coherent;}
static void iommu_get_resv_regions(struct device *dev,struct list_head *head)
{
	resv_gets++;if(!absent_region){struct iommu_resv_region *copy=malloc(sizeof(*copy));assert(copy);*copy=region;head->next=head->prev=&copy->list;copy->list.next=copy->list.prev=head;}
}
static void iommu_put_resv_regions(struct device *dev,struct list_head *head)
{
	resv_puts++;if(head->next!=head)free(entry(head->next,struct iommu_resv_region,list));head->next=head->prev=head;
}
static void *dma_alloc_coherent(struct device *dev,size_t bytes,dma_addr_t *dma,int flags)
{
	allocs++;if(fail_alloc)return NULL;assert(bytes==expected_bytes);*dma=dma_address;void *p=malloc(bytes);assert(p);memset(p,0xa5,bytes);return p;
}
static void dma_free_coherent(struct device *dev,size_t bytes,void *cpu,dma_addr_t dma)
{
	assert(dev==&device&&bytes==expected_bytes&&dma==dma_address);
	for(unsigned int i=0;i<PAGES;i++)assert(!alias[i]||alias[i]==0xdead0000);
	frees++;free(cpu);
}
static phys_addr_t iommu_iova_to_phys(struct iommu_domain *d,dma_addr_t iova)
{
	assert(d==&domain);
	if(iova>=alias_base&&iova-alias_base<expected_bytes){unsigned int i=(iova-alias_base)/PAGE_SIZE;return alias[i]+(alias[i]?iova%PAGE_SIZE:0);}
	assert(iova>=dma_address&&iova-dma_address<expected_bytes);unsigned int i=(iova-dma_address)/PAGE_SIZE;
	if((int)i==hole)return 0;
	return pages[i]+((int)i==bad_physical?1:0);
}
static int iommu_map(struct iommu_domain *d,unsigned long iova,phys_addr_t physical,size_t bytes,int prot,int flags)
{
	assert(d==&domain&&bytes==PAGE_SIZE&&iova>=alias_base&&iova-alias_base<expected_bytes&&iova%PAGE_SIZE==0);
	assert(prot==(IOMMU_READ|IOMMU_WRITE|(device.coherent?IOMMU_CACHE:0)|(expected_privileged?IOMMU_PRIV:0)));
	if(maps++==fail_map)return -ENOMEM;
	unsigned int i=(iova-alias_base)/PAGE_SIZE;assert(!alias[i]&&physical==pages[i]);alias[i]=physical;return 0;
}
static size_t iommu_unmap(struct iommu_domain *d,unsigned long iova,size_t bytes)
{
	assert(d==&domain&&bytes==PAGE_SIZE&&iova>=alias_base&&iova-alias_base<expected_bytes&&iova%PAGE_SIZE==0);
	if(unmaps++==fail_unmap)return 0;
	unsigned int i=(iova-alias_base)/PAGE_SIZE;assert(alias[i]==pages[i]);alias[i]=0;return bytes;
}

#define MEMREMAP_WC 1
static void *memremap(phys_addr_t physical,size_t bytes,unsigned flags) {
 assert(physical==0x9ab00000&&bytes==CAMSS_A5_FW_WINDOW&&flags==MEMREMAP_WC);allocs++;
 if(fail_alloc){return NULL;}
 void *cpu=malloc(bytes);assert(cpu);memset(cpu,0xa5,bytes);return cpu;
}
static void memunmap(void *cpu) {
 for(unsigned i=0;i<PAGES;i++)assert(!alias[i]||alias[i]==0xdead0000);
 frees++;free(cpu);
}

#include "actual-memory-private.c"
static void allocated(struct camss_a5_fw_memory *m)
{
	assert(!camss_a5_fw_memory_alloc(&device,m));assert(resv_gets==1&&resv_puts==1&&allocs==1&&!frees);
	for(unsigned int i=0;i<CAMSS_A5_FW_WINDOW;i++)assert(!((u8*)m->cpu)[i]);
}
static void released(struct camss_a5_fw_memory *m)
{
	assert(!camss_a5_fw_memory_unmap(m));assert(!camss_a5_fw_memory_free(m));assert(!m->cpu&&!m->mapped&&!m->bytes&&frees==1);
	assert(!camss_a5_fw_memory_unmap(m)&&!camss_a5_fw_memory_free(m)&&frees==1);
}
int main(void)
{
	struct camss_a5_fw_memory m;
	for(unsigned int coherent=0;coherent<2;coherent++){
		reset();m=(struct camss_a5_fw_memory){};device.coherent=coherent;allocated(&m);
		assert(!camss_a5_fw_memory_map(&m)&&m.mapped==CAMSS_A5_FW_WINDOW&&maps==PAGES);
		for(unsigned int i=0;i<PAGES;i++)assert(alias[i]==pages[i]);
		assert(camss_a5_fw_memory_map(&m)==-EBUSY&&camss_a5_fw_memory_free(&m)==-EBUSY&&!frees);released(&m);
	}
	for(unsigned int kind=0;kind<4;kind++){
		reset();m=(struct camss_a5_fw_memory){};
		if(kind==0){absent_region=true;}
		if(kind==1){region.type=IOMMU_RESV_DIRECT;}
		if(kind==2){region.length--;}
		if(kind==3){region.start=PAGE_SIZE;}
		assert(camss_a5_fw_memory_alloc(&device,&m)==-EINVAL&&!m.cpu&&!allocs&&resv_gets==resv_puts);
	}
	for(unsigned int kind=0;kind<2;kind++){
		reset();m=(struct camss_a5_fw_memory){};if(kind)domain.dma=false;else device.domain=NULL;
		assert(camss_a5_fw_memory_alloc(&device,&m)==-ENODEV&&!m.cpu&&!allocs&&!resv_gets);
	}
	reset();m=(struct camss_a5_fw_memory){};fail_alloc=true;assert(camss_a5_fw_memory_alloc(&device,&m)==-ENOMEM&&!m.cpu&&resv_gets==resv_puts);
	dma_addr_t invalid[]={0,CAMSS_A5_FW_WINDOW-PAGE_SIZE,0x100000000ULL,0xfffff000ULL};
	for(unsigned int i=0;i<4;i++){
		reset();m=(struct camss_a5_fw_memory){};dma_address=invalid[i];assert(camss_a5_fw_memory_alloc(&device,&m)==-ERANGE&&!m.cpu&&allocs==1&&frees==1);
	}
	unsigned int failures[]={0,1,PAGES/2,PAGES-1};
	for(unsigned int i=0;i<4;i++){
		reset();m=(struct camss_a5_fw_memory){};allocated(&m);fail_map=failures[i];assert(camss_a5_fw_memory_map(&m)==-ENOMEM&&!m.mapped&&!frees);released(&m);
	}
	for(unsigned int i=0;i<2;i++){
		reset();m=(struct camss_a5_fw_memory){};allocated(&m);if(i)bad_physical=PAGES/2;else hole=PAGES/2;
		assert(camss_a5_fw_memory_map(&m)==-EFAULT&&!m.mapped&&!frees);released(&m);
	}
	reset();m=(struct camss_a5_fw_memory){};allocated(&m);alias[PAGES-1]=0xdead0000;
	assert(camss_a5_fw_memory_map(&m)==-EBUSY&&!maps&&!m.mapped);released(&m);assert(alias[PAGES-1]==0xdead0000);
	reset();m=(struct camss_a5_fw_memory){};allocated(&m);fail_map=PAGES/2;fail_unmap=0;
	assert(camss_a5_fw_memory_map(&m)==-EIO&&m.mapped==PAGE_SIZE*(PAGES/2)&&!frees);
	assert(camss_a5_fw_memory_free(&m)==-EBUSY);fail_unmap=-1;released(&m);
	reset();m=(struct camss_a5_fw_memory){};allocated(&m);assert(!camss_a5_fw_memory_map(&m));fail_unmap=PAGES/2;
	assert(camss_a5_fw_memory_unmap(&m)==-EIO&&m.mapped==PAGE_SIZE*(PAGES/2)&&!frees);
	assert(camss_a5_fw_memory_free(&m)==-EBUSY);fail_unmap=-1;released(&m);
	reset();m=(struct camss_a5_fw_memory){};allocated(&m);device.domain=&other_domain;
	assert(camss_a5_fw_memory_map(&m)==-EXDEV&&camss_a5_fw_memory_free(&m)==-EXDEV&&!maps&&!frees);device.domain=&domain;released(&m);
	reset();m=(struct camss_a5_fw_memory){};allocated(&m);assert(!camss_a5_fw_memory_map(&m));device.domain=&other_domain;
	assert(camss_a5_fw_memory_unmap(&m)==-EXDEV&&m.mapped==CAMSS_A5_FW_WINDOW&&!unmaps);device.domain=&domain;released(&m);
	reset();m=(struct camss_a5_fw_memory){};dma_address=CAMSS_A5_FW_WINDOW;allocated(&m);assert(!camss_a5_fw_memory_map(&m));released(&m);
	assert(camss_a5_fw_memory_alloc(NULL,&m)==-EINVAL&&camss_a5_fw_memory_map(NULL)==-EINVAL&&camss_a5_fw_memory_unmap(NULL)==-EINVAL&&camss_a5_fw_memory_free(NULL)==-EINVAL);

 const u32 bases[]={0x07400000,0x10a00000,0xfff00000};
 const u32 sizes[]={0x1e000,0x100000,0x100000};
 for(unsigned int k=0;k<3;k++)for(unsigned int failure=0;failure<3;failure++) {
  reset();m=(struct camss_a5_fw_memory){};expected_privileged=false;alias_base=bases[k];expected_bytes=sizes[k];region.start=alias_base;region.length=expected_bytes;
  assert(!camss_a5_iova_memory_alloc(&device,&m,alias_base,expected_bytes));assert(m.iova==alias_base&&m.bytes==expected_bytes&&!m.privileged);
  if(failure==1)fail_map=expected_bytes/PAGE_SIZE/2;
  if(failure==2)alias[expected_bytes/PAGE_SIZE-1]=0xdead0000;
  int r=camss_a5_fw_memory_map(&m);
  assert(r==(failure==1?-ENOMEM:failure==2?-EBUSY:0));
  if(!failure)assert(m.mapped==expected_bytes);
  released(&m);
 }
 const u32 invalid_base[]={1,0,0xfffff000};const u32 invalid_size[]={PAGE_SIZE,1,PAGE_SIZE*2};
 for(unsigned int k=0;k<3;k++) {
  reset();m=(struct camss_a5_fw_memory){};
  assert(camss_a5_iova_memory_alloc(&device,&m,invalid_base[k],invalid_size[k])==-EINVAL&&!allocs);
 }
 reset();m=(struct camss_a5_fw_memory){};assert(camss_a5_iova_memory_alloc(&device,&m,0x7400000,PAGE_SIZE)==-EINVAL&&!allocs);
 reset();m=(struct camss_a5_fw_memory){};alias_base=0x7400000;expected_bytes=PAGE_SIZE*2;region.start=alias_base;region.length=expected_bytes;dma_address=alias_base-PAGE_SIZE;
 assert(camss_a5_iova_memory_alloc(&device,&m,alias_base,expected_bytes)==-ERANGE&&!m.cpu&&frees==1);
 for(unsigned kind=0;kind<4;kind++) {
  reset();m=(struct camss_a5_fw_memory){};for(unsigned i=0;i<PAGES;i++)pages[i]=0x9ab00000ULL+(u64)i*PAGE_SIZE;
  assert(!camss_a5_fw_carveout_alloc(&device,&m,0x9ab00000,CAMSS_A5_FW_WINDOW));assert(m.carveout&&m.privileged&&m.physical==0x9ab00000);
  if(kind==1){fail_map=PAGES/2;}
  if(kind==3){alias[PAGES-1]=0xdead0000;}
  int ret=camss_a5_fw_memory_map(&m);assert(ret==(kind==1?-ENOMEM:kind==3?-EBUSY:0));
  if(kind==2){fail_unmap=PAGES/2;assert(camss_a5_fw_memory_unmap(&m)==-EIO&&m.mapped&&m.cpu&&!frees);assert(camss_a5_fw_memory_free(&m)==-EBUSY);fail_unmap=-1;}
  released(&m);
 }
 const u64 bad_physical[]={0,0x9ab00001,0xfffffffffffff000ULL};
 for(unsigned k=0;k<3;k++){reset();m=(struct camss_a5_fw_memory){};assert(camss_a5_fw_carveout_alloc(&device,&m,bad_physical[k],CAMSS_A5_FW_WINDOW)==-EINVAL&&!allocs);}
 reset();m=(struct camss_a5_fw_memory){};assert(camss_a5_fw_carveout_alloc(&device,&m,0x9ab00000,PAGE_SIZE)==-EINVAL&&!allocs);
 reset();m=(struct camss_a5_fw_memory){};absent_region=true;assert(camss_a5_fw_carveout_alloc(&device,&m,0x9ab00000,CAMSS_A5_FW_WINDOW)==-EINVAL&&!allocs);
 reset();m=(struct camss_a5_fw_memory){};fail_alloc=true;assert(camss_a5_fw_carveout_alloc(&device,&m,0x9ab00000,CAMSS_A5_FW_WINDOW)==-ENOMEM&&allocs==1&&!frees);
 reset();m=(struct camss_a5_fw_memory){};device.domain=NULL;assert(camss_a5_fw_carveout_alloc(&device,&m,0x9ab00000,CAMSS_A5_FW_WINDOW)==-ENODEV&&!allocs);
 reset();m=(struct camss_a5_fw_memory){.bytes=PAGE_SIZE};assert(camss_a5_fw_carveout_alloc(&device,&m,0x9ab00000,CAMSS_A5_FW_WINDOW)==-EBUSY&&!allocs);

	printf("MEMORY_PASS scenarios=%u pages=%u scattered_physical_above_4GiB=1 partial_unmap_keeps_RAM=1\n",scenarios,PAGES);return 0;
}
