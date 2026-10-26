/* Actual candidate functions. Only register IO/kernel and board OF boundary fake. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
typedef int16_t s16;
enum {BQ27000,BQ27Z561,BQ28Z610};
enum {POWER_SUPPLY_STATUS_FULL=1,POWER_SUPPLY_STATUS_CHARGING,POWER_SUPPLY_STATUS_DISCHARGING,POWER_SUPPLY_STATUS_NOT_CHARGING};
enum power_supply_property {POWER_SUPPLY_PROP_STATUS,POWER_SUPPLY_PROP_PRESENT,POWER_SUPPLY_PROP_VOLTAGE_NOW,
 POWER_SUPPLY_PROP_CURRENT_NOW,POWER_SUPPLY_PROP_CURRENT_AVG,POWER_SUPPLY_PROP_CAPACITY,POWER_SUPPLY_PROP_CAPACITY_LEVEL,
 POWER_SUPPLY_PROP_TEMP,POWER_SUPPLY_PROP_TIME_TO_EMPTY_NOW,POWER_SUPPLY_PROP_TIME_TO_EMPTY_AVG,POWER_SUPPLY_PROP_TIME_TO_FULL_NOW,
 POWER_SUPPLY_PROP_TECHNOLOGY,POWER_SUPPLY_PROP_CHARGE_FULL,POWER_SUPPLY_PROP_CHARGE_NOW,POWER_SUPPLY_PROP_CHARGE_FULL_DESIGN,
 POWER_SUPPLY_PROP_CYCLE_COUNT,POWER_SUPPLY_PROP_POWER_AVG,POWER_SUPPLY_PROP_HEALTH,POWER_SUPPLY_PROP_MANUFACTURER,
 POWER_SUPPLY_PROP_ENERGY_FULL_DESIGN,POWER_SUPPLY_PROP_VOLTAGE_MIN_DESIGN,POWER_SUPPLY_PROP_VOLTAGE_MAX_DESIGN,POWER_SUPPLY_PROP_ENERGY_NOW};
enum {POWER_SUPPLY_TECHNOLOGY_UNKNOWN,POWER_SUPPLY_TECHNOLOGY_LION};
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define BQ27XXX_O_ZERO 1
#define BQ27Z561_O_BITS 2
#define BQ27XXX_O_MUL_CHEM 4
#define BQ27000_FLAG_FC 32
#define BQ27000_FLAG_CHGS 128
#define BQ27Z561_FLAG_FC 32
#define BQ27XXX_FLAG_FC 512
#define BQ27XXX_CURRENT_CONSTANT 3570
#define BQ27XXX_RS 20
#define BQ27XXX_MANUFACTURER "Texas Instruments"
#define INVALID_REG_ADDR 255
#define unlikely(x) (x)
#define HZ 100
union power_supply_propval{int intval;const char *strval;};
struct mutex{int held;};
struct device{void *of_node;};
struct power_supply{void *data;};
struct power_supply_desc{enum power_supply_property *properties;unsigned int num_properties;};
struct bq27xxx_reg_cache{int flags,capacity;};
struct bq27xxx_device_info;
struct bq27xxx_bus{int(*read)(struct bq27xxx_device_info*,unsigned char,bool);};
struct bq27xxx_device_info{struct device *dev;int chip,opts;unsigned char *regs;struct bq27xxx_bus bus;
 struct mutex lock;struct bq27xxx_reg_cache cache;union power_supply_propval last_status;struct power_supply *bat;
 unsigned long last_update;bool removed;int work;};
#include "tested-declarations.inc"
static bool samurai_instant_current,machine_ok,node_ok;
static int of_calls,reads,registers[32],word[256],changed;
static unsigned char regs[BQ27XXX_REG_MAX];
static struct device dev;static struct power_supply psy;static struct bq27xxx_device_info d;
static unsigned long jiffies;static int poll_interval;static void *system_percpu_wq;
static bool of_machine_is_compatible(const char *s){assert(!strcmp(s,"realme,samurai"));of_calls++;return machine_ok;}
static bool of_device_is_compatible(void *n,const char *s){assert(!strcmp(s,"ti,bq28z610"));of_calls++;return n&&node_ok;}
static void mutex_lock(struct mutex *m){assert(!m->held);m->held=1;}
static void mutex_unlock(struct mutex *m){assert(m->held);m->held=0;}
static void *power_supply_get_drvdata(struct power_supply *p){return p->data;}
static void power_supply_changed(struct power_supply *p){assert(p==&psy);changed++;}
static bool time_is_before_jiffies(unsigned long t){return t<jiffies;}
static void mod_delayed_work(void *wq,int *w,int delay){}
static void dev_err(struct device *p,const char *s,...){}
static void dev_dbg(struct device *p,const char *s,...){}
static int bq27xxx_battery_read_soc(struct bq27xxx_device_info *p){return 80;}
#define SIMPLE_STUB(n) static int n(struct bq27xxx_device_info *p,union power_supply_propval *v){return -EOPNOTSUPP;}
SIMPLE_STUB(bq27xxx_battery_voltage) SIMPLE_STUB(bq27xxx_battery_capacity_level)
SIMPLE_STUB(bq27xxx_battery_read_temperature) SIMPLE_STUB(bq27xxx_battery_read_nac) SIMPLE_STUB(bq27xxx_battery_read_rc)
SIMPLE_STUB(bq27xxx_battery_read_fcc) SIMPLE_STUB(bq27xxx_battery_read_dcap) SIMPLE_STUB(bq27xxx_battery_read_dmin_volt)
SIMPLE_STUB(bq27xxx_battery_read_dmax_volt) SIMPLE_STUB(bq27xxx_battery_read_cyct) SIMPLE_STUB(bq27xxx_battery_read_energy)
SIMPLE_STUB(bq27xxx_battery_pwr_avg) SIMPLE_STUB(bq27xxx_battery_read_health)
static int bq27xxx_battery_read_time(struct bq27xxx_device_info *p,int reg,union power_supply_propval *v){return -EOPNOTSUPP;}
static int bq27xxx_simple_value(int value,union power_supply_propval *v){v->intval=value;return 0;}
static int bus_read(struct bq27xxx_device_info *p,unsigned char reg,bool single)
{assert(reg==0x0a||reg==0x0c||reg==0x14);assert(reads<32);registers[reads++]=reg;return word[reg];}
#include "tested-functions.inc"
static void setup(bool enabled)
{
 memset(&d,0,sizeof(d));memset(word,0,sizeof(word));memset(registers,0,sizeof(registers));memset(regs,255,sizeof(regs));
 regs[BQ27XXX_REG_AI]=0x14;regs[BQ27XXX_REG_FLAGS]=0x0a;dev.of_node=(void*)1;
 d=(struct bq27xxx_device_info){.dev=&dev,.chip=BQ28Z610,.opts=BQ27Z561_O_BITS,.regs=regs,.bus={bus_read},.bat=&psy};psy.data=&d;
 d.cache.flags=0;d.cache.capacity=80;machine_ok=node_ok=true;samurai_instant_current=enabled;reads=changed=of_calls=0;jiffies=0;poll_interval=0;
}
static int get(enum power_supply_property prop,int *value)
{union power_supply_propval v={.intval=123456789};int ret=bq27xxx_battery_get_property(&psy,prop,&v);*value=v.intval;return ret;}
static void now_status(int ma,int flags,int want)
{
 word[0x0c]=(uint16_t)(int16_t)ma;word[0x0a]=flags;int current,status;
 assert(!get(POWER_SUPPLY_PROP_CURRENT_NOW,&current)&&current==ma*1000);
 assert(!get(POWER_SUPPLY_PROP_STATUS,&status)&&status==want);
}
static int groups;
static void done(const char *s){groups++;printf("ok: %s\n",s);}
static void test_profile_gate(void)
{
 for(int missing=0;missing<5;missing++){
  setup(true);if(missing==0)samurai_instant_current=false;if(missing==1)machine_ok=false;if(missing==2)d.chip=BQ27Z561;
  if(missing==3)node_ok=false;
  if(missing==4)dev.of_node=NULL;
  assert(!bq27xxx_samurai_instant(&d));struct power_supply_desc desc={bq28z610_props,ARRAY_SIZE(bq28z610_props)};
  bq27xxx_samurai_props(&d,&desc);assert(desc.properties==bq28z610_props&&desc.num_properties==ARRAY_SIZE(bq28z610_props));
  word[0x14]=7;word[0x0c]=(uint16_t)-9;int v;assert(!get(POWER_SUPPLY_PROP_CURRENT_NOW,&v)&&v==7000&&registers[0]==0x14);
  int old=reads;assert(get(POWER_SUPPLY_PROP_CURRENT_AVG,&v)==-EINVAL&&reads==old);
 }
 setup(true);assert(bq27xxx_samurai_instant(&d));struct power_supply_desc desc={bq28z610_props,ARRAY_SIZE(bq28z610_props)};
 bq27xxx_samurai_props(&d,&desc);assert(desc.properties==bq28z610_samurai_props&&desc.num_properties==ARRAY_SIZE(bq28z610_props)+1);
 assert(!memcmp(desc.properties,bq28z610_props,sizeof(bq28z610_props))&&desc.properties[desc.num_properties-1]==POWER_SUPPLY_PROP_CURRENT_AVG);
 done("opt-in plus actual machine/chip/native node all required; no average property otherwise");
}
static void test_default_differential(void)
{
 const int raw[]={0,1,0x7fff,0x8000,0xffff,-EIO};int assertions=0;
 for(unsigned int i=0;i<ARRAY_SIZE(raw);i++)for(int full=0;full<2;full++)for(int opts=0;opts<3;opts++){
  setup(false);d.opts=opts;word[0x14]=raw[i];word[0x0a]=full?(opts==0?512:32):0;
  union power_supply_propval cn={.intval=111},sn={.intval=222},co=cn,so=sn;
  int rn=bq27xxx_battery_current_and_status(&d,&cn,&sn,NULL);int seq[32],n=reads;memcpy(seq,registers,sizeof(seq));reads=0;
  int ro=original_current_and_status(&d,&co,&so,NULL);
  assert(rn==ro&&cn.intval==co.intval&&sn.intval==so.intval&&reads==n&&!memcmp(seq,registers,n*sizeof(int))&&!of_calls);assertions++;
 }
 assert(assertions==36);done("default actual current/status differential: raw signed bounds/errors/FC/layout and identical IO");
}
static void test_signed_and_full(void)
{
 setup(true);word[0x14]=123;now_status(7,0,POWER_SUPPLY_STATUS_CHARGING);reads=0;
 now_status(-1,0,POWER_SUPPLY_STATUS_DISCHARGING);reads=0;
 now_status(0,0,POWER_SUPPLY_STATUS_NOT_CHARGING);reads=0;
 now_status(-32768,32,POWER_SUPPLY_STATUS_FULL);reads=0;
 now_status(32767,32,POWER_SUPPLY_STATUS_FULL);
 done("enabled NOW/STATUS use signed 0c; zero and FC priority preserve existing semantics");
}
static void test_average_separation(void)
{
 setup(true);word[0x14]=(uint16_t)-31;now_status(19,0,POWER_SUPPLY_STATUS_CHARGING);
 int v;reads=0;assert(!get(POWER_SUPPLY_PROP_CURRENT_AVG,&v)&&v==-31000&&reads==1&&registers[0]==0x14);
 reads=0;word[0x14]=21;now_status(-15,0,POWER_SUPPLY_STATUS_DISCHARGING);reads=0;
 assert(!get(POWER_SUPPLY_PROP_CURRENT_AVG,&v)&&v==21000&&reads==1&&registers[0]==0x14);
 done("opposite instant/average signs stay separate; CURRENT_AVG reads original 14 only");
}
static void test_errors(void)
{
 setup(true);word[0x0c]=-EIO;int v;assert(get(POWER_SUPPLY_PROP_STATUS,&v)==-EIO&&v==123456789);
 reads=0;assert(get(POWER_SUPPLY_PROP_CURRENT_NOW,&v)==-EIO&&v==123456789);
 reads=0;word[0x0c]=0xffff;word[0x0a]=-EREMOTEIO;assert(get(POWER_SUPPLY_PROP_CURRENT_NOW,&v)==-EREMOTEIO&&v==123456789);
 reads=0;word[0x14]=-EIO;assert(get(POWER_SUPPLY_PROP_CURRENT_AVG,&v)==-EIO&&v==123456789);
 reads=0;d.cache.flags=-ENODEV;assert(get(POWER_SUPPLY_PROP_STATUS,&v)==-ENODEV&&!reads);
 done("transport/cache/flags errors never become fabricated zero current or status");
}
static void test_update_and_locks(void)
{
 setup(true);d.last_status.intval=POWER_SUPPLY_STATUS_CHARGING;word[0x14]=25;word[0x0c]=(uint16_t)-20;word[0x0a]=0;
 bq27xxx_battery_update(&d);assert(!d.lock.held&&changed==1&&d.last_status.intval==POWER_SUPPLY_STATUS_DISCHARGING);
 assert(reads==2&&registers[0]==0x0a&&registers[1]==0x0c);reads=0;
 bq27xxx_battery_update(&d);assert(changed==1);assert(!d.lock.held);
 /* Model outer R8 charger lock only; no source/charger callback exists in
  * the extracted gauge implementation to reacquire that outer lock. */
 int v;reads=0;assert(!get(POWER_SUPPLY_PROP_STATUS,&v)&&v==POWER_SUPPLY_STATUS_DISCHARGING&&!d.lock.held);
 done("actual update/cache status notification uses instant path without recursive di lock");
}
int main(void)
{test_profile_gate();test_default_differential();test_signed_and_full();test_average_separation();test_errors();test_update_and_locks();assert(groups==6);return 0;}
