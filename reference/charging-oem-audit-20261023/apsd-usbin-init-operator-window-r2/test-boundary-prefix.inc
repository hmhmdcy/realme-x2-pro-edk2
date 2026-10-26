/* Real core and complete module functions; fake regmap/workqueue/module OS. */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <sys/types.h>
#include "usbin-init-core.h"
typedef unsigned long long u64;
struct regmap {int dummy;};struct mutex {int held;};
struct work_struct {int dummy;};struct delayed_work {struct work_struct work;};
struct device {void *data;};struct device_attribute {int dummy;};
#include "tested-struct.inc"
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define THIS_MODULE ((void*)1)
#define container_of(p,t,m) ((t*)((char*)(p)-offsetof(t,m)))
#define to_delayed_work(p) container_of(p,struct delayed_work,work)
static struct ui_device d;
static struct device dev;
static struct regmap map;
static struct ui_snapshot hw;
static unsigned long long now_ms;
static int refs,gets,put_count,reads,writes,fail_at,write_error,ignore_write,change_after_write,flip_read_at,delay_at;
static unsigned long long delay_ms;
static bool going,queued,cancel_reentry;
static void mutex_lock(struct mutex *m){assert(!m->held);m->held=1;}
static void mutex_unlock(struct mutex *m){assert(m->held);m->held=0;}
static unsigned long long ktime_get_boottime(void){return now_ms;}
static unsigned long long ktime_to_ms(unsigned long long t){return t;}
static void *dev_get_drvdata(struct device *p){return p->data;}
static bool try_module_get(void *m){gets++;if(going)return false;refs++;return true;}
static void module_put(void *m){assert(refs>0&&!d.lock.held);refs--;put_count++;}
static unsigned int msecs_to_jiffies(unsigned int ms){return ms;}
static int schedule_delayed_work(struct delayed_work *w,unsigned int delay){queued=true;return 1;}
static ssize_t control_store(struct device*,struct device_attribute*,const char*,size_t);
static bool cancel_delayed_work_sync(struct delayed_work *w)
{assert(!d.lock.held);queued=false;if(cancel_reentry){cancel_reentry=false;assert(control_store(&dev,NULL,"restore_saved",13)==-EBUSY);}return true;}
static bool sysfs_streq(const char *a,const char *b){size_t n=strlen(a);if(n&&a[n-1]=='\n')n--;return strlen(b)==n&&!memcmp(a,b,n);}
static int sysfs_emit(char *buf,const char *fmt,...){va_list args;va_start(args,fmt);int n=vsnprintf(buf,4096,fmt,args);va_end(args);return n;}
static int regmap_read(struct regmap *m,unsigned int reg,unsigned int *value)
{
 static const unsigned int regs[]={0x1307,0x1308,0x1310,0x1506,0x1509,0x150b,0x150d};
 assert(m==&map);reads++;if(reads==fail_at)return -EIO;
 if(reads==delay_at)now_ms+=delay_ms;
 if(reads==flip_read_at)hw.raw[2]|=0x10;
 if(reg==UI_CFG){*value=hw.cfg;return 0;}
 for(unsigned int i=0;i<7;i++)if(reg==regs[i]){*value=hw.raw[i];return 0;}
 assert(0&&"unapproved register read");return -EINVAL;
}
static int regmap_update_bits(struct regmap *m,unsigned int reg,unsigned int mask,unsigned int value)
{
 assert(m==&map&&reg==0x1358&&mask==0x80&&!(value&~0x80));writes++;
 if(!ignore_write)hw.cfg=(hw.cfg&~mask)|(value&mask);
 if(change_after_write==1)hw.raw[5]|=0x21;
 if(change_after_write==2)hw.cfg^=0x40;
 if(change_after_write==3)fail_at=reads+1;
 if(change_after_write==4)hw.raw[0]^=1;
 return write_error;
}
#include "tested-functions.inc"
static void setup(void)
{
 memset(&d,0,sizeof(d));memset(&hw,0,sizeof(hw));dev.data=&d;d.map=&map;
 d.io=(struct ui_ops){&d,ui_snapshot_read,ui_config_read,ui_bit_write,ui_clock};d.instance=0x1234;
 hw.cfg=0xc0;now_ms=1000;refs=gets=put_count=reads=writes=fail_at=write_error=ignore_write=change_after_write=flip_read_at=delay_at=0;delay_ms=0;
 going=queued=cancel_reentry=false;
}
static int control(const char *s){return control_store(&dev,NULL,s,strlen(s));}
static void tick(unsigned int ms){now_ms=ms;queued=false;ui_work(&d.work.work);}
