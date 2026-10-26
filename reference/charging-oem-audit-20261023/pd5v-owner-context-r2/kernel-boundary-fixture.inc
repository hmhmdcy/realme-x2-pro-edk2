#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
typedef uint32_t u32;
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define container_of(p,t,m) ((t *)((char *)(p)-offsetof(t,m)))
#define GFP_KERNEL 0
#define THIS_MODULE ((void *)1)
#define ERR_PTR(n) ((void *)(intptr_t)(n))
#define PTR_ERR(p) ((int)(intptr_t)(p))
#define IS_ERR(p) ((uintptr_t)(p)>(uintptr_t)-4096)
struct device_node { int id; };
struct device { struct device_node *of_node; int refs;struct device *parent;void *driverdata; };
struct regulator { int refs, puts; };
struct mutex { int held; };
struct kref { int refs; };
struct regmap { unsigned int raw[0x1800]; };
#define DEFINE_MUTEX(n) struct mutex n
static void mutex_lock(struct mutex *m) { assert(!m->held);m->held=1; }
static void context_unlock_hook(struct mutex *m);
static void mutex_unlock(struct mutex *m) { assert(m->held);m->held=0;context_unlock_hook(m); }
static void mutex_init(struct mutex *m) { m->held=0; }
static void kref_init(struct kref *k) { k->refs=1; }
static void kref_get(struct kref *k) { assert(k->refs>0);k->refs++; }
static void kref_put(struct kref *k,void (*f)(struct kref *)) { assert(k->refs>0);if(!--k->refs)f(k); }
static unsigned long long clock_ms;
static int going,module_refs,reads,writes,fail_read_at,fail_write_at,write_took_effect;
static int mismatch_readback,attach_after_write,slow_read_at,power_enable_error,free_count;
static int attach_on_power;
static unsigned int log_regs[16];
static int try_module_get(void *unused) { (void)unused;if(going)return 0;module_refs++;return 1; }
static void module_put(void *unused) { (void)unused;assert(module_refs>0);module_refs--; }
static unsigned long long ktime_get_boottime(void) { return clock_ms; }
static unsigned long long ktime_to_ms(unsigned long long v) { return v; }
static void msleep(unsigned long long ms) { clock_ms+=ms; }
static int regmap_read(struct regmap *map,unsigned int addr,unsigned int *v) {
 assert(addr<ARRAY_SIZE(map->raw));reads++;
 if(reads==slow_read_at)clock_ms+=251;
 if(reads==fail_read_at)return -EREMOTEIO;
 *v=map->raw[addr];
 if(mismatch_readback && writes && addr==log_regs[writes-1])*v=1;
 return 0;
}
static int regmap_write(struct regmap *map,unsigned int addr,unsigned int value) {
 assert(writes<16);log_regs[writes++]=addr;
 assert(addr==0x174e || addr==0x1744 || addr==0x174c || addr==0x1746);
 assert(value==0);
 if(writes==fail_write_at){if(write_took_effect)map->raw[addr]=value;return -ETIMEDOUT;}
 map->raw[addr]=value;
 if(attach_after_write==writes){map->raw[0x1310]=0x10;map->raw[0x150b]=0x29;map->raw[0x1509]=0x23;map->raw[0x150a]=0;}
 return 0;
}
static struct device_node supply_node={1},other_node={2},phy_node={3};
static bool wrong_supply;
static struct regulator rail;
static struct regmap map;
static struct device_node *of_parse_phandle(struct device_node *np,const char *s,int i) {
 (void)i;assert(np);
 if(!strcmp(s,"vdd-pdphy-supply"))return wrong_supply?&other_node:&supply_node;
 assert(!strcmp(s,"vdda33-supply"));return &supply_node;
}
static struct device_node *of_find_node_by_path(const char *p) { assert(!strcmp(p,"/soc@0/phy@88e2000"));return &phy_node; }
static void of_node_put(struct device_node *n) { (void)n; }
static struct regulator *regulator_get(struct device *d,const char *s) { (void)d;assert(!strcmp(s,"vdd-pdphy"));return &rail; }
static int regulator_enable(struct regulator *r) {
 assert(clock_ms>=1500 && !(map.raw[0x1310]&0x10) && !(map.raw[0x150b]&0x21) && (map.raw[0x150a]&0x40));
 if(power_enable_error)return power_enable_error;
 r->refs++;
 if(attach_on_power){map.raw[0x1310]=0x10;map.raw[0x150b]=0x29;map.raw[0x1509]=0x23;map.raw[0x150a]=0;}
 return 0;
}
static int regulator_disable(struct regulator *r) { assert(r->refs>0);r->refs--;return 0; }
static void regulator_put(struct regulator *r) { r->puts++; }
static struct device *get_device(struct device *d) { d->refs++;return d; }
static void put_device(struct device *d) { assert(d->refs>0);d->refs--; }
static void *kzalloc(size_t n,int g) { (void)g;return calloc(1,n); }
static void kfree(void *p) { free_count++;free(p); }
#define dev_err(...) ((void)0)
#include "qcom_pmic_typec_5v.h"
#include "actual-functions.inc"
static struct device device={.of_node=&other_node};
static struct samurai_pd5v_lease lease;

static void reset(void) {
 assert(!module_refs && !pd5v_bound && !device.refs && !rail.refs);
 memset(&map,0,sizeof(map));memset(&lease,0,sizeof(lease));memset(&rail,0,sizeof(rail));
 clock_ms=1000;going=reads=writes=fail_read_at=fail_write_at=write_took_effect=0;
 mismatch_readback=attach_after_write=slow_read_at=power_enable_error=free_count=0;
 attach_on_power=0;
 wrong_supply=false;
 map.raw[0x150a]=0x40;map.raw[0x1544]=2;map.raw[0x1362]=0x18;
 map.raw[0x174e]=0x88;map.raw[0x1744]=0x23;map.raw[0x174c]=0x21;map.raw[0x1746]=1;
}

/* Full actual qcom probe plus real mode PM/remove callbacks. Only external
 * OF/platform/TCPM functions are faked; normal port/PD start counts matter. */
struct tcpc_dev { int (*init)(struct tcpc_dev *); void *fwnode; };
struct pmic_typec {
 struct device *dev;struct samurai_pd5v *pd5v;struct tcpc_dev tcpc;void *tcpm_port;
 int (*port_start)(struct pmic_typec *,void *);void (*port_stop)(struct pmic_typec *);
 int (*pdphy_start)(struct pmic_typec *,void *);void (*pdphy_stop)(struct pmic_typec *);
};
struct pmic_typec_resources { void *pdphy_res,*port_res; };
struct auxiliary_device { int unused; };
struct platform_device { struct device dev; };
static struct pmic_typec_resources resources={(void *)1,(void *)2};
static bool samurai_5v_only,mode_property,board_match,compatible_match;
static unsigned int children,typec_base,pd_base;
static int port_probes,pd_probes,port_starts,pd_starts;
static struct pmic_typec *probe_allocation;
static void *of_device_get_match_data(struct device *d) { (void)d;return &resources; }
static void *devm_kzalloc(struct device *d,size_t size,int g) { (void)d;(void)g;probe_allocation=calloc(1,size);return probe_allocation; }
static struct regmap *dev_get_regmap(struct device *d,const char *s) { (void)d;(void)s;return &map; }
static bool of_property_read_bool(struct device_node *n,const char *s) { (void)n;assert(!strcmp(s,"realme,pd5v-only"));return mode_property; }
static bool of_machine_is_compatible(const char *s) { assert(!strcmp(s,"realme,samurai"));return board_match; }
static bool of_device_is_compatible(struct device_node *n,const char *s) { (void)n;assert(!strcmp(s,"qcom,pm8150b-typec"));return compatible_match; }
static unsigned int of_get_child_count(struct device_node *n) { (void)n;return children; }
static int of_property_read_u32_index(struct device_node *n,const char *s,int i,unsigned int *v) { (void)n;assert(!strcmp(s,"reg"));*v=i?pd_base:typec_base;return 0; }
static void platform_set_drvdata(struct platform_device *p,void *v) { p->dev.driverdata=v; }
static void *platform_get_drvdata(struct platform_device *p) { return p->dev.driverdata; }
static void *dev_get_drvdata(struct device *d) { return d->driverdata; }
static int fake_port_start(struct pmic_typec *p,void *v) { (void)p;(void)v;port_starts++;return 0; }
static int fake_pd_start(struct pmic_typec *p,void *v) { (void)p;(void)v;pd_starts++;return 0; }
static void fake_stop(struct pmic_typec *p) { (void)p; }
static int qcom_pmic_typec_port_probe(struct platform_device *p,struct pmic_typec *t,void *r,struct regmap *m,unsigned int b) {
 (void)p;(void)r;(void)m;(void)b;port_probes++;t->port_start=fake_port_start;t->port_stop=fake_stop;return 0;
}
static int qcom_pmic_typec_pdphy_probe(struct platform_device *p,struct pmic_typec *t,void *r,struct regmap *m,unsigned int b) {
 (void)p;(void)r;(void)m;(void)b;pd_probes++;t->pdphy_start=fake_pd_start;t->pdphy_stop=fake_stop;return 0;
}
static int qcom_pmic_typec_pdphy_stub_probe(struct platform_device *p,struct pmic_typec *t) { (void)p;(void)t;return -ENODEV; }
static void *device_get_named_child_node(struct device *d,const char *s) { (void)d;(void)s;return NULL; }
static void *to_of_node(void *p) { return p; }
static struct auxiliary_device *devm_drm_dp_hpd_bridge_alloc(struct device *d,void *n) { (void)d;(void)n;return (void *)2; }
static void *tcpm_register_port(struct device *d,struct tcpc_dev *t) { (void)d;(void)t;return (void *)3; }
static void tcpm_unregister_port(void *p) { (void)p; }
static void fwnode_handle_put(void *p) { (void)p; }
static int devm_drm_dp_hpd_bridge_add(struct device *d,void *p) { (void)d;(void)p;return 0; }
#include "actual-probe.inc"
