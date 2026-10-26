/* Actual API, reader, backend and kernel regmap inline are inserted. */
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
struct device {int unused;};
struct mutex {bool held;};
static void mutex_lock(struct mutex *m){assert(!m->held);m->held=true;}
static void mutex_unlock(struct mutex *m){assert(m->held);m->held=false;}
struct delayed_work {bool pending;};
struct power_supply {int unused;};
static bool apsd_backend;
/* ACTUAL_API */
/* ACTUAL_DECODE */
struct regmap {
 struct mutex *lock;
 struct samurai_usb_status snapshots[4];
 unsigned int reads,writes,base_calls,fail_read_at;
 int read_error,transfer_error;
 unsigned int command;
 bool cancelled_after_validation,transfer_saw_cancel;
};
static const unsigned int addresses[]={0x1307,0x1308,0x1310,0x1506,0x1509,0x150b,0x150d};
static int validations,validation_error;
static const struct samurai_apsd_attempt *active;
static int regmap_read(struct regmap *map,unsigned int reg,unsigned int *value)
{
 unsigned int i=map->reads++;assert(map->lock->held&&i<28&&reg==addresses[i%7]);
 if(map->read_error&&i==map->fail_read_at)return map->read_error;
 *value=((const unsigned char*)&map->snapshots[i/7])[i%7];return 0;
}
static int regmap_update_bits_base(struct regmap *map,unsigned int reg,
 unsigned int mask,unsigned int value,bool *change,bool async,bool force)
{
 assert(map->lock->held&&reg==0x1341&&mask==1&&value==1&&!change&&!async&&force);
 assert(map->reads==14&&validations==1);map->base_calls++;
 map->transfer_saw_cancel=map->cancelled_after_validation;
 if(map->transfer_error)return map->transfer_error;
 map->writes++;map->command=(map->command&~mask)|(value&mask);return 0;
}
/* ACTUAL_INLINE */
/* ACTUAL_FUNCTIONS */
static struct samurai_usb_input input;
static struct regmap map;
static struct device device;
static int registrations,withdrawals;
int samurai_apsd_bus_register(struct device *dev,const struct samurai_apsd_bus_ops *ops,void *ctx)
{assert(dev==&device&&ctx==&input&&!input.lock.held&&ops==&samurai_usb_apsd_ops);registrations++;return 0;}
void samurai_apsd_bus_unregister(struct device *dev,void *ctx)
{assert(dev==&device&&ctx==&input&&!input.lock.held&&input.apsd_joining);withdrawals++;}
static int validate(const struct samurai_apsd_attempt *attempt,const struct samurai_apsd_bus_sample *fresh)
{
 assert(input.lock.held&&map.reads==14);validations++;
 if(attempt!=active||attempt->context!=&input)return -ESTALE;
 assert(fresh->serial==2&&fresh->present);return validation_error;
}
static const struct samurai_usb_status attached={1,1,0x10,8,0x20,0x29,2};
static struct samurai_apsd_attempt attempt;
static struct samurai_apsd_transfer_result result;
static void reset(void)
{
 memset(&input,0,sizeof(input));memset(&map,0,sizeof(map));memset(&attempt,0,sizeof(attempt));
 memset(&result,0x5a,sizeof(result));input.dev=&device;input.map=&map;map.lock=&input.lock;
 input.apsd_sample_serial=1;for(int i=0;i<4;i++)map.snapshots[i]=attached;
 validations=validation_error=registrations=withdrawals=0;apsd_backend=false;
 attempt.context=&input;attempt.epoch=10;attempt.expected.serial=1;attempt.expected.present=true;
 memcpy(attempt.expected.raw,&attached,7);attempt.validate=validate;active=&attempt;
}
static int run(void){return samurai_usb_apsd_rerun(&input,&attempt,&result);}
int main(void)
{
 reset();map.command=0xa5;assert(!run()&&map.base_calls==1&&map.writes==1&&map.command==0xa5);
 assert(map.reads==28&&validations==1&&result.transfer_attempted&&result.post_valid&&result.before.serial==2&&result.after.serial==3);
 assert(run()==-EALREADY&&map.base_calls==1&&map.reads==28&&validations==1);attempt.epoch=9;assert(run()==-ESTALE);
 puts("1 final two fresh seven-field reads, exact last callback, one forced masked transfer and new post-read serial");

 for(unsigned int i=0;i<14;i++){
  reset();map.fail_read_at=i;map.read_error=-ENXIO;assert(run()==-ENXIO&&!result.transfer_attempted&&!map.base_calls&&!validations);
  assert(input.apsd_attempt_epoch==10&&run()==-EALREADY);
 }
 reset();map.snapshots[1].result=4;assert(run()==-EAGAIN&&!validations&&!map.base_calls);
 puts("2 every final read errno and unstable pair consumes the epoch without callback or transfer");

 for(unsigned int i=0;i<7;i++){
  reset();((unsigned char*)&map.snapshots[0])[i]^=0x40;map.snapshots[1]=map.snapshots[0];
  assert(run()<0&&!map.base_calls&&!validations&&input.apsd_attempt_epoch==10);
 }
 reset();attempt.expected.present=false;assert(run()==-ESTALE&&!map.base_calls);
 reset();attempt.expected.serial=2;assert(run()==-ESTALE&&!map.base_calls);
 puts("3 each of seven changed fields, off expectation and stale serial reject the cached request");

 reset();validation_error=-ECANCELED;assert(run()==-ECANCELED&&validations==1&&!map.base_calls&&run()==-EALREADY);
 reset();struct samurai_apsd_attempt copied=attempt;assert(samurai_usb_apsd_rerun(&input,&copied,&result)==-ESTALE&&!map.base_calls);
 reset();input.paused=true;assert(run()==-ESHUTDOWN&&!map.reads&&!validations&&input.apsd_attempt_epoch==10);
 reset();input.apsd_joining=true;assert(run()==-ESHUTDOWN&&!map.reads);
 puts("4 final lease/cancellation error and copied identity refuse; paused/withdrawing paths consume without I/O");

 reset();map.transfer_error=-EIO;map.read_error=-ENXIO;map.fail_read_at=14;
 assert(run()==-EIO&&result.write_error==-EIO&&result.post_error==-ENXIO&&result.transfer_attempted&&!result.post_valid);
 assert(map.base_calls==1&&!map.writes&&run()==-EALREADY);
 for(unsigned int i=14;i<28;i++){
  reset();map.read_error=-ENXIO;map.fail_read_at=i;
  assert(run()==-ENXIO&&result.write_error==0&&result.post_error==-ENXIO&&map.writes==1&&!result.post_valid);
 }
 puts("5 command errno and independent post-read error both survive; unknown outcome is never retried");

 reset();map.snapshots[2].apsd=map.snapshots[3].apsd=0;
 assert(!run()&&result.post_valid&&!(result.after.raw[0]&1));
 reset();map.snapshots[2].result=map.snapshots[3].result=4;
 assert(!run()&&result.after.raw[1]==4); /* fresh result is not old-DONE completion */
 puts("6 post-command DONE clear/result changes are preserved for the real once core");

 for(unsigned int i=2;i<7;i++){
  reset();((unsigned char*)&map.snapshots[2])[i]^=0x40;map.snapshots[3]=map.snapshots[2];
  int ret=run();assert(ret<0&&ret==result.post_error&&map.writes==1&&!result.post_valid);
 }
 reset();memset(&map.snapshots[2],0,sizeof(attached));map.snapshots[3]=map.snapshots[2];
 assert(run()==-ESTALE&&map.writes==1);
 reset();map.snapshots[2].apsd=map.snapshots[3].apsd=3;assert(run()==-ESTALE&&map.writes==1);
 puts("7 post-write detach, source/role changes or QC are failure/unknown, never atomic attachment proof");

 reset();samurai_usb_apsd_start(&input);assert(!registrations);
 apsd_backend=true;samurai_usb_apsd_start(&input);assert(registrations==1);
 assert(!run());samurai_usb_apsd_withdraw(&input);assert(withdrawals==1);
 samurai_usb_apsd_start(&input);assert(registrations==2&&input.apsd_sample_serial==3&&input.apsd_attempt_epoch==10);
 assert(run()==-EALREADY&&map.base_calls==1);samurai_usb_apsd_withdraw(&input);
 puts("8 provider re-registration keeps physical epoch and serial history; no source-budget writes");

 reset();attempt.validate=NULL;assert(run()==-EINVAL&&!input.apsd_attempt_epoch&&!map.reads);
 reset();attempt.epoch=0;assert(run()==-EINVAL&&!map.reads);
 reset();input.apsd_sample_serial=~0ULL;assert(run()==-EOVERFLOW&&input.apsd_attempt_epoch==10&&!map.reads);
 puts("9 malformed attempts and exhausted serial never reach a write");
 return 0;
}
