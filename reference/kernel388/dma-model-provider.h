/* Test provider only; actual import/lifetime functions are included separately. */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>
typedef uint8_t u8;typedef uint16_t u16;typedef uint32_t u32;typedef uint64_t u64;typedef uint64_t phys_addr_t;
#define U32_MAX UINT32_MAX
#define U64_MAX UINT64_MAX
#define GFP_KERNEL 0
#define PAGE_SIZE 4096U
#define PAGE_ALIGN(x) (((u64)(x)+4095)&~4095ULL)
#define min_t(t,a,b) ((t)(a)<(t)(b)?(t)(a):(t)(b))
#define DIV_ROUND_UP(a,b) (((a)+(b)-1)/(b))
#define IS_ALIGNED(a,b) (!((a)&((b)-1)))
#define IS_ERR(x) ((uintptr_t)(x)>=(uintptr_t)-4095)
#define PTR_ERR(x) ((int)(intptr_t)(x))
#define ERR_PTR(x) ((void *)(intptr_t)(x))
#define msecs_to_jiffies(x) (x)
#define for_each_sgtable_dma_sg(t,s,i) for((i)=0;(i)<(t)->nents && ((s)=&(t)->sgl[i]);++(i))
#define for_each_sgtable_sg(t,s,i) for((i)=0;(i)<(t)->orig_nents && ((s)=&(t)->sgl[i]);++(i))
enum dma_data_direction{DMA_TO_DEVICE=1,DMA_FROM_DEVICE=2};
enum dma_resv_usage{DMA_RESV_USAGE_WRITE=1,DMA_RESV_USAGE_READ=2};
struct iommu_domain{bool dma;};struct device{struct iommu_domain *domain;};
struct page{phys_addr_t physical;};
struct scatterlist{struct page *page;u32 length,offset;u64 address,dma_length;};
struct sg_table{struct scatterlist *sgl;unsigned nents,orig_nents;};
struct dma_resv{long waited;};
struct dma_buf{u64 size;unsigned refs;struct dma_resv resv_storage,*resv;struct sg_table *table;u8 *cpu;};
struct dma_buf_attachment{struct dma_buf *buffer;bool mapped;struct sg_table wrapper;};
static struct dma_buf_attachment *live_attachments[32];
static unsigned refs,attachments,mappings,allocations,waits,sorts;
static bool fail_attach,fail_map,fail_alloc;
static enum dma_resv_usage last_usage;
static struct iommu_domain *iommu_get_domain_for_dev(struct device *d){return d->domain;}
static bool iommu_is_dma_domain(struct iommu_domain *d){return d->dma;}
#define sg_dma_len(s) ((s)->dma_length)
#define sg_dma_address(s) ((s)->address)
#define sg_page(s) ((s)->page)
#define sg_phys(s) ((s)->page->physical+(s)->offset)
static long dma_resv_wait_timeout(struct dma_resv *r,enum dma_resv_usage u,bool intr,unsigned timeout){assert(intr && timeout==1000);++waits;last_usage=u;return r->waited;}
static void get_dma_buf(struct dma_buf *b){assert(b->refs);++b->refs;++refs;}
static void dma_buf_put(struct dma_buf *b){assert(b->refs && refs);--b->refs;--refs;}
static struct dma_buf_attachment *dma_buf_attach(struct dma_buf *b,struct device *d){assert(b->refs && d->domain);if(fail_attach)return ERR_PTR(-ENOMEM);struct dma_buf_attachment *a=calloc(1,sizeof(*a));assert(a);a->buffer=b;unsigned i;for(i=0;i<32 && live_attachments[i];++i){}assert(i<32);live_attachments[i]=a;++attachments;return a;}
static struct sg_table *dma_buf_map_attachment_unlocked(struct dma_buf_attachment *a,enum dma_data_direction dir){
 assert(dir==DMA_TO_DEVICE || dir==DMA_FROM_DEVICE);if(fail_map)return ERR_PTR(-EIO);assert(!a->mapped);a->mapped=true;++mappings;
 struct sg_table *from=a->buffer->table,*to=&a->wrapper;to->nents=to->orig_nents=from->nents;to->sgl=calloc(from->nents,sizeof(*to->sgl));assert(to->sgl);
 for(unsigned i=0;i<from->nents;++i){to->sgl[i].address=from->sgl[i].address;to->sgl[i].dma_length=from->sgl[i].dma_length;}
 return to; /* DMABUF_DEBUG: no page, offset, or physical length fields. */
}
static void dma_buf_unmap_attachment_unlocked(struct dma_buf_attachment *a,struct sg_table *t,enum dma_data_direction dir){assert(t==&a->wrapper && a->mapped && mappings);assert(dir==DMA_TO_DEVICE || dir==DMA_FROM_DEVICE);free(t->sgl);memset(t,0,sizeof(*t));a->mapped=false;--mappings;}
static void dma_buf_detach(struct dma_buf *b,struct dma_buf_attachment *a){assert(a->buffer==b && !a->mapped && attachments);for(unsigned i=0;i<32;++i)if(live_attachments[i]==a)live_attachments[i]=NULL;--attachments;free(a);}
static phys_addr_t iommu_iova_to_phys(struct iommu_domain *domain,u64 address){
 assert(domain && domain->dma);
 for(unsigned i=0;i<32;++i){struct dma_buf_attachment *a=live_attachments[i];if(!a || !a->mapped)continue;struct sg_table *t=a->buffer->table;u64 logical=0;
  for(unsigned j=0;j<t->nents;++j){if(address>=t->sgl[j].address && address-t->sgl[j].address<t->sgl[j].dma_length){
    u64 offset=logical+address-t->sgl[j].address;
    for(unsigned k=0;k<t->orig_nents;++k){if(offset<t->sgl[k].length)return sg_phys(&t->sgl[k])+offset;offset-=t->sgl[k].length;}
    return 0;
   }logical+=t->sgl[j].dma_length;}
 }return 0;
}
static void *kvmalloc_array(size_t n,size_t bytes,int flags){(void)flags;if(fail_alloc)return NULL;if(n && bytes>SIZE_MAX/n)return NULL;void *p=calloc(n,bytes);if(p)++allocations;return p;}
static void kvfree(void *p){if(p){assert(allocations);--allocations;free(p);}}
static void sort(void *base,size_t n,size_t size,int(*compare)(const void *,const void *),void *swap){assert(!swap);++sorts;qsort(base,n,size,compare);}
static void clean_provider(void){assert(!refs && !attachments && !mappings && !allocations);fail_attach=fail_map=fail_alloc=false;}
static void init_buffer(struct dma_buf *b,struct sg_table *t,u64 size){memset(b,0,sizeof(*b));b->size=size;b->refs=1;b->table=t;b->resv=&b->resv_storage;b->resv->waited=1;}
