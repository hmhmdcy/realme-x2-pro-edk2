#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <sys/types.h>
typedef unsigned char u8;
struct device {void *data;};struct device_attribute {};struct platform_device {struct device dev;};
struct iommu_group {};struct device_node {};struct firmware {int unused;};
struct camss_a5 {
 struct device *dev;int lock;
 struct {unsigned enabled_groups,held_domains;} resources;
 struct {void *cpu;unsigned bytes,mapped;} firmware;
 bool power_held,cpu_enabled,irq_enabled,reset_asserted,initialized,cpu_release_attempted;
 bool init_done,ping_done,pc_done;
 unsigned interrupts,messages,watchdogs,protocol_errors;
 int cleanup_error,pc_error;
 void (*failure_snapshot)(struct camss_a5 *a);
};
#define GFP_KERNEL 0
#define THIS_MODULE ((void *)1)
#define READ_ONCE(x) (x)
#define dev_info(...) ((void)0)
#define dev_err_probe(dev,e,...) ((void)(dev),(e))
static struct camss_a5 *device_a5,*allocated;
static int test_lock,test_error;
static bool finished=true,pinned,held_failure,bound_seen=true,hold_start_failure=true;
static const u8 *snapshot_boot_code;
static const char *phase="ready";
static unsigned group_devices,requests,releases,starts,pings,stops,updates,pm_enables,gets,put_calls,refs;
static int scenario;static bool get_ok=true;
static void mutex_lock(int *l){assert(!*l);*l=1;}
static void mutex_unlock(int *l){assert(*l);*l=0;}
static bool sysfs_streq(const char *a,const char *b){return !strcmp(a,b);}
static bool try_module_get(void *m){assert(m==THIS_MODULE);if(!get_ok)return false;++gets;++refs;return true;}
static void __module_get(void *m){assert(m==THIS_MODULE);++gets;++refs;}
static void module_put(void *m){assert(m==THIS_MODULE && refs);++put_calls;--refs;}
static void *dev_get_drvdata(struct device *d){return d->data;}
static bool camss_a5_backing_owned(const struct camss_a5 *a){return a->firmware.cpu!=NULL;}
static void update_result(void){++updates;}
static int request_firmware_direct(const struct firmware **f,const char *n,struct device *d){(void)n;(void)d;++requests;static struct firmware fw;*f=&fw;return scenario==2?-ENOENT:0;}
static void release_firmware(const struct firmware *f){assert(f);++releases;}
static int configure_snapshot(struct camss_a5 *a,const struct firmware *f){(void)a;assert(f);return scenario==3?-EINVAL:0;}
static int camss_a5_start(struct camss_a5 *a,const struct firmware *f){assert(f && bound_seen && test_lock);++starts;
 a->power_held=true;a->cpu_release_attempted=true;a->firmware.cpu=(void *)1;a->firmware.bytes=a->firmware.mapped=64;a->resources.enabled_groups=a->resources.held_domains=7;
 if(scenario==4||scenario==7){a->reset_asserted=true;return -EIO;}
 a->cpu_enabled=a->irq_enabled=a->initialized=a->init_done=true;return 0;
}
static int camss_a5_ping(struct camss_a5 *a,uint64_t cookie){(void)cookie;++pings;assert(a->initialized);if(scenario==6)return -EPROTO;a->ping_done=true;return 0;}
static int camss_a5_stop(struct camss_a5 *a){++stops;a->cpu_enabled=a->irq_enabled=false;a->reset_asserted=true;if(scenario==5){a->cleanup_error=-EIO;return -EIO;}
 a->pc_done=a->initialized;a->initialized=false;a->firmware.cpu=NULL;a->firmware.mapped=0;a->power_held=false;a->resources.enabled_groups=a->resources.held_domains=0;a->interrupts=a->messages=3;return 0;
}
static void *devm_kzalloc(struct device *d,size_t n,int flags){(void)d;(void)flags;allocated=calloc(1,n);return allocated;}
static struct iommu_group *iommu_group_get(struct device *d){(void)d;static struct iommu_group g;return &g;}
static int iommu_group_for_each_dev(struct iommu_group *g,void *target,int (*cb)(struct device *,void *)){(void)g;if(scenario==22)return -EBUSY;return cb(target,target);}
static void iommu_group_put(struct iommu_group *g){(void)g;}
static struct device_node *of_parse_phandle(void *n,const char *name,int i){(void)n;(void)name;(void)i;static struct device_node node;return scenario==21?NULL:&node;}
static int of_property_present(struct device_node *n,const char *name){(void)n;(void)name;return 1;}
static void of_node_put(struct device_node *n){(void)n;}
static int camss_a5_init(struct platform_device *p,struct camss_a5 *a){a->dev=&p->dev;return scenario==23?-EIO:0;}
static void platform_set_drvdata(struct platform_device *p,void *a){p->dev.data=a;}
static void pm_runtime_set_suspended(struct device *d){(void)d;}
static void pm_runtime_enable(struct device *d){(void)d;++pm_enables;}
static void run_locked(struct device *dev);
#include "owner-bodies.inc"
int main(int argc,char **argv)
{
 assert(argc==2);scenario=atoi(argv[1]);struct platform_device p={0};struct camss_a5 a={.dev=&p.dev};p.dev.data=&a;device_a5=&a;
 if(scenario>=20){device_a5=NULL;finished=false;int ret=boot_test_probe(&p);assert(!test_lock && !requests && !starts && !pings && !stops);
  assert(ret==(scenario==20?0:scenario==21?-ENXIO:scenario==22?-EBUSY:-EIO));
  if(scenario==20)assert(finished && !strcmp(phase,"ready") && device_a5==allocated && pm_enables==1 && !test_error);
  else assert(!pm_enables);free(allocated);return 0;
 }
 if(scenario==1)bound_seen=false;
 if(scenario==7)hold_start_failure=false;
 if(scenario==8)a.resources.held_domains=1;
 if(scenario==9)finished=false;
 if(scenario==10)get_ok=false;
 if(scenario==13)device_a5=NULL;
 if(scenario==14)p.dev.data=NULL;
 ssize_t ret=run_store(&p.dev,NULL,scenario==11?"0":"1",1);
 bool rejected=scenario==1||scenario==8||scenario==9||scenario==10||scenario==11||scenario==13||scenario==14;
 assert(!test_lock);
 if(rejected){assert(ret==(scenario==10?-ENODEV:scenario==11?-EINVAL:-EBUSY) && !requests && !starts && !stops && !refs);return 0;}
 assert(ret==1 && finished && requests==1);
 assert(releases==(scenario==2?0U:1U));assert(starts==((scenario==2||scenario==3)?0U:1U));
 assert(pings==((scenario==2||scenario==3||scenario==4||scenario==7)?0U:1U));
 assert(stops==(scenario==4?0U:1U));assert(pinned==(scenario==4||scenario==5));assert(refs==(unsigned)pinned);
 int error=scenario==2?-ENOENT:scenario==3?-EINVAL:scenario==4||scenario==5||scenario==7?-EIO:scenario==6?-EPROTO:0;
 assert(test_error==error);
 if(scenario==4){assert(held_failure && !strcmp(phase,"failed-held"));assert(run_store(&p.dev,NULL,"1",1)==-EBUSY && requests==1 && starts==1);}
 if(scenario==12){assert(!pinned && !refs);assert(run_store(&p.dev,NULL,"1",1)==1 && starts==2 && requests==2 && !test_error && !refs);}
 return 0;
}
