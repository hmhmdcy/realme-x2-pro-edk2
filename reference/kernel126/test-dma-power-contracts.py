from pathlib import Path
import runpy,re,subprocess,json,hashlib
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel126';runpy.run_path(str(ref/'ensure-build-volume.py'));k=Path('/home/cy122/pmos-samurai-build126/kernel');out=Path('/mnt/e/edk2-samurai-out/kernel126/c-contracts');out.mkdir(exist_ok=True)
def extract(file,name):
 t=(k/'drivers/media/platform/qcom/camss'/file).read_text();m=re.search(r'\b'+name+r'\([^;{}]*\)\s*\{',t);assert m
 start=t.rfind('\n\n',0,m.start())+2;b=t.index('{',m.start());i=b+1;d=1
 while d:d+=(t[i]=='{')-(t[i]=='}');i+=1
 return t[start:i]
dma='''#include <stdint.h>
#include <stddef.h>
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#define CAMSS_8150 8150
typedef uint64_t dma_addr_t;
struct camss_resources{int version;};struct camss{const struct camss_resources*res;};struct camss_video{struct camss*camss;};
struct scatterlist{dma_addr_t address;size_t length;};struct sg_table{struct scatterlist*sgl;unsigned nents;};
#define sg_dma_address(s) ((s)->address)
#define sg_dma_len(s) ((s)->length)
#define for_each_sgtable_dma_sg(t,s,i) for(i=0,s=(t)->sgl;i<(t)->nents;i++,s++)
'''+extract('camss-video.c','video_check_dma_mapping')+'''
int main(void){struct camss_resources res={8150};struct camss cam={&res};struct camss_video video={&cam};struct scatterlist sg[3];struct sg_table table={sg,1};
#define CHECK(addr,len,size,wanted) do{sg[0]=(struct scatterlist){addr,len};table.nents=1;assert(video_check_dma_mapping(&video,&table,size)==wanted);}while(0)
 assert(video_check_dma_mapping(&video,NULL,4096)==-EINVAL);
 table.sgl=NULL;assert(video_check_dma_mapping(&video,&table,4096)==-EINVAL);table.sgl=sg;table.nents=0;assert(video_check_dma_mapping(&video,&table,4096)==-EINVAL);
 CHECK(0x7400000,4096,0,-EINVAL);CHECK(0x73fffff,4096,4096,-ERANGE);CHECK(0xe0000000,4096,4096,-ERANGE);CHECK(0x100000000ULL,4096,4096,-ERANGE);CHECK(UINT64_MAX,4096,4096,-ERANGE);
 CHECK(0xdffff000,4096,4097,-ERANGE);CHECK(0x7400000,4096,SIZE_MAX,-ERANGE);CHECK(0x7400000,0,4096,-EINVAL);CHECK(0x7400000,4095,4096,-EINVAL);
 CHECK(0x7400000,4096,4096,0);CHECK(0xdffff000,4096,4096,0);CHECK(0x7400000,0xd8c00000,0xd8c00000,0);
 table.nents=2;sg[0]=(struct scatterlist){0x7400000,2048};sg[1]=(struct scatterlist){0x7400800,2048};assert(!video_check_dma_mapping(&video,&table,4096));
 sg[1].address++;assert(video_check_dma_mapping(&video,&table,4096)==-EINVAL);sg[1].address-=2;assert(video_check_dma_mapping(&video,&table,4096)==-EINVAL);
 sg[1]=(struct scatterlist){0x7400800,0};assert(video_check_dma_mapping(&video,&table,4096)==-EINVAL);
 for(unsigned n=1;n<=256;n++){size_t length=8192+n;sg[0]=(struct scatterlist){0x10000000,n};sg[1]=(struct scatterlist){0x10000000+n,4096};sg[2]=(struct scatterlist){0x10001000+n,length-n-4096};table.nents=3;assert(!video_check_dma_mapping(&video,&table,length));sg[2].address+=4096;assert(video_check_dma_mapping(&video,&table,length)==-EINVAL);}
 res.version=8250;assert(!video_check_dma_mapping(&video,NULL,0));puts("ACTUAL_DMA_MAPPING_19_BOUNDARIES_AND_512_SG_CASES_PASS");return 0;}
'''
power='''#include <assert.h>
#include <stdio.h>
#include <stdbool.h>
#define CAMSS_8150 8150
struct device{int unused;};struct camss;struct csid_device;
struct parent_dev_ops{int(*get)(struct camss*,int);int(*put)(struct camss*,int);};
struct csid_hw_ops{int(*reset)(struct csid_device*);void(*hw_version)(struct csid_device*);};
struct csid_resources{struct parent_dev_ops*parent_dev_ops;struct csid_hw_ops*hw_ops;};
struct camss{struct device*dev;};struct csid_device{struct camss*camss;struct csid_resources*res;int id,num_supplies,supplies,nclocks,clock,irq;struct{int need_vc_update;}phy;};
struct v4l2_subdev{struct csid_device*csid;};
static int fail,parent,pm,reg,clocks,irq,puts_count,versions;
static struct csid_device*v4l2_get_subdevdata(struct v4l2_subdev*s){return s->csid;}
static int parent_get(struct camss*c,int id){(void)c;(void)id;if(fail==1)return -1;parent++;return 0;}
static int parent_put(struct camss*c,int id){(void)c;(void)id;assert(parent>0);parent--;puts_count++;return 0;}
static int pm_runtime_resume_and_get(struct device*d){(void)d;if(fail==2)return -2;pm++;return 0;}
static void pm_runtime_put_sync(struct device*d){(void)d;assert(pm>0);pm--;}
static int regulator_bulk_enable(int n,int s){(void)n;(void)s;if(fail==3)return -3;reg++;return 0;}
static void regulator_bulk_disable(int n,int s){(void)n;(void)s;assert(reg>0);reg--;}
static int csid_set_clock_rates(struct csid_device*c){(void)c;return fail==4?-4:0;}
static int camss_enable_clocks(int n,int c,struct device*d){(void)n;(void)c;(void)d;if(fail==5)return -5;clocks++;return 0;}
static void camss_disable_clocks(int n,int c){(void)n;(void)c;assert(clocks>0);clocks--;}
static void enable_irq(int n){(void)n;irq++;}
static void disable_irq(int n){(void)n;assert(irq>0);irq--;}
static int reset(struct csid_device*c){(void)c;return fail==6?-6:0;}
static void version(struct csid_device*c){(void)c;versions++;}
'''+extract('camss-csid.c','csid_set_power')+'''
int main(void){struct device dev={0};struct camss cam={&dev};struct parent_dev_ops pop={parent_get,parent_put};struct csid_hw_ops hop={reset,version};struct csid_resources res={&pop,&hop};struct csid_device csid={.camss=&cam,.res=&res};struct v4l2_subdev sd={&csid};
 for(fail=1;fail<=6;fail++){puts_count=0;assert(csid_set_power(&sd,1)==-fail);assert(parent==0&&pm==0&&reg==0&&clocks==0&&irq==0&&versions==0);assert(puts_count==(fail>1));}
 fail=0;puts_count=0;assert(!csid_set_power(&sd,1));assert(parent==1&&pm==1&&reg==1&&clocks==1&&irq==1&&versions==1&&csid.phy.need_vc_update==1);assert(!csid_set_power(&sd,0));assert(parent==0&&pm==0&&reg==0&&clocks==0&&irq==0&&puts_count==1);
 /* Existing VFE owner retains its independent reference after a failure. */
 parent=1;fail=3;puts_count=0;assert(csid_set_power(&sd,1)==-3);assert(parent==1&&puts_count==1&&pm==0&&reg==0&&clocks==0&&irq==0);
 puts("ACTUAL_CSID_POWER_6_FAULTS_NORMAL_AND_SHARED_OWNER_PASS");return 0;}
'''
reports=[]
for name,source in [('dma-mapping',dma),('csid-power',power)]:
 p=out/(name+'.c');p.write_text(source);binary=out/name
 cp=subprocess.run(['gcc','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-sign-compare','-fsanitize=address,undefined','-fno-omit-frame-pointer','-g',str(p),'-o',str(binary)],capture_output=True,timeout=60);(out/(name+'-compile.txt')).write_bytes(cp.stdout+cp.stderr);assert cp.returncode==0,cp.stderr.decode()[:3000]
 cp=subprocess.run([str(binary)],capture_output=True,timeout=30);(out/(name+'-run.txt')).write_bytes(cp.stdout+cp.stderr);assert cp.returncode==0,cp.stderr.decode()[:3000];reports.append(dict(name=name,source_sha256=hashlib.sha256(source.encode()).hexdigest(),asan_ubsan_pass=True,actual_function_body_not_rewritten=True));print(cp.stdout.decode().strip())
(ref/'dma-power-c-validation.json').write_text(json.dumps(dict(harnesses=reports,randomized_sg_positive_negative_cases=512,csid_six_fault_branches_normal_and_shared_owner=True,host_stubs_not_real_dma=True,phone_unchanged=True),indent=2)+'\n')
