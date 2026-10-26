#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <sys/types.h>
struct file {};struct bin_attribute {};struct kobject {};
struct device {struct kobject kobj;void *data;};
struct camss_a5 {
 int lock;
 bool cpu_enabled,irq_enabled,reset_asserted,power_held;
 struct {void *cpu;unsigned mapped,bytes;} firmware;
};
static struct camss_a5 *device_a5;
static bool held_failure;
static int test_lock,barriers;
#define kobj_to_dev(k) ((struct device *)(k))
#define dev_get_drvdata(d) ((d)->data)
#define min_t(type,a,b) ((type)(a)<(type)(b)?(type)(a):(type)(b))
static void mutex_lock(int *l) {assert(!*l);*l=1;}
static void mutex_unlock(int *l) {assert(*l);*l=0;}
static void dma_rmb(void) {++barriers;}
#include "body.inc"
int main(int argc,char **argv)
{
 assert(argc==2);int scenario=atoi(argv[1]);char backing[64],out[80];
 memset(backing,0x5a,sizeof(backing));memset(out,0x7b,sizeof(out));
 struct camss_a5 a={.reset_asserted=true,.power_held=true,.firmware={backing,64,64}};
 struct device dev={.data=&a};device_a5=&a;held_failure=true;
 loff_t offset=0;size_t count=sizeof(out);ssize_t expected=64;
 switch(scenario){
 case 1:offset=63;expected=1;break;
 case 2:offset=64;expected=0;break;
 case 3:offset=INT64_MAX;expected=0;break;
 case 4:offset=-1;expected=-EINVAL;break;
 case 5:held_failure=false;expected=-ENODATA;break;
 case 6:device_a5=NULL;expected=-ENODATA;break;
 case 7:dev.data=NULL;expected=-ENODATA;break;
 case 8:a.cpu_enabled=true;expected=-ENODATA;break;
 case 9:a.irq_enabled=true;expected=-ENODATA;break;
 case 10:a.reset_asserted=false;expected=-ENODATA;break;
 case 11:a.power_held=false;expected=-ENODATA;break;
 case 12:a.firmware.cpu=NULL;expected=-ENODATA;break;
 case 13:a.firmware.mapped=63;expected=-ENODATA;break;
 case 14:count=0;expected=0;break;
 }
 assert(firmware_read(NULL,&dev.kobj,NULL,out,offset,count)==expected);
 assert(!test_lock && !a.lock);
 if(expected>0){assert(barriers==1);for(ssize_t i=0;i<expected;i++)assert(out[i]==0x5a);}
 else assert(!barriers || scenario==14);
 for(size_t i=expected>0?(size_t)expected:0;i<sizeof(out);i++)assert(out[i]==0x7b);
 puts("A5_OWNED_FIRMWARE_SNAPSHOT_PASS");
}
