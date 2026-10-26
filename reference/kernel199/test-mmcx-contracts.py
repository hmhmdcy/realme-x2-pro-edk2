from pathlib import Path
import hashlib,json,re,subprocess
k=Path('/home/cy122/pmos-samurai-kernel136/kernel');ref=Path(__file__).resolve().parent;out=Path('/mnt/e/edk2-samurai-out/kernel199');b=k/'drivers/media/platform/qcom/camss';cpas=(b/'camss-cpas.c').read_text();camss=(b/'camss.c').read_text()
def extract(s,name):
 m=re.search(r'^(?:static )?(?:int|void) (?:__maybe_unused )?'+name+r'\(',s,re.M);assert m,name;a=s.index('{',m.start());i=a+1;depth=1
 while depth:depth+=(s[i]=='{')-(s[i]=='}');i+=1
 return s[m.start():i]
prefix=r'''#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
typedef uint32_t u32;
#define __maybe_unused
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define U32_MAX UINT32_MAX
#define RPMH_REGULATOR_LEVEL_TURBO 384
#define CAMSS_8150 8150
struct device { void *data; };struct device_link { int unused; };
struct clk_bulk_data { int clk; };
struct camss_cpas {struct device *dev,*mmcx;struct device_link *mmcx_link;bool performance_requested;void *top,*noc;struct clk_bulk_data clocks[7];bool enabled;};
struct camss_cpas_reg {u32 offset,mask,value;};
struct resources_icc {struct {unsigned int avg,peak;} icc_bw_tbl;};
struct camss_resources {int version,icc_path_num;const struct resources_icc *icc_res;};
struct camss {struct device *dev;struct camss_cpas *cpas;struct camss_resources *res;int icc_path[4];};
static int failure,own_level,clock_refs,link_refs,domain_refs,errors,icc_failure_index=-1;static unsigned int tests,mmio_writes;
static u32 top_regs[2],noc_regs[0x5000/4],avg[4],peak[4];
static int dev_pm_genpd_set_performance_state(struct device *d,unsigned int level){(void)d;if((level==384&&failure==1)||(!level&&failure==7))return -EIO;own_level=level;return 0;}
static int clk_set_rate(int clk,unsigned long rate){assert(own_level==384);if((clk==3&&failure==2)||(clk==5&&failure==3))return -EIO;assert(rate==80000000||rate==150000000);return 0;}
static int clk_bulk_prepare_enable(unsigned int n,struct clk_bulk_data *c){(void)c;assert(n==7&&own_level==384);if(failure==4)return -EIO;assert(clock_refs==0);clock_refs++;return 0;}
static void clk_bulk_disable_unprepare(unsigned int n,struct clk_bulk_data *c){(void)c;assert(n==7&&clock_refs==1);clock_refs--;}
static u32 readl(void *p){if(failure==5&&p==top_regs)return 0;if(failure==6&&p==(void*)((unsigned char*)noc_regs+0x430)&&mmio_writes)return *(u32*)p^1;return *(u32*)p;}
static void writel(u32 v,void *p){*(u32*)p=v;mmio_writes++;}
#define dev_err(...) do {errors++;} while(0)
static void device_link_del(struct device_link *l){(void)l;assert(link_refs==1);link_refs--;}
static void dev_pm_domain_detach(struct device *d,bool poweroff){(void)d;assert(poweroff&&domain_refs==1);domain_refs--;own_level=0;}
static void *dev_get_drvdata(struct device *d){return d->data;}
static int icc_set_bw(int index,unsigned int a,unsigned int p){if(!a&&index==icc_failure_index){icc_failure_index=-1;return -EIO;}avg[index]=a;peak[index]=p;return 0;}
'''
table=cpas[cpas.index('static const struct camss_cpas_reg sm8150_ife_qos[]'):cpas.index('\n};',cpas.index('static const struct camss_cpas_reg sm8150_ife_qos[]'))+3]
functions='\n'.join(extract(cpas,n) for n in ['camss_cpas_stop','camss_cpas_release','camss_cpas_resume','camss_cpas_suspend'])+'\n'+'\n'.join(extract(camss,n) for n in ['camss_runtime_suspend','camss_runtime_resume'])
body=r'''
static struct device dev,mmcx;static struct device_link link;static struct camss_cpas cp;
static const struct resources_icc paths[4]={{{100,200}},{{101,201}},{{102,202}},{{103,203}}};static struct camss_resources res={8150,4,paths};static struct camss cam={&dev,&cp,&res,{0,1,2,3}};
static void reset(void){memset(&cp,0,sizeof(cp));memset(noc_regs,0,sizeof(noc_regs));for(int i=0;i<7;i++)cp.clocks[i].clk=i;cp.dev=&dev;cp.mmcx=&mmcx;cp.mmcx_link=&link;cp.top=top_regs;cp.noc=noc_regs;top_regs[0]=0x010705;top_regs[1]=0x10000001;dev.data=&cam;cam.cpas=&cp;res.version=8150;failure=own_level=clock_refs=errors=0;link_refs=domain_refs=1;mmio_writes=0;icc_failure_index=-1;for(int i=0;i<4;i++){avg[i]=paths[i].icc_bw_tbl.avg;peak[i]=paths[i].icc_bw_tbl.peak;}}
static void running(void){assert(camss_cpas_resume(&cam)==0);assert(cp.enabled&&cp.performance_requested&&own_level==384&&clock_refs==1);}
static void stopped(void){assert(!cp.enabled&&!cp.performance_requested&&own_level==0&&clock_refs==0);}
int main(void){
 for(int f=1;f<=6;f++){reset();failure=f;assert(camss_cpas_resume(&cam)==(f==5?-EOPNOTSUPP:-EIO));stopped();tests++;}
 reset();running();assert(camss_cpas_suspend(&cam)==0);stopped();tests++;
 reset();running();failure=7;assert(camss_cpas_suspend(&cam)==-EIO);assert(cp.enabled&&cp.performance_requested&&own_level==384&&clock_refs==1);failure=0;assert(camss_cpas_suspend(&cam)==0);stopped();tests++;
 reset();running();failure=7;assert(camss_runtime_suspend(&dev)==-EIO);assert(cp.enabled&&own_level==384&&clock_refs==1);for(int i=0;i<4;i++)assert(avg[i]==100U+i&&peak[i]==200U+i);failure=0;assert(camss_runtime_suspend(&dev)==0);stopped();tests++;
 for(int f=0;f<4;f++){reset();running();icc_failure_index=f;assert(camss_runtime_suspend(&dev)==-EIO);assert(cp.enabled&&own_level==384&&clock_refs==1);for(int i=0;i<4;i++)assert(avg[i]==100U+i&&peak[i]==200U+i);assert(camss_cpas_suspend(&cam)==0);stopped();tests++;}
 reset();failure=1;assert(camss_runtime_resume(&dev)==-EIO);for(int i=0;i<4;i++)assert(!avg[i]&&!peak[i]);stopped();tests++;
 reset();running();camss_cpas_release(&cp);assert(!clock_refs&&!own_level&&!link_refs&&!domain_refs);tests++;
 reset();running();failure=7;camss_cpas_release(&cp);assert(!clock_refs&&!own_level&&!link_refs&&!domain_refs&&errors==1);tests++;
 reset();res.version=1;assert(camss_cpas_resume(&cam)==0&&!own_level&&!clock_refs);cam.cpas=NULL;assert(camss_cpas_suspend(&cam)==0);tests++;
 printf("CAMSS_MMCX_CONTRACTS_PASS cases=%u\n",tests);return 0;
}
'''
records=[]
for label,func in [('fixed',functions),('missing-vote',functions.replace('ret = dev_pm_genpd_set_performance_state(cpas->mmcx, RPMH_REGULATOR_LEVEL_TURBO);','ret = 0;'))]:
 c=out/('mmcx-'+label+'-private.c');c.write_text(prefix+table+func+body);exe=out/('mmcx-'+label+'-private');p=subprocess.run(['gcc','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-sign-compare','-Wno-missing-field-initializers','-fsanitize=address,undefined','-fno-omit-frame-pointer','-g',str(c),'-o',str(exe)],capture_output=True);(out/('mmcx-'+label+'-compile-private.log')).write_bytes(p.stdout+p.stderr);assert p.returncode==0,p.stderr.decode();p=subprocess.run([str(exe)],capture_output=True,timeout=20);(out/('mmcx-'+label+'-run-private.log')).write_bytes(p.stdout+p.stderr);assert (p.returncode==0)==(label=='fixed');records.append(dict(label=label,returncode=p.returncode));
 if label=='fixed':count=int(re.search(rb'cases=(\d+)',p.stdout).group(1))
r=dict(stage=199,actual_driver_functions_extracted=True,asan_ubsan_passed=True,cases=count,missing_performance_vote_mutation_detected=True,source_sha256={str(p.relative_to(k)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [b/'camss-cpas.c',b/'camss.c']},results=records);(ref/'mmcx-host-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))

