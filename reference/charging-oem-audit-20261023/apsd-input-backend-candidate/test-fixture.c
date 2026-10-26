#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
typedef uint64_t u64;
typedef uint8_t u8;
#define IS_ENABLED(x) 1
#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))
#define BIT(n) (1U<<(n))
#define dev_warn(...) ((void)0)
struct device {void *data;};
struct mutex {bool held;};
static void mutex_lock(struct mutex *m) {assert(!m->held);m->held=true;}
static void mutex_unlock(struct mutex *m) {assert(m->held);m->held=false;}
struct work_struct {int unused;};
struct delayed_work {bool pending;};
struct power_supply {int unused;};
static bool apsd_backend;
static int queue_count,cancel_count;
static int system_wq;
static void mod_delayed_work(int q,struct delayed_work *w,int delay)
{queue_count++;w->pending=true;}
static void cancel_delayed_work_sync(struct delayed_work *w)
{cancel_count++;w->pending=false;}
static void *dev_get_drvdata(struct device *d) {return d->data;}
/* ACTUAL_API */
/* ACTUAL_DECODE */
struct regmap {
 struct mutex *lock;
 struct samurai_usb_status snapshots[2];
 unsigned int reads,base_calls,writes,fail_read_at;
 int read_error,transfer_error;
 unsigned int command;
};
static const unsigned int expected_addresses[]={0x1307,0x1308,0x1310,0x1506,0x1509,0x150b,0x150d};
static int regmap_read(struct regmap *map,unsigned int reg,unsigned int *value)
{
 unsigned int i=map->reads++;
 assert(map->lock->held);assert(i<14);assert(reg==expected_addresses[i%7]);
 if(map->read_error && i==map->fail_read_at)return map->read_error;
 const unsigned char *raw=(const unsigned char *)&map->snapshots[i/7];
 _Static_assert(sizeof(struct samurai_usb_status)==7,"fixture must match seven actual bytes");
 *value=raw[i%7];return 0;
}
static int regmap_update_bits_base(struct regmap *map,unsigned int reg,
 unsigned int mask,unsigned int val,bool *change,bool async,bool force)
{
 assert(map->lock->held);assert(reg==0x1341&&mask==1&&val==1&&!change&&!async&&force);
 map->base_calls++;
 if(map->transfer_error)return map->transfer_error;
 map->writes++;map->command=(map->command&~mask)|(val&mask);return 0;
}
/* ACTUAL_REGMAP_INLINE */
/* ACTUAL_FUNCTIONS */
static struct samurai_usb_input input;
static struct regmap map;
static struct device device;
static int registration_count,unregistration_count,registration_error;
static bool late_callbacks;
static int late_read_error,late_write_error;
int samurai_apsd_bus_register(struct device *dev,const struct samurai_apsd_bus_ops *ops,void *ctx)
{
 assert(dev==&device&&ctx==&input);assert(!input.lock.held);assert(!input.paused&&!input.apsd_joining);
 assert(ops->read_sample==samurai_usb_apsd_read&&ops->rerun_once==samurai_usb_apsd_rerun);
 registration_count++;return registration_error;
}
void samurai_apsd_bus_unregister(struct device *dev,void *ctx)
{
 assert(dev==&device&&ctx==&input);assert(!input.lock.held);
 assert(input.apsd_joining&&!input.apsd_registered);unregistration_count++;
 if(late_callbacks) {
  struct samurai_apsd_bus_sample sample;
  unsigned int r=map.reads,w=map.base_calls;
  late_read_error=samurai_usb_apsd_read(ctx,&sample);
  late_write_error=samurai_usb_apsd_rerun(ctx,input.apsd_attempt_epoch+1);
  assert(map.reads==r&&map.base_calls==w); /* joined late callbacks cannot touch map */
 }
}
static const struct samurai_usb_status attached_sdp={1,1,0x10,8,0x20,0x29,2};
static const struct samurai_usb_status absent={0};
static void prime(struct samurai_usb_status a,struct samurai_usb_status b)
{
 map.snapshots[0]=a;map.snapshots[1]=b;map.reads=0;map.read_error=0;map.transfer_error=0;
}
static void reset(void)
{
 memset(&input,0,sizeof(input));memset(&map,0,sizeof(map));memset(&device,0,sizeof(device));
 input.dev=&device;input.map=&map;device.data=&input;map.lock=&input.lock;
 apsd_backend=false;queue_count=cancel_count=registration_count=unregistration_count=registration_error=0;
 late_callbacks=false;late_read_error=late_write_error=0;prime(attached_sdp,attached_sdp);
}
int main(void)
{
 struct samurai_apsd_bus_sample sample,poison;
 struct samurai_usb_budget budget;
 reset();memset(&sample,0x5a,sizeof(sample));assert(!samurai_usb_apsd_read(&input,&sample));
 assert(map.reads==14&&sample.serial==1&&sample.present);assert(!memcmp(sample.raw,&attached_sdp,7));
 prime(attached_sdp,attached_sdp);assert(!samurai_usb_apsd_read(&input,&sample));assert(sample.serial==2&&map.reads==14&&!map.writes);
 puts("1 actual R7 two seven-field reads: exact address/order, fresh serial, raw sample, zero write");
 reset();memset(&poison,0x5a,sizeof(poison));
 for(unsigned int fail=0;fail<14;fail++) {
  prime(attached_sdp,attached_sdp);map.fail_read_at=fail;map.read_error=fail%2?-EIO:-ENXIO;sample=poison;
  assert(samurai_usb_apsd_read(&input,&sample)==map.read_error);assert(!memcmp(&sample,&poison,sizeof(sample)));
  assert(map.reads==fail+1&&!input.apsd_sample_serial);
 }
 prime(attached_sdp,attached_sdp);map.snapshots[1].result=4;sample=poison;
 assert(samurai_usb_apsd_read(&input,&sample)==-EAGAIN&&!input.apsd_sample_serial);
 assert(!memcmp(&sample,&poison,sizeof(sample)));
 puts("2 each actual read errno and unequal snapshots leave caller sample/serial unchanged");
 reset();prime(absent,absent);assert(!samurai_usb_apsd_read(&input,&sample)&&!sample.present);
 for(unsigned int bit=0;bit<4;bit++) {
  struct samurai_usb_status s=attached_sdp;
  if(bit==0)s.plugin&=~0x10U;
  if(bit==1)s.misc&=~0x20U;
  if(bit==2)s.misc&=~1U;
  if(bit==3)s.attached&=~0x20U;
  prime(s,s);assert(samurai_usb_apsd_read(&input,&sample)==-EAGAIN);
 }
 struct samurai_usb_status unsafe=attached_sdp;unsafe.misc|=0x10;unsafe.cc=0;
 prime(unsafe,unsafe);assert(!samurai_usb_apsd_read(&input,&sample)&&sample.present);
 prime(unsafe,unsafe);assert(samurai_usb_get_budget(&input,&budget)==-ENODATA&&!map.writes);
 puts("3 proved all-off/all-on only; partial presence rejected; present never grants sink/PD/budget permission");
 reset();assert(samurai_usb_apsd_read(&input,NULL)==-EINVAL&&!map.reads);
 input.apsd_sample_serial=~0ULL;assert(samurai_usb_apsd_read(&input,&sample)==-EOVERFLOW&&!map.reads);
 input.apsd_sample_serial=0;input.paused=true;assert(samurai_usb_apsd_read(&input,&sample)==-ESHUTDOWN&&!map.reads);
 input.paused=false;input.apsd_joining=true;assert(samurai_usb_apsd_read(&input,&sample)==-ESHUTDOWN&&!map.reads);
 puts("4 null output, serial overflow, paused/joining reject before any PMIC read");
 reset();assert(samurai_usb_apsd_rerun(&input,0)==-EINVAL&&!input.apsd_attempt_epoch&&!map.base_calls);
 map.command=0xa5;assert(!samurai_usb_apsd_rerun(&input,10));assert(map.base_calls==1&&map.writes==1&&map.command==0xa5);
 assert(samurai_usb_apsd_rerun(&input,10)==-EALREADY);assert(samurai_usb_apsd_rerun(&input,9)==-ESTALE);assert(map.base_calls==1);
 map.command=0xa4;assert(!samurai_usb_apsd_rerun(&input,11));assert(map.base_calls==2&&map.writes==2&&map.command==0xa5);
 puts("5 actual regmap_write_bits wrapper forces one masked write even when bit already set; preserves other bits");
 reset();map.transfer_error=-EIO;assert(samurai_usb_apsd_rerun(&input,1)==-EIO);assert(input.apsd_attempt_epoch==1&&map.base_calls==1&&!map.writes);
 assert(samurai_usb_apsd_rerun(&input,1)==-EALREADY&&map.base_calls==1);
 input.paused=true;assert(samurai_usb_apsd_rerun(&input,2)==-ESHUTDOWN&&input.apsd_attempt_epoch==2);
 input.paused=false;assert(samurai_usb_apsd_rerun(&input,2)==-EALREADY);
 input.apsd_joining=true;assert(samurai_usb_apsd_rerun(&input,3)==-ESHUTDOWN&&input.apsd_attempt_epoch==3);
 input.apsd_joining=false;assert(samurai_usb_apsd_rerun(&input,3)==-EALREADY&&map.base_calls==1);
 map.transfer_error=0;assert(!samurai_usb_apsd_rerun(&input,~0ULL));assert(samurai_usb_apsd_rerun(&input,1)==-ESTALE);
 puts("6 zero/duplicate/stale epochs rejected; transfer/paused/joining errors consume once, no retry or wrap");
 reset();samurai_usb_apsd_start(&input);assert(!registration_count&&!input.apsd_registered);
 input.udc_valid=true;input.udc_current_ua=100000;assert(!samurai_usb_get_budget(&input,&budget)&&budget.current_ua==100000);
 assert(!samurai_usb_suspend(&device));assert(input.paused&&!registration_count&&!unregistration_count&&!input.udc_valid);
 assert(!samurai_usb_resume(&device));assert(!registration_count&&!unregistration_count&&!input.paused&&queue_count==1);
 puts("7 default false never registers across actual suspend/resume, original budget/UDC pause behavior preserved");
 reset();apsd_backend=true;registration_error=-EOPNOTSUPP;input.udc_valid=true;input.udc_current_ua=100000;
 samurai_usb_apsd_start(&input);assert(registration_count==1&&!input.apsd_registered&&input.apsd_joining&&!input.paused);
 assert(!samurai_usb_get_budget(&input,&budget)&&budget.current_ua==100000&&!map.writes);
 puts("8 optional owner registration failure does not fail or alter ordinary R7 budget observer");
 reset();apsd_backend=true;samurai_usb_apsd_start(&input);assert(registration_count==1&&input.apsd_registered&&!input.apsd_joining);
 samurai_usb_apsd_start(&input);assert(registration_count==1&&input.apsd_registered&&!input.apsd_joining);
 late_callbacks=true;samurai_usb_apsd_withdraw(&input);assert(unregistration_count==1&&late_read_error==-ESHUTDOWN&&late_write_error==-ESHUTDOWN);
 assert(!map.reads&&!map.base_calls&&input.apsd_attempt_epoch==1);samurai_usb_apsd_withdraw(&input);assert(unregistration_count==1);
 puts("9 duplicate start short-circuits; withdraw marks joining before lock-free join; late callbacks do zero I/O");
 reset();apsd_backend=true;samurai_usb_apsd_start(&input);assert(!samurai_usb_apsd_read(&input,&sample));
 assert(!samurai_usb_apsd_rerun(&input,7));u64 serial=input.apsd_sample_serial;unsigned int writes=map.writes;
 input.udc_valid=true;input.udc_current_ua=100000;input.work.pending=true;assert(!samurai_usb_suspend(&device));
 assert(input.paused&&!input.work.pending&&!input.apsd_registered&&unregistration_count==1);
 assert(samurai_usb_get_budget(&input,&budget)==-ENODATA);
 assert(!samurai_usb_resume(&device));assert(registration_count==2&&input.apsd_registered&&!input.paused&&!input.apsd_joining);
 assert(input.apsd_sample_serial==serial&&input.apsd_attempt_epoch==7);assert(samurai_usb_apsd_rerun(&input,7)==-EALREADY&&map.writes==writes);
 prime(attached_sdp,attached_sdp);assert(!samurai_usb_apsd_read(&input,&sample)&&sample.serial==serial+1);
 prime(attached_sdp,attached_sdp);assert(!samurai_usb_get_budget(&input,&budget)&&budget.current_ua==-ENODATA);
 puts("10 actual stop/resume re-registers after join without counter reset, old attempt retry or invented 100mA");
 return 0;
}
