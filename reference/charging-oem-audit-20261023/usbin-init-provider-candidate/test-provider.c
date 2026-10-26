/* Actual provider functions + frozen core; fake hardware and kernel boundary. */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>
#include "samurai-usb-input-decode.h"
#include "usbin-init-core.h"
struct regmap { int unused; };
struct mutex { int held; };
struct work_struct { int unused; };
struct delayed_work { struct work_struct work; };
struct device { void *data; };
struct device_attribute { int unused; };
struct power_supply { void *data; };
enum power_supply_usb_type { POWER_SUPPLY_USB_TYPE_UNKNOWN, POWER_SUPPLY_USB_TYPE_SDP,
 POWER_SUPPLY_USB_TYPE_CDP, POWER_SUPPLY_USB_TYPE_DCP, POWER_SUPPLY_USB_TYPE_C };
enum power_supply_property { POWER_SUPPLY_PROP_ONLINE, POWER_SUPPLY_PROP_USB_TYPE,
 POWER_SUPPLY_PROP_CURRENT_MAX, POWER_SUPPLY_PROP_INPUT_CURRENT_LIMIT };
union power_supply_propval { int intval; };
#include "tested-struct.inc"
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define container_of(p,t,m) ((t*)((char*)(p)-offsetof(t,m)))
#define to_delayed_work(p) container_of(p,struct delayed_work,work)
static bool usbin_init;
static bool native_ref_held,native_retained,dt_wired;
static int module_gets;
struct device_node { int unused; };
static struct device_node node;
#define THIS_MODULE ((void*)1)
static struct device_node *of_find_node_by_path(const char *p){assert(!strcmp(p,"/soc@0/usb@a6f8800/usb@a600000"));return dt_wired?&node:NULL;}
static int of_property_read_string(struct device_node *p,const char *key,const char **name){assert(p==&node&&!strcmp(key,"usb-psy-name"));*name="samurai-usb-input";return 0;}
static void of_node_put(struct device_node *p){}
static void __module_get(void *p){module_gets++;}
static void dev_info(struct device *p,const char *fmt,...){}
static void *system_wq;
static struct samurai_usb_input d;
static struct regmap map;
static struct device dev;
static struct power_supply psy;
static struct ui_snapshot hw;
static unsigned long long now_ms, delay_ms;
static int reads,cfg_reads,writes,fail_at,delay_at,ignore_write,write_error,post_change,cfg_flip_at;
static int scheduled,changed,cancelled,status_formats;
static unsigned int schedule_ms;
static void mutex_lock(struct mutex *m){assert(!m->held);m->held=1;}
static void mutex_unlock(struct mutex *m){assert(m->held);m->held=0;}
static unsigned long long ktime_get_boottime(void){return now_ms;}
static unsigned long long ktime_to_ms(unsigned long long t){return t;}
static void *dev_get_drvdata(struct device *p){return p->data;}
static void *power_supply_get_drvdata(struct power_supply *p){return p->data;}
static void power_supply_changed(struct power_supply *p){assert(p==&psy);changed++;}
static unsigned int msecs_to_jiffies(unsigned int ms){return ms;}
static int schedule_delayed_work(struct delayed_work *w,unsigned int ms){scheduled++;schedule_ms=ms;return 1;}
static int mod_delayed_work(void *q,struct delayed_work *w,unsigned int ms){scheduled++;schedule_ms=ms;return 1;}
static bool cancel_delayed_work_sync(struct delayed_work *w){assert(!d.lock.held);cancelled++;return true;}
/* Formatter deliberately does not interpret kernel-only %ph; private W=1
 * object compilation separately checks the actual kernel format contract. */
static ssize_t sysfs_emit(char *buf,const char *fmt,...){assert(d.lock.held);status_formats++;strcpy(buf,"cached\n");return 7;}
static int regmap_read(struct regmap *m,unsigned int reg,unsigned int *value)
{
 static const unsigned int regs[]={0x1307,0x1308,0x1310,0x1506,0x1509,0x150b,0x150d};
 assert(m==&map);reads++;
 if(reads==delay_at)now_ms+=delay_ms;
 if(reads==fail_at)return -EIO;
 if(reg==UI_CFG){assert(d.lock.held);cfg_reads++;if(cfg_reads==cfg_flip_at)hw.cfg^=0x40;*value=hw.cfg;return 0;}
 for(unsigned int i=0;i<7;i++)if(reg==regs[i]){*value=hw.raw[i];return 0;}
 assert(0&&"read outside fixed seven status fields and one config");return -EINVAL;
}
static int regmap_update_bits(struct regmap *m,unsigned int reg,unsigned int mask,unsigned int value)
{
 assert(m==&map&&d.lock.held&&reg==UI_CFG&&mask==UI_BIT&&value==0);writes++;
 if(!ignore_write)hw.cfg&=~mask;
 if(post_change==1)hw.raw[5]|=0x21;
 if(post_change==2)hw.cfg^=0x40;
 if(post_change==3)fail_at=reads+1;
 return write_error;
}
#include "tested-functions.inc"
static void setup(bool enabled,unsigned int cfg)
{
 memset(&d,0,sizeof(d));memset(&hw,0,sizeof(hw));d.map=&map;d.psy=&psy;psy.data=&d;dev.data=&d;
 hw.cfg=cfg;now_ms=1000;delay_ms=0;reads=cfg_reads=writes=fail_at=delay_at=ignore_write=write_error=post_change=cfg_flip_at=0;
 scheduled=changed=cancelled=status_formats=0;schedule_ms=0;usbin_init=enabled;
 native_ref_held=native_retained=false;dt_wired=true;module_gets=0;samurai_usb_retain_for_native_consumer(&dev);
 assert(native_ref_held&&native_retained&&module_gets==1);
}
static void online(unsigned int result)
{const unsigned char raw[]={0x11,result,0x10,8,0x23,0x2b,6};memcpy(hw.raw,raw,7);}
static void off(void){memset(hw.raw,0,7);}
static void step(unsigned long long ms){now_ms=ms;mutex_lock(&d.lock);samurai_usbin_step_locked(&d);mutex_unlock(&d.lock);}
static void poll(unsigned long long ms){now_ms=ms;samurai_usb_poll(&d.work.work);assert(!d.lock.held);}
static void prepare(void){mutex_lock(&d.lock);samurai_usbin_prepare(&d);mutex_unlock(&d.lock);assert(!d.lock.held);}
static void native(int ua){union power_supply_propval v={ua};assert(!samurai_usb_set_property(&psy,POWER_SUPPLY_PROP_INPUT_CURRENT_LIMIT,&v));}
static struct samurai_usb_budget budget(void){struct samurai_usb_budget b={0};assert(!samurai_usb_get_budget(&d,&b));return b;}
static void terminal_again(void)
{int n=writes;struct ui_state old=d.init;step(now_ms+100000);assert(writes==n&&!memcmp(&old,&d.init,sizeof(old)));}
static int groups;
static void done(const char *s){groups++;printf("ok: %s\n",s);}
static void test_disabled(void)
{
 setup(false,0xc0);prepare();assert(!reads&&d.init_stage==SUI_DISABLED);online(1);native(100000);poll(1000);
 assert(!cfg_reads&&!writes&&schedule_ms==1000&&d.init_stage==SUI_DISABLED);
 assert(budget().current_ua==100000);samurai_usb_suspend(&dev);samurai_usb_resume(&dev);poll(2000);assert(!cfg_reads&&!writes);
 done("default disabled: no config IO, original source/native and 1000ms cadence");
}
static void test_native_lifetime(void)
{
 setup(true,0xc0);native_ref_held=native_retained=false;dt_wired=false;module_gets=0;
 samurai_usb_retain_for_native_consumer(&dev);prepare();assert(!native_ref_held&&!module_gets&&!reads&&!writes&&d.init.error==-ENODEV);
 terminal_again();
 setup(true,0xc0);native_ref_held=false;native_retained=true;module_gets=0;
 samurai_usb_retain_for_native_consumer(&dev);prepare();assert(!native_ref_held&&!module_gets&&!reads&&!writes&&d.init.error==-ENODEV);
 terminal_again();
 setup(true,0xc0);prepare();step(1000);step(2000);assert(writes==1&&native_ref_held&&module_gets==1);
 done("native lifecycle: actual retained ref required; absent wiring and preset parameter cannot authorize IO");
}
static void test_probe(void)
{
 setup(true,0x40);prepare();assert(cfg_reads==2&&!writes&&d.init_stage==SUI_PROBE_ZERO&&!d.init.clear_used);
 poll(1000);samurai_usb_suspend(&dev);samurai_usb_resume(&dev);poll(2000);assert(cfg_reads==2&&!writes);
 setup(true,0xc0);fail_at=1;prepare();assert(d.init_stage==SUI_TERMINAL&&d.init_probe_error==-EIO);terminal_again();
 setup(true,0xc0);cfg_flip_at=2;prepare();assert(d.init_probe_error==-EAGAIN&&d.init_stage==SUI_TERMINAL);terminal_again();
 done("probe already-zero and read-error/change: zero writes, immutable terminal history");
}
static void test_wait_pm(void)
{
 setup(true,0xc0);online(1);prepare();poll(1000);poll(1000000);
 assert(d.init_stage==SUI_WAIT_FIRST_OFF&&!d.init.clear_used&&!d.init.deadline_ms&&!writes);
 samurai_usb_suspend(&dev);int r=reads;step(1000001);assert(reads==r&&cancelled==1);
 samurai_usb_resume(&dev);poll(2000000);assert(d.init_stage==SUI_WAIT_FIRST_OFF&&!d.init.clear_used);
 off();poll(2001000);assert(d.init.running&&d.init.started_ms==2001000&&d.init.first_ms==2001000);
 poll(2002000);assert(d.init_stage==SUI_INITIALIZED&&writes==1&&hw.cfg==0x40&&d.init.committed);
 done("unarmed wait survives ordinary PM, starts once only after new physical-off sample");
}
static void test_success(void)
{
 setup(true,0xc5);prepare();poll(1000);assert(d.init_stage==SUI_TRANSACTION&&!writes&&d.init.off_samples==1);
 poll(2000);assert(writes==1&&hw.cfg==0x45&&d.init_stage==SUI_INITIALIZED);
 assert(d.init.old_valid&&d.init.old_bit==0x80&&d.init.changed&&d.init.write_attempted);
 assert(!d.init.write_return&&!d.init.readback_error&&!d.init.post_error&&!d.init.pending_restore&&d.init.committed);
 assert(d.init.prewrite_ms==2000&&d.init.first_ms==1000&&d.init.off_samples==2);
 struct ui_state saved=d.init;online(1);native(100000);poll(3000);samurai_usb_suspend(&dev);samurai_usb_resume(&dev);poll(4000);
 assert(writes==1&&!memcmp(&saved,&d.init,sizeof(saved)));assert(budget().current_ua<0); /* resume invalidated native */
 done("actual worker integration: unchanged bits, one write, automatic zero-IO commit, persistent receipt");
}
static void test_fresh_anchor(void)
{
 setup(true,0xc0);prepare();step(1000);step(1250);assert(d.init.first_ms==1000&&d.init.off_samples==2&&!writes);
 hw.raw[0]^=1;step(1500);assert(d.init.first_ms==1500&&d.init.off_samples==1&&!writes);
 step(2000);assert(writes==1&&d.init_stage==SUI_INITIALIZED);
 setup(true,0xc0);prepare();step(1000);online(1);step(2000);assert(!d.init.have_first&&!writes);
 off();step(3000);assert(d.init.first_ms==3000);step(4000);assert(writes==1);
 done("first-off anchor, every-field change and reconnect reset stable evidence");
}
static void test_active_pm(void)
{
 setup(true,0xc0);prepare();poll(1000);unsigned long long deadline=d.init.deadline_ms;
 samurai_usb_suspend(&dev);assert(d.init_stage==SUI_TERMINAL&&d.init.phase==UI_CANCELLED&&d.init.error==-ECANCELED);
 assert(d.init.deadline_ms==deadline&&!d.init.running&&!writes&&cancelled==1);
 samurai_usb_resume(&dev);poll(2000);terminal_again();assert(!writes&&d.init.deadline_ms==deadline);
 done("started transaction PM: cancel/join without held mutex, deadline retained, no resume rearm");
}
static void test_deadline(void)
{
 setup(true,0xc0);prepare();step(1000);step(61000);assert(d.init.phase==UI_TIMEOUT&&!writes);terminal_again();
 setup(true,0xc0);prepare();step(1000);
 /* Second step reads sample(8), pre(8), then config; make that config block. */
 delay_at=reads+17;delay_ms=60000;step(2000);assert(d.init.phase==UI_TIMEOUT&&!writes&&d.init.prewrite_ms==62000);terminal_again();
 setup(true,0xc0);prepare();step(1000);delay_at=reads+17;delay_ms=251;step(2000);
 assert(d.init.error==-EAGAIN&&!writes&&d.init.prewrite_ms==2251);terminal_again();
 done("deadline and fresh-prewrite gates survive blocking config, no new write after expiry");
}
static void test_failures(void)
{
 for(int mode=0;mode<5;mode++){
  setup(true,0xc0);prepare();step(1000);
  if(mode==0)ignore_write=1;
  if(mode==1)write_error=-EIO;
  if(mode>=2)post_change=mode-1;
  step(2000);assert(writes==1&&d.init_stage==SUI_TERMINAL&&d.init.unknown_write&&d.init.pending_restore);
  assert(!d.init.committed&&d.init.old_valid&&d.init.old_bit==UI_BIT);terminal_again();
  unsigned long long deadline=d.init.deadline_ms;samurai_usb_suspend(&dev);samurai_usb_resume(&dev);
  assert(d.init.deadline_ms==deadline&&d.init.unknown_write);terminal_again();
 }
 setup(true,0xc0);prepare();online(1);fail_at=reads+1;step(1000);
 assert(d.init_stage==SUI_TERMINAL&&!d.init.clear_used&&d.init.error==-EIO&&!writes);terminal_again();
 done("ignored/error writes, post-on/config-change/read-error remain unknown; wait read error is terminal");
}
static void test_budget_and_status(void)
{
 setup(true,0xc0);prepare();step(1000);ignore_write=1;step(2000);assert(d.init.unknown_write);
 const struct ui_state old=d.init;int n=writes;
 online(1);native(100000);struct samurai_usb_budget b=budget();assert(b.kind==SAMURAI_USB_SDP&&b.current_ua==100000);
 native(500000);b=budget();assert(b.current_ua==500000);
 online(0x10);native(100000);b=budget();assert(b.kind==SAMURAI_USB_SDP&&b.current_ua==100000);
 online(4);b=budget();assert(b.kind==SAMURAI_USB_CDP&&b.current_ua==1500000);
 union power_supply_propval v;assert(!samurai_usb_get_property(&psy,POWER_SUPPLY_PROP_CURRENT_MAX,&v)&&v.intval==1500000);
 assert(writes==n&&!memcmp(&old,&d.init,sizeof(old)));
 char buf[4096];int nr=reads;assert(usbin_init_state_show(&dev,NULL,buf)==7&&status_formats==1&&reads==nr&&writes==n);
 assert(!memcmp(&old,&d.init,sizeof(old)));
 done("unknown-init history never changes SDP/FLOAT/CDP/native budget; getters/status cannot write or advance");
}
int main(void)
{
 test_disabled();test_native_lifetime();test_probe();test_wait_pm();test_success();test_fresh_anchor();test_active_pm();test_deadline();test_failures();test_budget_and_status();
 assert(groups==10);printf("groups: %d\n",groups);return 0;
}
