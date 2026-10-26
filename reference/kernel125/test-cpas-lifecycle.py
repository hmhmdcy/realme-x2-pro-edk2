from pathlib import Path
import runpy,re,subprocess,json,hashlib
r=Path('/mnt/e/RealmeX2Pro edk2');runpy.run_path(str(r/'reference/kernel122/ensure-rootfs-volume.py'));k=Path('/home/cy122/pmos-samurai-rootfs122/camera125/kernel');base=k/'drivers/media/platform/qcom/camss';out=Path('/mnt/e/edk2-samurai-out/kernel125/c-contracts');out.mkdir(exist_ok=True)
t=(base/'camss-cpas.c').read_text();actual='\n'.join(l for l in t.splitlines() if not l.startswith('#include'))
core=(base/'camss.c').read_text()
def function(t,name):
 m=re.search(r'^static int __maybe_unused '+name+r'\(',t,re.M);assert m;a=m.start();b=t.index('{',m.end());i=b+1;d=1
 while d:d+=(t[i]=='{')-(t[i]=='}');i+=1
 return t[a:i]
pre='''#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <stddef.h>
#include <errno.h>
typedef uint32_t u32;typedef uint64_t u64;
#define __iomem
#define __maybe_unused
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define U32_MAX UINT32_MAX
#define GFP_KERNEL 0
#define IORESOURCE_MEM 1
#define CAMSS_8150 8150
#define IOMMU_DOMAIN_DMA 1
#define IOMMU_DOMAIN_DMA_FQ 2
#define IOMMU_RESV_RESERVED 1
#define dev_err(...) ((void)0)
#define dev_err_probe(dev,ret,...) (ret)
#define IS_ERR(p) ((intptr_t)(p)<0 && (intptr_t)(p)>-4096)
#define PTR_ERR(p) ((int)(intptr_t)(p))
struct list_head{struct list_head *next,*prev;};
#define LIST_HEAD(name) struct list_head name={&name,&name}
#define container_of(p,t,m) ((t*)((char*)(p)-offsetof(t,m)))
#define list_for_each_entry(pos,head,member) for(pos=container_of((head)->next,typeof(*pos),member);&pos->member!=(head);pos=container_of(pos->member.next,typeof(*pos),member))
static void list_add_tail(struct list_head*n,struct list_head*h){n->prev=h->prev;n->next=h;h->prev->next=n;h->prev=n;}
struct iommu_domain{int type;};struct iommu_resv_region{u64 start,length;int type;struct list_head list;};
struct clk{int id;};struct clk_bulk_data{const char *id;struct clk *clk;};
struct resource{u64 start,end;};struct device{void *data;};struct platform_device{struct device dev;};
struct resources_icc{struct{u32 avg,peak;}icc_bw_tbl;};struct resources{int version,icc_path_num;const struct resources_icc *icc_res;};
struct icc_path{int id;};struct camss_cpas;struct camss{struct device *dev;struct resources *res;struct camss_cpas *cpas;struct icc_path *icc_path[4];};
static struct iommu_domain domain={IOMMU_DOMAIN_DMA};static struct iommu_resv_region regions[2];
static int fault,clk_refs,clk_gets,gets,puts,allocs,map_calls,rate_calls,reads,writes,write_fault,readback_fault,icc_failure,icc_calls;
static bool null_domain;static void *allocated;static struct clk clk[7];static u32 top[0x1000/4],noc[0x5000/4];static u32 trace_offsets[20],trace_values[20];static u32 voted_avg[4],voted_peak[4];
static struct iommu_domain *iommu_get_domain_for_dev(struct device*d){return null_domain?NULL:&domain;}
static void iommu_get_resv_regions(struct device*d,struct list_head*h){gets++;if(fault!=1)list_add_tail(&regions[0].list,h);if(fault!=2)list_add_tail(&regions[1].list,h);}
static void iommu_put_resv_regions(struct device*d,struct list_head*h){puts++;h->next=h->prev=h;}
static void *devm_kzalloc(struct device*d,size_t sz,int flags){allocs++;if(fault==3)return NULL;assert(!allocated);return allocated=calloc(1,sz);}
static struct platform_device *to_platform_device(struct device*d){return container_of(d,struct platform_device,dev);}
static struct resource *platform_get_resource_byname(struct platform_device*p,int type,const char*name){static struct resource top_res,noc_res;bool is_top=strcmp(name,"cpas_top")==0;if(fault==(is_top?4:6))return NULL;struct resource *r=is_top?&top_res:&noc_res;r->start=is_top?0xac40000:0xac42000;r->end=r->start+(is_top?0x1000:0x5000)-1;if(fault==(is_top?5:7))r->end--;return r;}
static u64 resource_size(struct resource*r){return r->end-r->start+1;}
static void *devm_ioremap_resource(struct device*d,struct resource*r){map_calls++;bool is_top=r->start==0xac40000;if(fault==(is_top?8:9))return (void*)(intptr_t)-EIO;return is_top?(void*)top:(void*)noc;}
static int devm_clk_bulk_get(struct device*d,int n,struct clk_bulk_data*b){clk_gets++;assert(n==7);if(fault==10)return -EIO;for(int i=0;i<n;i++){clk[i].id=i;b[i].clk=&clk[i];}return 0;}
static int clk_set_rate(struct clk*c,u64 rate){rate_calls++;assert((c->id==3&&rate==80000000)||(c->id==5&&rate==150000000));return fault==(c->id==3?11:12)?-EIO:0;}
static int clk_bulk_prepare_enable(int n,struct clk_bulk_data*b){assert(n==7&&clk_refs==0);if(fault==13)return -EIO;clk_refs++;return 0;}
static void clk_bulk_disable_unprepare(int n,struct clk_bulk_data*b){assert(n==7&&clk_refs==1);clk_refs--;}
static u32 readl(void*p){assert(clk_refs==1);reads++;uintptr_t a=(uintptr_t)p;if(a>=(uintptr_t)top&&a<(uintptr_t)(top+ARRAY_SIZE(top)))return *(u32*)p;assert(a>=(uintptr_t)noc&&a<(uintptr_t)(noc+ARRAY_SIZE(noc)));u32 value=*(u32*)p;if(readback_fault&&writes==readback_fault&&trace_offsets[writes-1]==a-(uintptr_t)noc){u32 mask=(a-(uintptr_t)noc==0x438||a-(uintptr_t)noc==0x838)?0x70:0xffffffff;value^=mask&-mask;}return value;}
static void writel(u32 value,void*p){assert(clk_refs==1);uintptr_t off=(uintptr_t)p-(uintptr_t)noc;assert(off<0x5000&&off%4==0&&writes<20);trace_offsets[writes]=off;trace_values[writes++]=value;*(u32*)p=value;}
static void *dev_get_drvdata(struct device*d){return d->data;}
static int icc_set_bw(struct icc_path*p,u32 avg,u32 peak){icc_calls++;voted_avg[p->id]=avg;voted_peak[p->id]=peak;if(icc_calls==icc_failure)return -EIO;return 0;}
'''
source=pre+actual+'\n'+function(core,'camss_runtime_suspend')+'\n'+function(core,'camss_runtime_resume')+'''
static struct platform_device pdev;static struct resources_icc icc[4]={{{38400,76800}},{{2097152,2097152}},{{0,2097152}},{{2097152,3000000}}};static struct resources resources={8150,4,icc};static struct icc_path paths[4];static struct camss camss;
static void clear(void){free(allocated);allocated=NULL;camss=(struct camss){.dev=&pdev.dev,.res=&resources};pdev.dev.data=&camss;resources.version=8150;domain.type=IOMMU_DOMAIN_DMA;null_domain=false;for(int i=0;i<4;i++){paths[i].id=i;camss.icc_path[i]=&paths[i];voted_avg[i]=voted_peak[i]=0;}regions[0]=(struct iommu_resv_region){.start=0,.length=0x7400000,.type=IOMMU_RESV_RESERVED};regions[1]=(struct iommu_resv_region){.start=0xe0000000,.length=0x20000000,.type=IOMMU_RESV_RESERVED};fault=clk_refs=clk_gets=gets=puts=allocs=map_calls=rate_calls=reads=writes=write_fault=readback_fault=icc_failure=icc_calls=0;memset(top,0,sizeof(top));for(unsigned i=0;i<ARRAY_SIZE(noc);i++)noc[i]=0xa5a5a5a5;top[0]=0xab010705;top[1]=0x10000000;}
static void init(void){assert(camss_cpas_init(&camss)==0);assert(gets==1&&puts==1&&reads==0&&writes==0&&clk_refs==0);}
int main(void){
 clear();resources.version=845;assert(camss_cpas_init(&camss)==0&&allocs==0&&gets==0);assert(camss_cpas_resume(&camss)==0&&reads==0&&writes==0);camss_cpas_suspend(&camss);
 clear();null_domain=true;assert(camss_cpas_init(&camss)==-ENODEV&&allocs==0&&gets==0);clear();domain.type=99;assert(camss_cpas_init(&camss)==-ENODEV&&allocs==0);
 for(int f=1;f<=10;f++){clear();fault=f;assert(camss_cpas_init(&camss)<0&&clk_refs==0&&reads==0&&writes==0&&!camss.cpas&&gets==puts);}
 clear();regions[0].type=99;assert(camss_cpas_init(&camss)==-EINVAL);clear();regions[1].length--;assert(camss_cpas_init(&camss)==-EINVAL);clear();regions[0].start=1;assert(camss_cpas_init(&camss)==-EINVAL);
 for(int revision=0;revision<=1;revision++){clear();init();top[1]=0x10000000+revision;assert(camss_cpas_resume(&camss)==0&&clk_refs==1&&camss.cpas->enabled&&writes==10);
'''
oracle=json.loads((r/'reference/kernel125/native-qos-validation.json').read_text())['qos_revisions'][0]['ife_ports'];index=0
for port in oracle:
 for row in port['updates']:
  mask=row['mask'] if row['masked'] else 0xffffffff;expected=(0xa5a5a5a5&~mask)|(row['value']<<row['shift']) if row['masked'] else row['value']
  source+=f'assert(trace_offsets[{index}]=={row["offset"]} && trace_values[{index}]=={expected});\n';index+=1
source+='''camss_cpas_suspend(&camss);assert(clk_refs==0&&!camss.cpas->enabled);camss_cpas_suspend(&camss);assert(clk_refs==0);}
 u32 bad_versions[]={0x10020000,0x10000002,0,0xffffffff};for(unsigned i=0;i<ARRAY_SIZE(bad_versions);i++){clear();init();top[1]=bad_versions[i];assert(camss_cpas_resume(&camss)==-EOPNOTSUPP&&clk_refs==0&&writes==0&&reads==2&&!camss.cpas->enabled);}
 clear();init();top[0]=0x010700;assert(camss_cpas_resume(&camss)==-EOPNOTSUPP&&writes==0&&clk_refs==0);
 for(int f=11;f<=13;f++){clear();init();fault=f;assert(camss_cpas_resume(&camss)==-EIO&&clk_refs==0&&reads==0&&writes==0&&!camss.cpas->enabled);}
 for(int f=1;f<=10;f++){clear();init();readback_fault=f;assert(camss_cpas_resume(&camss)==-EIO&&clk_refs==0&&!camss.cpas->enabled&&writes==f);}
 for(int f=1;f<=4;f++){clear();init();icc_failure=f;assert(camss_runtime_resume(&pdev.dev)==-EIO&&clk_refs==0&&reads==0&&writes==0);for(int i=0;i<4;i++)assert(voted_avg[i]==0&&voted_peak[i]==0);}
 clear();init();top[1]=0x10020000;assert(camss_runtime_resume(&pdev.dev)==-EOPNOTSUPP&&clk_refs==0&&writes==0);for(int i=0;i<4;i++)assert(voted_avg[i]==0&&voted_peak[i]==0);
 for(int f=1;f<=4;f++){clear();init();assert(camss_runtime_resume(&pdev.dev)==0&&clk_refs==1);icc_calls=0;icc_failure=f;assert(camss_runtime_suspend(&pdev.dev)==-EIO&&clk_refs==1&&camss.cpas->enabled);for(int i=0;i<4;i++)assert(voted_avg[i]==icc[i].icc_bw_tbl.avg&&voted_peak[i]==icc[i].icc_bw_tbl.peak);icc_failure=0;assert(camss_runtime_suspend(&pdev.dev)==0&&clk_refs==0&&!camss.cpas->enabled);}
 clear();init();assert(camss_runtime_resume(&pdev.dev)==0);assert(camss_runtime_suspend(&pdev.dev)==0);for(int i=0;i<4;i++)assert(voted_avg[i]==0&&voted_peak[i]==0);free(allocated);allocated=NULL;puts("CPAS_RESOURCE_VERSION_QOS_AND_RUNTIME_UNWIND_PASS");return 0;}
'''
# puts() counter would shadow the C library function: use a neutral test name.
source=re.sub(r'\bputs\b(?!\s*\()', 'put_calls',source)
p=out/'cpas-lifecycle.c';p.write_text(source)
args=['gcc','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-sign-compare','-Wno-missing-field-initializers','-fsanitize=address,undefined','-fno-omit-frame-pointer','-g','-o',str(out/'cpas-lifecycle'),str(p)]
cp=subprocess.run(args,capture_output=True,timeout=60);(out/'cpas-lifecycle-compile.txt').write_bytes(cp.stdout+cp.stderr);assert cp.returncode==0,cp.stderr.decode()[:4000]
cp=subprocess.run([str(out/'cpas-lifecycle')],capture_output=True,timeout=30);(out/'cpas-lifecycle-run.txt').write_bytes(cp.stdout+cp.stderr);assert cp.returncode==0,cp.stderr.decode()[:4000]
report=dict(actual_cpas_and_runtime_functions_extracted=True,function_bodies_not_rewritten=True,driver_qos_table_checked_against_independent_native_source_parser=True,other_soc_untouched=True,initialization_fault_cases=15,supported_revision_cases=2,unsupported_revision_camera_cases=5,clock_faults=3,qos_readback_faults=10,resume_icc_faults=4,suspend_icc_restore_cases=4,cpas_fail_icc_rollback=1,normal_runtime_roundtrip=1,masked_urgency_preserves_unrelated_bits=True,unsupported_revision_qos_writes=0,asan_ubsan_pass=True,source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),host_stubs_not_hardware=True,phone_unchanged=True)
(r/'reference/kernel125/cpas-c-validation.json').write_text(json.dumps(report,indent=2)+'\n');print('CPAS125_ACTUAL_C_45_CASES_NATIVE_ORACLE_ASAN_UBSAN_PASS')
