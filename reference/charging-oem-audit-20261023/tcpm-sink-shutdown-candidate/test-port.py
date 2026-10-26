"""Exercise complete candidate functions; fake only kernel/device/I/O boundaries."""
from pathlib import Path
import hashlib, json, re, subprocess, tempfile
HERE = Path(__file__).resolve().parent
source = (HERE / 'qcom_pmic_typec_port.c').read_text()
names = ['qcom_pmic_typec_port_vbus_toggle', 'qcom_pmic_typec_port_set_vbus',
         'qcom_pmic_typec_port_set_cc', 'qcom_pmic_typec_port_set_vconn',
         'qcom_pmic_typec_port_start_toggling', 'qcom_pmic_typec_port_start',
         'qcom_pmic_typec_port_get_vbus_supply']

def function(name):
    match = re.search(r'^static int ' + name + r'\([^;]*?\)\n\{', source, re.M)
    assert match, name
    pos = match.end()
    depth = 1
    while depth:
        if source[pos] == '{': depth += 1
        elif source[pos] == '}': depth -= 1
        pos += 1
    return source[match.start():pos] + '\n'

prefix = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
typedef uint32_t u32;
typedef uint8_t u8;
#define BIT(n) (1U << (n))
#define GENMASK(h,l) (((~0U) << (l)) & ((~0U) >> (31-(h))))
#define ERR_PTR(e) ((void *)(intptr_t)(e))
#define PTR_ERR(p) ((int)(intptr_t)(p))
#define IS_ERR(p) ((uintptr_t)(p) >= (uintptr_t)-4095)
#define EPROBE_DEFER 517
#define dev_dbg(d, ...) do { (void)(d); if (0) printf(__VA_ARGS__); } while (0)
#define dev_warn dev_dbg
#define misc_to_cc(m) (((m)&CC_ORIENTATION)?"cc1":"cc2")
#define misc_to_vconn(m) (((m)&CC_ORIENTATION)?"cc2":"cc1")
#define spin_lock_irqsave(l,f) do { (void)(l); (f)=0; } while (0)
#define spin_unlock_irqrestore(l,f) do { (void)(l); (void)(f); } while (0)
#define mutex_lock(l) ((void)(l))
#define mutex_unlock(l) ((void)(l))
enum typec_cc_status { TYPEC_CC_OPEN, TYPEC_CC_RA, TYPEC_CC_RD, TYPEC_CC_RP_DEF, TYPEC_CC_RP_1_5, TYPEC_CC_RP_3_0 };
enum typec_port_type { TYPEC_PORT_SRC, TYPEC_PORT_SNK, TYPEC_PORT_DRP };
struct device { int unused; };
struct regulator { int unused; };
struct fwnode_handle { int unused; };
struct tcpm_port { int unused; };
struct regmap { int unused; };
struct mutex { int unused; };
struct pmic_typec_port_irq_data { int irq; };
struct pmic_typec_port {
 struct device *dev; struct tcpm_port *tcpm_port; struct regmap *regmap;
 u32 base; unsigned int nr_irqs; struct pmic_typec_port_irq_data *irq_data;
 struct regulator *vdd_vbus; bool vbus_enabled, sink_only, irqs_started;
 struct mutex vbus_lock; int cc, debouncing_cc, lock, cc_debounce_dwork;
};
struct tcpc_dev { int unused; };
struct pmic_typec { struct device *dev; struct pmic_typec_port *pmic_typec_port; struct tcpm_port *tcpm_port; struct tcpc_dev tcpc; };
#define tcpc_to_tcpm(p) ((struct pmic_typec *)((char *)(p)-offsetof(struct pmic_typec,tcpc)))
static unsigned regs[65536], reads, writes, attempts, irqs, debounces, events;
static int read_errno, fail_at, regulator_errno, enables, disables, polls;
static unsigned addresses[32], values[32];
static struct regulator regulator;
static struct fwnode_handle connector;
static bool connector_present;
static const char *role;
static struct regulator *connector_supply, *legacy_supply;
static int node_gets, node_puts, optional_legacy_gets, required_legacy_gets;
static void reset(void) {
 memset(regs,0,sizeof(regs)); reads=writes=attempts=irqs=debounces=events=0;
 read_errno=fail_at=regulator_errno=enables=disables=polls=0;
 node_gets=node_puts=optional_legacy_gets=required_legacy_gets=0;
 connector_present=true; role="sink";
 connector_supply=legacy_supply=ERR_PTR(-ENODEV);
}
static int regmap_read(struct regmap *m, unsigned a, unsigned *v) {
 (void)m; reads++; if(read_errno) return read_errno; *v=regs[a]; return 0;
}
static int regmap_write(struct regmap *m, unsigned a, unsigned v) {
 (void)m; attempts++; if ((int)attempts==fail_at) return -EIO;
 assert(writes<32); addresses[writes]=a; values[writes++]=v; regs[a]=v; return 0;
}
static int regmap_update_bits(struct regmap *m, unsigned a, unsigned mask, unsigned v) {
 return regmap_write(m,a,(regs[a]&~mask)|(v&mask));
}
#define regmap_read_poll_timeout(m,a,v,c,t,to) (polls++, (v)=regs[a], (c)?0:-ETIMEDOUT)
static int regulator_enable(struct regulator *r) { assert(r && !IS_ERR(r)); enables++; return regulator_errno; }
static int regulator_disable(struct regulator *r) { assert(r && !IS_ERR(r)); disables++; return regulator_errno; }
static void tcpm_vbus_change(struct tcpm_port *p) { (void)p; events++; }
static void qcom_pmic_set_cc_debounce(struct pmic_typec_port *p) { p->debouncing_cc=true; debounces++; }
static const char *rp_sel_to_name(int n) { (void)n; return "rp"; }
static const char *str_on_off(bool b) { return b?"on":"off"; }
static void enable_irq(int n) { (void)n; irqs++; }
static void disable_delayed_work_sync(int *p) { (void)p; }
static struct fwnode_handle *device_get_named_child_node(struct device *d, const char *n) {
 (void)d; assert(!strcmp(n,"connector")); if(!connector_present) return NULL; node_gets++; return &connector;
}
static int fwnode_property_read_string(struct fwnode_handle *f, const char *n, const char **s) {
 assert(f==&connector && !strcmp(n,"power-role")); if(!role) return -EINVAL; *s=role; return 0;
}
static void *to_of_node(struct fwnode_handle *f) { return f; }
static struct regulator *devm_of_regulator_get_optional(struct device *d, void *n, const char *s) {
 (void)d; assert(n==&connector && !strcmp(s,"vbus")); return connector_supply;
}
static struct regulator *devm_regulator_get_optional(struct device *d, const char *s) {
 (void)d; assert(!strcmp(s,"vdd-vbus")); optional_legacy_gets++; return legacy_supply;
}
static struct regulator *devm_regulator_get(struct device *d, const char *s) {
 (void)d; assert(!strcmp(s,"vdd-vbus")); required_legacy_gets++; return legacy_supply;
}
static void fwnode_handle_put(struct fwnode_handle *f) { assert(f==&connector); node_puts++; }
'''
defines = source[source.index('#define TYPEC_SNK_STATUS_REG'):source.index('struct pmic_typec_port_irq_data {')]
interrupt_defines = source[source.index('#define TYPEC_INTR_EN_CFG_1_MASK'):source.index('static int qcom_pmic_typec_port_start(')]
tests = r'''
static struct device dev;
static struct regmap regmap;
static struct pmic_typec_port_irq_data irq_data[2];
static struct pmic_typec_port port;
static struct pmic_typec tcpm;
static void setup(bool sink) {
 reset(); memset(&port,0,sizeof(port)); memset(&tcpm,0,sizeof(tcpm));
 port.dev=&dev; port.regmap=&regmap; port.base=0x1500; port.sink_only=sink;
 port.vdd_vbus=&regulator; port.irq_data=irq_data; port.nr_irqs=2;
 tcpm.dev=&dev; tcpm.pmic_typec_port=&port;
}
int main(void) {
 /* Optional source supply is absent only for an explicit sink. */
 setup(false); assert(!qcom_pmic_typec_port_get_vbus_supply(&dev,&port));
 assert(port.sink_only && !port.vdd_vbus && optional_legacy_gets==1 && !required_legacy_gets && node_gets==node_puts);
 const int faults[]={-EPROBE_DEFER,-EIO,-EINVAL};
 for(unsigned i=0;i<3;i++) {
  setup(false); connector_supply=ERR_PTR(faults[i]);
  assert(qcom_pmic_typec_port_get_vbus_supply(&dev,&port)==faults[i]);
  assert(node_gets==node_puts && !optional_legacy_gets && !required_legacy_gets);
  setup(false); legacy_supply=ERR_PTR(faults[i]);
  assert(qcom_pmic_typec_port_get_vbus_supply(&dev,&port)==faults[i]); assert(node_gets==node_puts);
 }
 setup(false); connector_supply=&regulator;
 assert(!qcom_pmic_typec_port_get_vbus_supply(&dev,&port) && port.vdd_vbus==&regulator && !optional_legacy_gets && node_gets==node_puts);
 setup(false); legacy_supply=&regulator;
 assert(!qcom_pmic_typec_port_get_vbus_supply(&dev,&port) && port.vdd_vbus==&regulator && optional_legacy_gets==1 && node_gets==node_puts);
 const char *roles[]={"source","dual",NULL,"Sink"};
 for(unsigned i=0;i<4;i++) {
  setup(false); role=roles[i]; legacy_supply=&regulator;
  assert(!qcom_pmic_typec_port_get_vbus_supply(&dev,&port));
  assert(!port.sink_only && required_legacy_gets==1 && !optional_legacy_gets && node_gets==node_puts);
 }
 setup(false); role="dual";
 assert(qcom_pmic_typec_port_get_vbus_supply(&dev,&port)==-ENODEV && node_gets==node_puts);
 setup(false); connector_present=false;
 assert(qcom_pmic_typec_port_get_vbus_supply(&dev,&port)==-EINVAL && !node_gets && !node_puts);
 puts("PASS supply ownership, absence, defer/errors, references");
 /* Neither VBUS nor VCONN source-enable may touch hardware in sink mode. */
 setup(true); port.vdd_vbus=NULL;
 assert(qcom_pmic_typec_port_set_vbus(&tcpm.tcpc,true,false)==-EOPNOTSUPP);
 assert(qcom_pmic_typec_port_set_vconn(&tcpm.tcpc,true)==-EOPNOTSUPP);
 assert(!qcom_pmic_typec_port_set_vbus(&tcpm.tcpc,false,true));
 assert(!reads && !writes && !enables && !disables && !polls && !port.vbus_enabled);
 assert(!qcom_pmic_typec_port_set_vconn(&tcpm.tcpc,false));
 assert(!(regs[port.base+TYPEC_VCONN_CONTROL_REG]&VCONN_EN_VALUE));
 setup(false); regs[port.base+TYPEC_SM_STATUS_REG]=TYPEC_SM_VBUS_VSAFE5V;
 assert(!qcom_pmic_typec_port_set_vbus(&tcpm.tcpc,true,false));
 assert(port.vbus_enabled && enables==1 && polls==1 && events==1);
 puts("PASS sink source rejection and existing source path");
 /* OPEN really removes Rd; Rd restores it, and failures do not update cache. */
 setup(true); port.cc=TYPEC_CC_RD;
 assert(!qcom_pmic_typec_port_set_cc(&tcpm.tcpc,TYPEC_CC_OPEN));
 assert(writes==1 && addresses[0]==port.base+TYPEC_MODE_CFG_REG && values[0]==TYPEC_DISABLE_CMD && port.cc==TYPEC_CC_OPEN);
 assert(!qcom_pmic_typec_port_set_cc(&tcpm.tcpc,TYPEC_CC_RD));
 assert(writes==2 && values[1]==EN_SNK_ONLY && port.cc==TYPEC_CC_RD);
 for(int cc=TYPEC_CC_RP_DEF;cc<=TYPEC_CC_RP_3_0;cc++) {
  setup(true); assert(qcom_pmic_typec_port_set_cc(&tcpm.tcpc,cc)==-EOPNOTSUPP && !reads && !writes);
 }
 setup(true); assert(qcom_pmic_typec_port_set_cc(&tcpm.tcpc,TYPEC_CC_RA)==-EOPNOTSUPP && !reads);
 setup(true); port.cc=TYPEC_CC_RD; fail_at=1;
 assert(qcom_pmic_typec_port_set_cc(&tcpm.tcpc,TYPEC_CC_OPEN)==-EIO && port.cc==TYPEC_CC_RD && !debounces);
 setup(true); read_errno=-EIO;
 assert(qcom_pmic_typec_port_set_cc(&tcpm.tcpc,TYPEC_CC_OPEN)==-EIO && !attempts);
 setup(false); assert(!qcom_pmic_typec_port_set_cc(&tcpm.tcpc,TYPEC_CC_RP_1_5));
 assert(writes==1 && addresses[0]==port.base+TYPEC_CURRSRC_CFG_REG && values[0]==TYPEC_SRC_RP_SEL_180UA);
 puts("PASS actual OPEN/Rd writes, unsupported Rp, I/O errors, legacy Rp");
 /* Startup never enters DRP for the fixed sink. Toggling honors same role. */
 setup(true); assert(!qcom_pmic_typec_port_start(&tcpm,NULL));
 assert(regs[port.base+TYPEC_MODE_CFG_REG]==EN_SNK_ONLY && irqs==2);
 setup(false); assert(!qcom_pmic_typec_port_start(&tcpm,NULL));
 assert(regs[port.base+TYPEC_MODE_CFG_REG]==EN_TRY_SNK && irqs==2);
 for(int f=1;f<=5;f++) {
  setup(true); fail_at=f; assert(qcom_pmic_typec_port_start(&tcpm,NULL)==-EIO && !irqs);
 }
 setup(true); assert(qcom_pmic_typec_port_start_toggling(&tcpm.tcpc,TYPEC_PORT_DRP,TYPEC_CC_RD)==-EOPNOTSUPP && !reads && !writes);
 assert(qcom_pmic_typec_port_start_toggling(&tcpm.tcpc,TYPEC_PORT_SRC,TYPEC_CC_RP_DEF)==-EOPNOTSUPP && !reads && !writes);
 assert(!qcom_pmic_typec_port_start_toggling(&tcpm.tcpc,TYPEC_PORT_SNK,TYPEC_CC_RD));
 assert(writes==2 && values[0]==TYPEC_DISABLE_CMD && values[1]==EN_SNK_ONLY);
 setup(true); fail_at=2;
 assert(qcom_pmic_typec_port_start_toggling(&tcpm.tcpc,TYPEC_PORT_SNK,TYPEC_CC_RD)==-EIO && writes==1 && regs[port.base+TYPEC_MODE_CFG_REG]==TYPEC_DISABLE_CMD);
 puts("PASS fixed-role startup, toggle rejection, partial-write failure");
 return 0;
}
'''
code = prefix + defines + interrupt_defines + ''.join(function(n) for n in names) + tests
with tempfile.TemporaryDirectory(prefix='tcpm-sink-port-') as temp:
    c, binary = Path(temp)/'port.c', Path(temp)/'port-test'
    c.write_text(code)
    argv = ['cc','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-sign-compare','-fsanitize=address,undefined','-fno-omit-frame-pointer','-g',str(c),'-o',str(binary)]
    built = subprocess.run(argv, capture_output=True, text=True)
    print(built.stdout + built.stderr, end='')
    assert built.returncode == 0
    run = subprocess.run([str(binary)], capture_output=True, text=True)
    print(run.stdout + run.stderr, end='')
    assert run.returncode == 0
result = dict(passed=True, functions=names, candidate_sha256=hashlib.sha256(source.encode()).hexdigest(), harness_sha256=hashlib.sha256(code.encode()).hexdigest(), groups=run.stdout.splitlines(), sanitizers=['address','undefined'], kernel_boundaries_mocked=True, phone_test=False)
(HERE/'test-result.json').write_text(json.dumps(result,indent=2)+'\n')
