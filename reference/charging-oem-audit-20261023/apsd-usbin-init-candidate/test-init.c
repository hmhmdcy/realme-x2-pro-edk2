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
static void stable(void){int old=writes;tick(1000);tick(1250);assert(writes==old&&d.state.running);tick(1500);}
static void restore(void){hw.raw[5]=hw.raw[2]=0;change_after_write=write_error=ignore_write=fail_at=0;assert(control("restore_saved")==13);tick(1500);tick(1750);tick(2000);assert(d.state.phase==UI_RESTORED&&!refs&&!d.state.pending_restore);}
static int groups;
static void done(const char *name){groups++;printf("ok: %s\n",name);}
static void test_default_and_commit(void)
{
 setup();assert(control("observe")==7&&!writes&&!refs&&!queued);
 assert(control("arm")==3&&refs==1&&d.state.running);stable();
 assert(writes==1&&hw.cfg==0x40&&d.state.phase==UI_CLEAR_VERIFIED&&d.state.old_bit==0x80&&d.state.pending_restore&&refs==1);
 int n=writes;assert(control("commit")==6&&writes==n&&!refs&&d.state.committed&&!d.state.pending_restore);
 assert(control("arm")==-EALREADY&&!refs);done("default observe; first anchor at 0/250/500ms; one-bit clear and zero-write commit");
}
static void test_nooff(void)
{
 setup();hw.raw[2]=0x10;hw.raw[4]=0x20;hw.raw[5]=0x21;assert(control("arm")==3);tick(1000);tick(1250);tick(61000);
 assert(!writes&&!refs&&d.state.phase==UI_TIMEOUT&&d.state.error==-ETIMEDOUT&&!d.state.old_valid);
 assert(control("commit")==-EPERM);done("no physical off timeout has zero writes and releases worker ref");
}
static void test_reset_evidence(void)
{
 setup();assert(control("arm")==3);tick(1000);tick(1250);hw.raw[6]^=2;tick(1500);assert(!writes&&d.state.first_ms==1500);
 tick(1750);assert(!writes);tick(2000);assert(writes==1);assert(control("commit")==6);
 setup();assert(control("arm")==3);tick(1000);hw.raw[5]=1;tick(1250);assert(!d.state.have_first);hw.raw[5]=0;tick(1500);tick(1750);assert(!writes);tick(2000);assert(writes==1);assert(control("commit")==6);
 done("any raw field change or physical-on discards prior off evidence");
}
static void test_prewrite_race(void)
{
 setup();assert(control("arm")==3);tick(1000);tick(1250);flip_read_at=27;tick(1500);
 assert(!writes&&d.state.running&&!d.state.have_first);assert(control("cancel")==6&&!refs);
 done("write-precheck sees reattachment and cannot reuse old stable evidence");
}
static void test_read_failure(void)
{
 setup();assert(control("arm")==3);tick(1000);fail_at=reads+1;tick(1250);
 assert(!writes&&!refs&&d.state.phase==UI_ERROR&&d.state.error==-EIO);done("read error terminates before write without stale off reuse");
}
static void test_write_errors(void)
{
 for(int kind=0;kind<5;kind++) {
  setup();assert(control("arm")==3);
  if(kind==0)write_error=-EIO;
  else if(kind==1)ignore_write=1;
  else change_after_write=kind-1;
  stable();assert(writes==1&&d.state.phase==UI_ERROR&&refs==1&&d.state.pending_restore&&d.state.unknown_write);
  assert(control("commit")==-EPERM&&refs==1);restore();
 }
 done("error-after-applied, ignored write, post-online, unmasked change, readback error retain owner");
}
static void test_post_raw_change(void)
{
 setup();change_after_write=4;assert(control("arm")==3);stable();
 assert(d.state.post_error==-EAGAIN&&d.state.unknown_write&&refs==1&&control("commit")==-EPERM);restore();
 done("postwrite raw change is an explicit failed/unknown result even while off");
}
static void test_restore_gate(void)
{
 setup();assert(control("restore_saved")==-ENOENT&&!refs);assert(control("arm")==3);stable();
 hw.raw[2]=0x10;assert(control("restore_saved")==13);tick(1500);tick(61500);
 assert(writes==1&&refs==1&&d.state.pending_restore&&d.state.phase==UI_TIMEOUT);
 assert(control("commit")==-EPERM);hw.raw[2]=0;now_ms=1000;assert(control("restore_saved")==13);stable();
 assert(writes==2&&hw.cfg==0xc0&&!refs&&!d.state.pending_restore);
 done("restore uses saved actual bit only after a new full off gate; no blind timeout restore");
}
static void test_old_zero(void)
{
 setup();hw.cfg=0x40;assert(control("arm")==3);stable();assert(!writes&&!refs&&d.state.old_valid&&!d.state.old_bit&&d.state.phase==UI_CLEAR_VERIFIED);
 assert(control("commit")==6&&!writes);assert(control("restore_saved")==-ENOENT);
 done("old bit already zero never causes a write or fabricated restore-one");
}
static void test_ref_cancel_stop(void)
{
 setup();going=true;assert(control("arm")==-ENODEV&&!d.state.running&&!refs&&!writes);
 going=false;assert(control("arm")==3);cancel_reentry=true;assert(control("cancel")==6&&!refs&&!queued&&!writes);
 setup();assert(control("arm")==3);ui_stop(&d);assert(d.paused&&!refs&&!queued&&!writes);
 setup();assert(control("arm")==3);stable();ui_stop(&d);assert(d.paused&&refs==1&&d.state.pending_restore&&writes==1);
 d.paused=false;assert(control("commit")==6&&!refs);done("try-get before scheduling; cancel join outside mutex; no auto restore on stop");
}
static void test_state_zero_io(void)
{
 setup();char buf[4096];int n=reads;assert(state_show(&dev,NULL,buf)>0&&reads==n&&!writes);
 assert(strstr(buf,"\"schema\":1")&&strstr(buf,"\"can_unload\":true"));
 assert(control("arm")==3);n=reads;assert(state_show(&dev,NULL,buf)>0&&reads==n&&strstr(buf,"\"remaining_ms\":60000"));
 assert(control("cancel")==6);printf("state: %s",buf);done("cached schema and current BOOTTIME remaining fields perform no register IO");
}
static void test_prewrite_deadline(void)
{
 setup();assert(control("arm")==3);tick(1000);tick(1250);delay_at=33;delay_ms=60000;tick(1500);
 assert(!writes&&!refs&&d.state.phase==UI_TIMEOUT&&d.state.error==-ETIMEDOUT);
 setup();assert(control("arm")==3);tick(1000);tick(1250);delay_at=33;delay_ms=251;tick(1500);
 assert(!writes&&!refs&&d.state.phase==UI_ERROR&&d.state.error==-EAGAIN);
 setup();assert(control("arm")==3);tick(1000);now_ms=999;ui_work(&d.work.work);
 assert(!writes&&!refs&&d.state.phase==UI_ERROR&&d.state.error==-EIO);
 done("actual prewrite clock rejects blocked read past deadline, stale off, or backward time");
}
int main(void)
{setbuf(stdout,NULL);test_default_and_commit();test_nooff();test_reset_evidence();test_prewrite_race();test_read_failure();test_write_errors();test_post_raw_change();test_restore_gate();test_old_zero();test_ref_cancel_stop();test_state_zero_io();test_prewrite_deadline();assert(groups==12);return 0;}
