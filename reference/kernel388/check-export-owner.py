from pathlib import Path
import json,re,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;s=(P/'videobuf2-dma-sg.c.proposed').read_text()
def function(name):
 m=re.search(r'(?:static )?struct dma_buf \*'+name+r'\([^;]+?\n\{.*?^\}\n',s,re.S|re.M);assert m,name;return m.group()
prefix=r'''
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
struct module{unsigned refs;};static struct module allocator,platform;
#define THIS_MODULE (&allocator)
#define WARN_ON(x) (x)
#define IS_ERR(x) ((uintptr_t)(x)>=(uintptr_t)-4095)
struct vb2_buffer{unsigned unused;};struct sg_table{unsigned unused;};
struct vb2_dma_sg_buf{unsigned size,refcount;struct sg_table *dma_sgt;bool dma_mapped;};
struct dma_buf{struct module *owner;struct vb2_dma_sg_buf *priv;unsigned refs;bool deferred;};
struct dma_buf_export_info{void *ops,*priv;struct module *owner;unsigned size;unsigned long flags;};
#define DEFINE_DMA_BUF_EXPORT_INFO(x) struct dma_buf_export_info x={.owner=THIS_MODULE}
static int vb2_dma_sg_dmabuf_ops;
static unsigned fail_export,retired;
static struct dma_buf *dma_buf_export(struct dma_buf_export_info *i){
 assert(i->ops==&vb2_dma_sg_dmabuf_ops);if(fail_export)return (void *)(intptr_t)-ENOMEM;
 struct dma_buf *b=calloc(1,sizeof(*b));assert(b);b->owner=i->owner;b->priv=i->priv;b->refs=1;++b->owner->refs;return b;
}
static void refcount_inc(unsigned *ref){++*ref;}
static void allocator_put(struct vb2_dma_sg_buf *p){assert(p->refcount);if(!--p->refcount){assert(platform.refs || allocator.refs);p->dma_mapped=false;++retired;}}
static void file_put(struct dma_buf *b){assert(b->refs);if(!--b->refs)b->deferred=true;}
static void complete_deferred_release(struct dma_buf *b){assert(b->deferred && b->refs==0);allocator_put(b->priv);assert(!b->priv->dma_mapped);assert(b->owner->refs);--b->owner->refs;free(b);}
'''
cases=r'''
int main(void){unsigned cases=0;struct vb2_buffer vb={0};struct sg_table sg={0};
 for(unsigned owner=0;owner<2;++owner){
  struct vb2_dma_sg_buf storage={4096,1,&sg,true};
  struct dma_buf *b=owner?vb2_dma_sg_get_dmabuf_owner(&vb,&storage,3,&platform):vb2_dma_sg_get_dmabuf(&vb,&storage,3);
  assert(b && b->owner==(owner?&platform:&allocator) && storage.refcount==2);
  allocator_put(&storage); /* queue/video FD released */
  b->refs+=2; /* mmap and a temporary global observer reference */
  file_put(b);assert(b->owner->refs==1 && storage.dma_mapped);
  file_put(b);assert(b->owner->refs==1 && storage.dma_mapped);
  file_put(b);assert(b->deferred && b->owner->refs==1 && storage.dma_mapped);
  complete_deferred_release(b);assert(!platform.refs && !allocator.refs && !storage.dma_mapped);++cases;
 }
 fail_export=1;struct vb2_dma_sg_buf storage={4096,1,&sg,true};assert(!vb2_dma_sg_get_dmabuf_owner(&vb,&storage,3,&platform));assert(storage.refcount==1 && !platform.refs);++cases;
 fail_export=0;storage.dma_sgt=NULL;assert(!vb2_dma_sg_get_dmabuf_owner(&vb,&storage,3,&platform));assert(storage.refcount==1 && !platform.refs);++cases;
 assert(retired==2);printf("EXPORT_OWNER_MODEL cases=%u passed=1\n",cases);return 0;}
'''
model=P/'export-owner-model.c';model.write_text(prefix+function('vb2_dma_sg_get_dmabuf_owner')+function('vb2_dma_sg_get_dmabuf')+cases)
q=subprocess.run(['cc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=address,undefined','-no-pie',str(model),'-o',str(P/'export-owner-model')],capture_output=True)
(P/'export-owner-model-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-4000:]
q=subprocess.run([str(P/'export-owner-model')],capture_output=True);(P/'export-owner-model-run.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-4000:]
report=dict(stage=388,actual_new_and_legacy_export_functions=True,asan_ubsan=True,cases=4,default_owner_behavior_kept=True,custom_owner_file_lifetime=True,queue_and_video_fd_release_before_export=True,mmap_and_observer_refs_and_deferred_fput_modelled=True,allocator_release_precedes_owner_put=True,allocation_and_export_failures_balanced=True,dma_buf_core_and_allocator_provider_only=True,hardware_export_lifetime_not_claimed=True,passed=True)
(HERE/'export-owner-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
