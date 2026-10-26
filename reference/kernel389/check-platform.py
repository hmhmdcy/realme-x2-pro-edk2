"""Run the actual platform probe/group/PM/remove paths against failure providers."""
from pathlib import Path
import json,re,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;s=(HERE/'camss-icp-platform.c').read_text()
def block(pattern):
 m=re.search(pattern,s);assert m,pattern;start=s.index('{',m.start());level=1;end=start+1
 while level:
  level+=(s[end]=='{')-(s[end]=='}');end+=1
 return s[m.start():end]+'\n'
prefix=r'''
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#define GFP_KERNEL 0
#define ICP_FIRMWARE "qcom/sm8150/camera-icp.elf"
#define WARN_ON(x) (x)
#define IS_ERR(x) ((uintptr_t)(x)>=(uintptr_t)-4095)
#define PTR_ERR(x) ((int)(intptr_t)(x))
#ifdef BUILTIN_TEST
#define THIS_MODULE NULL
#define BUILTIN_VALUE 1
#else
static int owner;
#define THIS_MODULE (&owner)
#define BUILTIN_VALUE 0
#endif
struct device {void *data,*of_node;};struct platform_device {struct device dev;};
struct mutex {unsigned depth;};
static void mutex_init(struct mutex *m){m->depth=0;}
static void mutex_lock(struct mutex *m){assert(m->depth++==0);}
static void mutex_unlock(struct mutex *m){assert(--m->depth==0);}
struct camss_a5_resources {unsigned enabled_groups,held_domains;};
struct camss_a5 {struct camss_a5_resources resources;bool engine_dma_capable;};
struct camss_a5_m2m {unsigned unused;};
struct iommu_group {unsigned unused;};
static struct iommu_group group;
static struct camss_a5_m2m endpoint;
static struct device other;
static int group_mode,allocation_fail,init_error,engine=1,property_error,property_empty,registration_error;
static unsigned group_refs,pm_enabled,suspended,inited,registered,resources_released,resume_calls,suspend_calls,firmware_requests;
static char firmware_used[128];
static void *allocated;
static void *devm_kzalloc(struct device *d,size_t bytes,int g){(void)d;(void)g;allocated=allocation_fail?NULL:calloc(1,bytes);return allocated;}
static struct iommu_group *iommu_group_get(struct device *d){(void)d;if(group_mode==1)return NULL;++group_refs;return &group;}
static void iommu_group_put(struct iommu_group *g){assert(g==&group && group_refs);--group_refs;}
static int iommu_group_for_each_dev(struct iommu_group *g,void *data,int (*cb)(struct device *,void *));
static bool device_is_bound(struct device *d){return d->data!=NULL;}
static void *dev_get_drvdata(struct device *d){return d->data;}
static void platform_set_drvdata(struct platform_device *p,void *v){p->dev.data=v;}
static void *platform_get_drvdata(struct platform_device *p){return p->dev.data;}
static int dev_err_probe(struct device *d,int error,const char *text){(void)d;(void)text;return error;}
static void dev_info(struct device *d,const char *text){(void)d;(void)text;}
static int camss_a5_init(struct platform_device *p,struct camss_a5 *a){(void)p;++inited;a->engine_dma_capable=engine;return init_error;}
static int of_property_read_string(void *node,const char *key,const char **value){(void)node;assert(!strcmp(key,"firmware-name"));if(property_error)return property_error;*value=property_empty?"":"qcom/sm8150/board-camera.elf";return 0;}
static void pm_runtime_set_suspended(struct device *d){(void)d;++suspended;}
static void pm_runtime_enable(struct device *d){(void)d;assert(!pm_enabled);++pm_enabled;}
static void pm_runtime_disable(struct device *d){(void)d;assert(pm_enabled);--pm_enabled;}
static struct camss_a5_m2m *camss_a5_m2m_register(struct camss_a5 *a,void *o,const char *f,bool (*bound)(struct device *)){
 assert(a->engine_dma_capable && o==THIS_MODULE && bound==device_is_bound && pm_enabled);++registered;strcpy(firmware_used,f);
 return registration_error?(void *)(intptr_t)registration_error:&endpoint;
}
static int camss_a5_resources_release(struct camss_a5_resources *r){assert(!r->enabled_groups && !r->held_domains);++resources_released;return 0;}
static int camss_a5_m2m_unregister(struct camss_a5_m2m *p){assert(p==&endpoint);return 0;}
static int camss_a5_runtime_resume(struct camss_a5 *a){++resume_calls;a->resources.enabled_groups=a->resources.held_domains=1;return 0;}
static int camss_a5_runtime_suspend(struct camss_a5 *a){++suspend_calls;a->resources.enabled_groups=a->resources.held_domains=0;return 0;}
'''
actual=block(r'struct camss_icp \{')+';\n'+block(r'struct icp_group_check \{')+';\n'
actual+=block(r'static int check_group_device\(')+block(r'static int check_dma_group\(')
iterator=r'''
static int iommu_group_for_each_dev(struct iommu_group *g,void *data,int (*cb)(struct device *,void *)){
 assert(g==&group);struct icp_group_check *c=data;if(group_mode==2)return cb(&other,data);if(group_mode==3)return 0;
 int ret=cb(c->owner,data);return ret?ret:(group_mode==4?cb(&other,data):0);
}
'''
actual+=iterator+block(r'static int icp_runtime_resume\(')+block(r'static int icp_runtime_suspend\(')+block(r'static int camss_icp_probe\(')+block(r'static void camss_icp_remove\(')
cases=r'''
int main(void){unsigned cases=0;
 for(int i=0;i<13;i++){
  struct platform_device p={0};allocated=NULL;group_mode=allocation_fail=init_error=property_error=property_empty=registration_error=0;engine=1;
  group_refs=pm_enabled=suspended=inited=registered=resources_released=resume_calls=suspend_calls=0;firmware_used[0]=0;
  int expected=0;
  if(i>=1 && i<=4){group_mode=i;expected=i==1?-ENODEV:-EBUSY;}
  if(i==5){allocation_fail=1;expected=-ENOMEM;}
  if(i==6){init_error=-EIO;expected=-EIO;}
  if(i==7){engine=0;expected=-EINVAL;}
  if(i==8){property_error=-EILSEQ;expected=-EILSEQ;}
  if(i==9){registration_error=-ENOMEM;expected=-ENOMEM;}
  if(i==10)property_error=-EINVAL;
  if(i==12){property_empty=1;expected=-EINVAL;}
  int ret=camss_icp_probe(&p);assert(ret==expected && !group_refs);
  if(!ret){
   assert(pm_enabled && suspended==1 && registered==1 && !firmware_requests);
   assert(!strcmp(firmware_used,i==10?ICP_FIRMWARE:"qcom/sm8150/board-camera.elf"));
   assert(!icp_runtime_resume(&p.dev) && resume_calls==1);
   if(i!=11)assert(!icp_runtime_suspend(&p.dev) && suspend_calls==1);
   camss_icp_remove(&p);assert(!pm_enabled && resources_released==1 && suspend_calls==1);
  }else{
   assert(!pm_enabled);
   if(i==9)assert(resources_released==1 && registered==1);
  }
  free(allocated);++cases;
 }
 printf("PLATFORM_MODEL cases=%u builtin=%d passed=1\n",cases,BUILTIN_VALUE);return 0;
}
'''
model=P/'platform-model.c';model.write_text(prefix+actual+cases);results=[]
for builtin in [False,True]:
 binary=P/('platform-model-builtin' if builtin else 'platform-model-module')
 command=['cc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-no-pie']+(['-DBUILTIN_TEST'] if builtin else [])+[str(model),'-o',str(binary)]
 q=subprocess.run(command,capture_output=True);(P/(binary.name+'-build.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-3000:]
 q=subprocess.run([str(binary)],capture_output=True);(P/(binary.name+'-run.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-3000:]
 assert re.fullmatch(rb'PLATFORM_MODEL cases=13 builtin=[01] passed=1\n',q.stdout);results.append(q.stdout.decode().strip())
report=dict(stage=389,actual_platform_probe_group_pm_and_remove_functions=True,cases=26,asan_ubsan=True,missing_or_shared_iommu_group_rejected=True,failed_registration_disables_pm_and_releases_resources=True,firmware_dt_and_default_paths_checked=True,empty_firmware_name_rejected=True,no_firmware_start_in_probe=True,module_and_builtin_owner_arguments_checked=True,driver_core_resume_before_remove_modelled=True,providers_not_real_hardware_or_kernel_concurrency=True,passed=True)
(HERE/'platform-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
