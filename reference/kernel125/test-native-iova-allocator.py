from pathlib import Path
import runpy,re,subprocess,json,hashlib
r=Path('/mnt/e/RealmeX2Pro edk2');runpy.run_path(str(r/'reference/kernel122/ensure-rootfs-volume.py'));k=Path('/home/cy122/pmos-samurai-rootfs122/camera125/kernel');out=Path('/mnt/e/edk2-samurai-out/kernel125/c-contracts');out.mkdir(exist_ok=True);t=(k/'drivers/iommu/iova.c').read_text()
def function(name):
 m=re.search(r'\b'+name+r'\([^;{}]*\)\s*\{',t);assert m,name;start=t.rfind('\n\n',0,m.start())+2;b=t.index('{',m.start());i=b+1;d=1
 while d:d+=(t[i]=='{')-(t[i]=='}');i+=1
 return t[start:i]
names=['to_iova','init_iova_domain','__get_cached_rbnode','__cached_rbnode_insert_update','iova_find_limit','iova_insert_rbtree','__alloc_and_insert_iova_range','alloc_iova','__is_range_overlap','alloc_and_init_iova','__insert_new_range','__adjust_overlap_range','reserve_iova']
source='''#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <limits.h>
#include <errno.h>
#include <linux/rbtree.h>
#define IOVA_ANCHOR (~0UL)
#define PAGE_SIZE 4096UL
#define WARN_ON(x) ({bool v=!!(x);assert(!v);v;})
#define spin_lock_init(p) (*(p)=0)
#define spin_lock_irqsave(p,flags) do{flags=0;assert(!*(p));*(p)=1;}while(0)
#define spin_unlock_irqrestore(p,flags) do{assert(*(p)==1);assert(flags==0);*(p)=0;}while(0)
struct iova{struct rb_node node;unsigned long pfn_hi,pfn_lo;};
struct iova_domain{int iova_rbtree_lock;struct rb_root rbroot;struct rb_node *cached_node,*cached32_node;unsigned long granule,start_pfn,dma_32bit_pfn,max32_alloc_size;struct iova anchor;};
static bool fail_alloc;
static unsigned long iova_shift(struct iova_domain*d){return __builtin_ctzl(d->granule);}
static bool is_power_of_2(unsigned long x){return x && !(x&(x-1));}
static unsigned long fls_long(unsigned long x){return x?8*sizeof(x)-__builtin_clzl(x):0;}
static struct iova *alloc_iova_mem(void){return fail_alloc?NULL:calloc(1,sizeof(struct iova));}
static void free_iova_mem(struct iova*p){free(p);}
'''+''.join(function(n)+'\n' for n in names)+'''
static void clear(struct iova_domain*d){struct rb_node*n;while((n=rb_first(&d->rbroot))){struct iova*i=to_iova(n);rb_erase(n,&d->rbroot);if(i!=&d->anchor)free(i);}}
static void prepare(struct iova_domain*d){*d=(struct iova_domain){0};init_iova_domain(d,4096,1);assert(reserve_iova(d,0,(0x7400000UL>>12)-1));assert(reserve_iova(d,0xe0000000UL>>12,0xffffffffUL>>12));}
static void valid(struct iova*i){assert(i&&i->pfn_lo>=(0x7400000UL>>12)&&i->pfn_hi<(0xe0000000UL>>12));}
int main(void){struct iova_domain d={0};struct iova*i;
 init_iova_domain(&d,4096,1);i=alloc_iova(&d,256,0xffffffffUL>>12,false);assert(i && (i->pfn_lo<<12)==0xfff00000UL);clear(&d);
 prepare(&d);i=alloc_iova(&d,256,0xffffffffUL>>12,false);valid(i);assert((i->pfn_lo<<12)==0xdff00000UL);clear(&d);
 prepare(&d);i=alloc_iova(&d,0xd8c00000UL>>12,0xffffffffUL>>12,false);valid(i);assert((i->pfn_lo<<12)==0x7400000UL && (i->pfn_hi<<12)+4096==0xe0000000UL);assert(!alloc_iova(&d,1,0xffffffffUL>>12,false));clear(&d);
 prepare(&d);assert(!alloc_iova(&d,(0xd8c00000UL>>12)+1,0xffffffffUL>>12,false));clear(&d);
 for(int aligned=0;aligned<2;aligned++){prepare(&d);for(unsigned n=0;n<512;n++){unsigned long size=(n*37U)%1024+1;i=alloc_iova(&d,size,0xffffffffUL>>12,aligned);valid(i);for(struct rb_node*p=rb_first(&d.rbroot);p;p=rb_next(p)){struct iova*other=to_iova(p);if(other!=i)assert(other->pfn_hi<i->pfn_lo||other->pfn_lo>i->pfn_hi);}}clear(&d);}
 prepare(&d);fail_alloc=true;assert(!alloc_iova(&d,1,0xffffffffUL>>12,false));fail_alloc=false;clear(&d);
 puts("NATIVE_IOVA_RBTREE_FULL_WINDOW_ALLOCATION_PASS");return 0;}
'''
p=out/'native-iova-allocator.c';p.write_text(source);args=['gcc','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-sign-compare','-Wno-missing-field-initializers','-fsanitize=address,undefined','-fno-omit-frame-pointer','-g','-I'+str(k/'tools/include'),'-o',str(out/'native-iova-allocator'),str(p),str(k/'tools/lib/rbtree.c')]
cp=subprocess.run(args,capture_output=True,timeout=60);(out/'native-iova-compile.txt').write_bytes(cp.stdout+cp.stderr);assert cp.returncode==0,cp.stderr.decode()[:4000]
cp=subprocess.run([str(out/'native-iova-allocator')],capture_output=True,timeout=30);(out/'native-iova-run.txt').write_bytes(cp.stdout+cp.stderr);assert cp.returncode==0,cp.stderr.decode()[:4000]
report=dict(actual_kernel_iova_functions_extracted_without_rewrite=names,actual_kernel_tools_rbtree_linked=True,old_unreserved_allocation_reproduced=0xfff00000,new_reserved_allocation=0xdff00000,full_native_window_allocation_exact_bounds=True,extra_page_and_oversize_fail=True,randomized_size_allocations=1024,all_allocations_in_native_window_and_nonoverlapping=True,allocation_failure_checked=True,asan_ubsan_pass=True,source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),host_only_not_real_smmu_dma=True,phone_unchanged=True)
(r/'reference/kernel125/iova-allocator-validation.json').write_text(json.dumps(report,indent=2)+'\n');print('IOVA125_ACTUAL_ALLOCATOR_AND_RBTREE_1024_ALLOCATION_ASAN_UBSAN_PASS')
