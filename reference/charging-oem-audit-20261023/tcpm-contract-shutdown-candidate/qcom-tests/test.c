/* Kernel/device boundaries for complete production functions included below. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#define BIT(n) (1U<<(n))
#define GENMASK(h,l) (((~0U)<<(l)) & ((~0U)>>(31-(h))))
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define PD_REV20 1
#define PDO_FIXED_USB_COMM BIT(26)
#define PDO_FIXED(mv,ma,flags) ((((mv)/50)<<10)|((ma)/10)|(flags))
#define dev_err(d,...) do { (void)(d); if(0) printf(__VA_ARGS__); } while(0)
#define dev_info dev_err
typedef uint32_t u32;
typedef int spinlock_t;
struct mutex { int unused; };
struct work_struct { int active; };
struct delayed_work { int active; };
struct regulator { int unused; };
struct regmap { int unused; };
struct tcpm_port { int unused; };
struct fwnode_handle { const char *power,*data; int count; u32 pdo,uw; bool source; };
struct device { void *of_node; };
struct tcpc_dev { struct fwnode_handle *fwnode; };
struct platform_device { struct pmic_typec *data; };
#include "actual-types.inc"

static struct pmic_typec tcpm;
static struct pmic_typec_port port;
static struct pmic_typec_pdphy pd;
static struct pmic_typec_port_irq_data port_irqs[2];
static struct pmic_typec_pdphy_irq_data pd_irqs[2];
static struct regulator supply;
static struct device dev;
static struct tcpm_port core;
static struct fwnode_handle fw;
static bool board_ok, pmic_ok, core_joined;
static int prepare_error, prepare_calls;
static unsigned regs[65536], addresses[64], values[64];
static bool write_joined[64];
static int write_attempts,write_ok,reads,fail_write,fail_read,corrupt_read;
static int supply_count,enable_error,disable_error,put_count,reset_joins,unregisters;
static int cc_pre_joins,cc_post_joins,port_disabled,pd_disabled,enabled,legacy_quiesce,legacy_destroy;

static int regmap_write(struct regmap *m,unsigned a,unsigned v)
{
 (void)m; write_attempts++;
 if(tcpm.samurai_fixed_5v && a>=0x1740 && a<=0x174e) assert(supply_count==1);
 assert(write_attempts<=64);
 addresses[write_attempts-1]=a; values[write_attempts-1]=v;
 write_joined[write_attempts-1]=core_joined;
 if(write_attempts==fail_write) return -EIO;
 regs[a]=v; write_ok++; return 0;
}
static int regmap_read(struct regmap *m,unsigned a,unsigned *v)
{
 (void)m; reads++;
 if(tcpm.samurai_fixed_5v && a>=0x1740 && a<=0x174e) assert(supply_count==1);
 if(reads==fail_read) return -EREMOTEIO;
 *v=regs[a]; if(reads==corrupt_read) *v^=0x80; return 0;
}
static int regmap_update_bits(struct regmap *m,unsigned a,unsigned mask,unsigned v)
{ return regmap_write(m,a,(regs[a]&~mask)|(v&mask)); }
static void enable_irq(int n) { (void)n; enabled++; }
static void disable_irq(int n)
{
 assert(!core_joined);
 if(n<10) port_disabled++; else pd_disabled++;
}
static void cancel_work_sync(struct work_struct *w)
{
 assert(w==&pd.reset_work); assert(!core_joined);
 assert(!pd.irqs_started); reset_joins++; w->active=0;
}
static void disable_delayed_work_sync(struct delayed_work *w)
{
 assert(w==&port.cc_debounce_dwork);
 if(core_joined) cc_post_joins++; else cc_pre_joins++;
 w->active=0;
}
static int regulator_enable(struct regulator *r)
{ assert(r==&supply); if(enable_error) return enable_error; supply_count++; return 0; }
static int regulator_disable(struct regulator *r)
{ assert(r==&supply && supply_count>0); if(disable_error) return disable_error; supply_count--; return 0; }
static void usleep_range(unsigned a,unsigned b) { assert(a==400 && b==500); }
static struct pmic_typec *platform_get_drvdata(struct platform_device *d) { return d->data; }
static void fwnode_handle_put(struct fwnode_handle *f) { if(f) { assert(f==&fw); put_count++; } }
static bool of_machine_is_compatible(const char *s) { assert(!strcmp(s,"realme,samurai")); return board_ok; }
static bool of_device_is_compatible(void *n,const char *s)
{ assert(n==dev.of_node && !strcmp(s,"qcom,pm8150b-typec")); return pmic_ok; }
static int fwnode_property_read_string(struct fwnode_handle *f,const char *n,const char **s)
{
 assert(f==&fw); *s=!strcmp(n,"power-role")?f->power:f->data;
 return *s?0:-EINVAL;
}
static bool fwnode_property_present(struct fwnode_handle *f,const char *n)
{ assert(f==&fw && !strcmp(n,"source-pdos")); return f->source; }
static int fwnode_property_count_u32(struct fwnode_handle *f,const char *n)
{ assert(f==&fw && !strcmp(n,"sink-pdos")); return f->count; }
static int fwnode_property_read_u32(struct fwnode_handle *f,const char *n,u32 *v)
{ assert(f==&fw); *v=!strcmp(n,"sink-pdos")?f->pdo:f->uw; return 0; }
static void samurai_pd5v_quiesce(struct samurai_pd5v *p) { assert(p); legacy_quiesce++; }
static void samurai_pd5v_destroy(struct samurai_pd5v *p) { assert(p); legacy_destroy++; }
static void tcpm_unregister_port(struct tcpm_port *p)
{
 assert(p==&core && !core_joined);
 if(tcpm.samurai_fixed_5v) {
  assert(!port.irqs_started && !pd.irqs_started && !pd.reset_work.active);
  assert(supply_count==1 || !pd.supply_held);
 }
 /* Model a pending TCPM callback during worker join, before join returns. */
 port.cc_debounce_dwork.active=1;
 regs[port.base+TYPEC_MODE_CFG_REG]=TYPEC_DISABLE_CMD;
 unregisters++; core_joined=true;
}

static int tcpm_prepare_sink_shutdown(struct tcpm_port *p, unsigned int timeout_ms,
 int (*reader)(void *,int *), void *context)
{
 assert(p==&core&&timeout_ms==2000&&!core_joined&&context==&tcpm);
 (void)reader;
 assert(port.irqs_started&&pd.irqs_started&&pd.supply_held);
 assert(!write_attempts&&!port_disabled&&!pd_disabled&&!unregisters);
 prepare_calls++;return prepare_error;
}
#include "actual-functions.inc"


static void setup(bool fixed)
{
 memset(&tcpm,0,sizeof(tcpm)); memset(&port,0,sizeof(port)); memset(&pd,0,sizeof(pd));
 memset(regs,0,sizeof(regs)); memset(write_joined,0,sizeof(write_joined));
 write_attempts=write_ok=reads=fail_write=fail_read=corrupt_read=0;
 supply_count=1; enable_error=disable_error=put_count=reset_joins=unregisters=0;
 cc_pre_joins=cc_post_joins=port_disabled=pd_disabled=enabled=legacy_quiesce=legacy_destroy=0;
 core_joined=false; board_ok=pmic_ok=true;prepare_error=prepare_calls=0;
 fw=(struct fwnode_handle){.power="sink",.data="device",.count=1,.pdo=0x04019032,.uw=2500000};
 dev.of_node=&dev; tcpm.dev=&dev; tcpm.tcpm_port=&core; tcpm.tcpc.fwnode=&fw;
 tcpm.pmic_typec_port=&port; tcpm.pmic_typec_pdphy=&pd; tcpm.samurai_fixed_5v=fixed;
 tcpm.port_stop=qcom_pmic_typec_port_stop; tcpm.pdphy_stop=qcom_pmic_typec_pdphy_stop;
 port.dev=pd.dev=&dev; port.base=0x1500; pd.base=0x1700;
 port.tcpm_port=pd.tcpm_port=&core; port.nr_irqs=pd.nr_irqs=2;
 port.irq_data=port_irqs; pd.irq_data=pd_irqs;
 port_irqs[0].irq=1;port_irqs[1].irq=2;pd_irqs[0].irq=11;pd_irqs[1].irq=12;
 port.irqs_started=pd.irqs_started=pd.supply_held=true; pd.vdd_pdphy=&supply;
 pd.reset_work.active=1; port.cc_debounce_dwork.active=1;
 regs[0x174e]=regs[0x1744]=regs[0x174c]=regs[0x1746]=0xff;
}
static void assert_off(void)
{
 assert(!regs[0x174e] && !regs[0x1744] && !regs[0x174c] && !regs[0x1746]);
 assert(tcpm.samurai_joined && !tcpm.tcpm_port && !pd.tcpm_port && !port.tcpm_port);
 assert(!port.cc_debounce_dwork.active && !pd.reset_work.active);
 assert(port_disabled==2 && pd_disabled==2 && unregisters==1 && reset_joins==1);
 assert(cc_pre_joins==1 && cc_post_joins==1);
}
int main(void)
{
 setup(true); assert(qcom_pmic_typec_samurai_fixed_5v(&tcpm));
 board_ok=false; assert(!qcom_pmic_typec_samurai_fixed_5v(&tcpm)); board_ok=true;
 pmic_ok=false; assert(!qcom_pmic_typec_samurai_fixed_5v(&tcpm)); pmic_ok=true;
 fw.power="dual"; assert(!qcom_pmic_typec_samurai_fixed_5v(&tcpm)); fw.power="sink";
 fw.data="dual"; assert(!qcom_pmic_typec_samurai_fixed_5v(&tcpm)); fw.data="device";
 fw.pdo=PDO_FIXED(9000,500,PDO_FIXED_USB_COMM); assert(!qcom_pmic_typec_samurai_fixed_5v(&tcpm)); fw.pdo=0x04019032;
 fw.source=true; assert(!qcom_pmic_typec_samurai_fixed_5v(&tcpm)); fw.source=false;
 fw.count=2; assert(!qcom_pmic_typec_samurai_fixed_5v(&tcpm)); fw.count=1;
 fw.uw=15000000; assert(!qcom_pmic_typec_samurai_fixed_5v(&tcpm));
 assert(!write_attempts); puts("PASS exact board/connector/PDO gate; 9V and other roles excluded");

 setup(true); assert(!qcom_pmic_typec_stop_samurai_5v(&tcpm)); assert_off();
 const unsigned off[]={0x174e,0x1744,0x174c,0x1746,0x1544};
 assert(write_attempts==5 && reads==5 && supply_count==0 && tcpm.samurai_pd_quiet);
 for(int i=0;i<5;i++) assert(addresses[i]==off[i] && write_joined[i]);
 assert(regs[0x1544]==EN_SNK_ONLY);
 assert(!qcom_pmic_typec_stop_samurai_5v(&tcpm) && write_attempts==5 && unregisters==1);
 puts("PASS CC/PD IRQ+work, TCPM join, four zero/readbacks, supply release, final debounce/Rd");

 for(int i=1;i<=4;i++) {
  setup(true); fail_write=i;
  assert(qcom_pmic_typec_stop_samurai_5v(&tcpm)==-EIO);
  assert(supply_count==1 && !tcpm.samurai_pd_quiet && regs[0x1544]==TYPEC_DISABLE_CMD);
  assert(write_attempts==5 && tcpm.samurai_joined && !tcpm.tcpm_port);
  int n=write_attempts;assert(qcom_pmic_typec_stop_samurai_5v(&tcpm)==-EIO && n==write_attempts);
  setup(true); fail_read=i;
  assert(qcom_pmic_typec_stop_samurai_5v(&tcpm)==-EREMOTEIO && supply_count==1 && !tcpm.samurai_pd_quiet);
  setup(true); corrupt_read=i;
  assert(qcom_pmic_typec_stop_samurai_5v(&tcpm)==-EIO && supply_count==1 && !tcpm.samurai_pd_quiet);
 }
 setup(true);fail_write=1;fail_read=1;
 assert(qcom_pmic_typec_stop_samurai_5v(&tcpm)==-EIO && supply_count==1);
 puts("PASS every PD write/read/mismatch: first error, retained supply, CC disabled, no retry");

 setup(true); disable_error=-EBUSY;
 assert(qcom_pmic_typec_stop_samurai_5v(&tcpm)==-EBUSY && supply_count==1 && tcpm.samurai_pd_quiet);
 assert(regs[0x1544]==TYPEC_DISABLE_CMD);
 setup(true); fail_write=5;
 assert(qcom_pmic_typec_stop_samurai_5v(&tcpm)==-EIO && supply_count==0 && tcpm.samurai_pd_quiet);
 setup(true); corrupt_read=5; assert(qcom_pmic_typec_stop_samurai_5v(&tcpm)==-EIO);
 setup(true);assert(qcom_pmic_typec_pdphy_finish_5v(&tcpm)==-EBUSY && !write_attempts);
 assert(qcom_pmic_typec_port_finish_5v(&tcpm,true)==-EBUSY && !write_attempts);
 puts("PASS regulator/CC failures and pre-join hardware refusal");

 setup(true); pd.irqs_started=pd.supply_held=port.irqs_started=false; supply_count=0;
 assert(!qcom_pmic_typec_stop_samurai_5v(&tcpm));
 assert(!port_disabled && !pd_disabled && !tcpm.samurai_pd_quiet && write_attempts==1 && !supply_count);
 puts("PASS never-started resources: no IRQ underflow, no PD I/O or false quiet claim");

 setup(true); struct platform_device d={.data=&tcpm};
 qcom_pmic_typec_shutdown(&d); assert_off(); assert(put_count==1 && !tcpm.tcpc.fwnode);
 qcom_pmic_typec_remove(&d); assert(put_count==1 && unregisters==1);
 setup(false); qcom_pmic_typec_shutdown(&d); assert(!write_attempts && !unregisters);
 tcpm.pd5v=(struct samurai_pd5v *)&dev;
 qcom_pmic_typec_shutdown(&d);qcom_pmic_typec_remove(&d);
 assert(legacy_quiesce==1 && legacy_destroy==1 && !write_attempts && !unregisters);
 puts("PASS shutdown/remove once and unchanged PD5V/default shutdown dispatch");

 setup(true); pd.supply_held=pd.irqs_started=false;supply_count=0;pd.reset_work.active=0;
 enable_error=-EIO;assert(qcom_pmic_typec_pdphy_start(&tcpm,&core)==-EIO && !supply_count && !enabled);
 enable_error=0; fail_write=3;
 assert(qcom_pmic_typec_pdphy_start(&tcpm,&core)==-EIO && supply_count==1 && pd.supply_held && !pd.irqs_started);
 fail_write=0;write_attempts=write_ok=reads=0;
 assert(!qcom_pmic_typec_stop_samurai_5v(&tcpm) && !supply_count && tcpm.samurai_pd_quiet);
 puts("PASS failed PD startup retains supply until joined cleanup");

 setup(false);tcpm.samurai_contract_shutdown=true;
 assert(qcom_pmic_typec_samurai_sink(&tcpm));
 fw.power="dual";assert(!qcom_pmic_typec_samurai_sink(&tcpm));fw.power="sink";
 assert(!qcom_pmic_typec_stop_samurai_contract(&tcpm));assert_off();assert(prepare_calls==1);
 assert(!qcom_pmic_typec_stop_samurai_contract(&tcpm)&&prepare_calls==1);
 puts("PASS high-contract path prepares with IRQ/worker alive before join/MMIO close");
 const int errors[]={-EOPNOTSUPP,-ETIMEDOUT,-EIO,-EAGAIN};
 for(unsigned i=0;i<ARRAY_SIZE(errors);i++){
  setup(false);tcpm.samurai_contract_shutdown=true;prepare_error=errors[i];
  qcom_pmic_typec_shutdown(&d);
  assert(prepare_calls==1&&!unregisters&&!write_attempts&&!tcpm.samurai_joined);
  assert(port.irqs_started&&pd.irqs_started&&supply_count==1&&tcpm.tcpc.fwnode==&fw);
  qcom_pmic_typec_remove(&d);
  assert(prepare_calls==2&&unregisters==1&&tcpm.samurai_joined&&!tcpm.tcpm_port);
  assert(tcpm.samurai_stop_error==errors[i]&&!tcpm.samurai_pd_quiet);
  assert(!write_attempts&&put_count==1&&!tcpm.tcpc.fwnode);
  assert(!port.irqs_started&&!pd.irqs_started&&!pd.reset_work.active);
  assert(!port.cc_debounce_dwork.active&&!port.tcpm_port&&cc_post_joins==1);
  qcom_pmic_typec_remove(&d);assert(unregisters==1&&prepare_calls==2&&put_count==1);
 }
 puts("PASS failed preparation keeps shutdown alive; void remove joins without false5V close");
 setup(false);tcpm.samurai_contract_shutdown=true;fail_write=1;
 qcom_pmic_typec_shutdown(&d);
 assert(tcpm.samurai_joined&&tcpm.samurai_stop_error==-EIO&&!tcpm.tcpm_port);
 int attempts=write_attempts;qcom_pmic_typec_remove(&d);
 assert(unregisters==1&&prepare_calls==1&&put_count==1&&write_attempts==attempts);
 puts("PASS post-join close error and later remove never unregister NULL or double-join");
 return 0;
}
