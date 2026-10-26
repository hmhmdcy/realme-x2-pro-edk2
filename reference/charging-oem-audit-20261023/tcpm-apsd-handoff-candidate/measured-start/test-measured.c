/* Executes production measured helper and actual extracted PHY callbacks. */
#include "qcom_pmic_typec_apsd.c"
#include "qcom_pmic_typec.h"
#include <stdio.h>
#include <stdlib.h>

struct regulator { int refs, enables, disables, enable_error, disable_error; };
struct work_struct { int unused; };
typedef unsigned int u32;
typedef int spinlock_t;
#define spin_lock_irqsave(p,f) do { (f)=0;spin_depth++; } while(0)
#define spin_unlock_irqrestore(p,f) do { (void)(f);spin_depth--; } while(0)
static int spin_depth;
#define USB_PDPHY_BIST_MODE_REG 0x4e
#define USB_PDPHY_TX_CONTROL_REG 0x44
#define USB_PDPHY_FRAME_FILTER_REG 0x4c
#define USB_PDPHY_EN_CONTROL_REG 0x46

static int cases, io_count, fail_io, slow_adc, adc_error_call, adc_calls;
static int qc_change_adc, role_change_adc, writes, pd_reads, pd_writes;
static int reset_error, resets, irq_on, irq_off, cancelled, worker_joined;
static int owner_joins, owner_releases, adc_uv=5000000, require_preflight;
static s64 test_ms;
static void (*actions[8])(void *);
static void *action_data[8], *allocated;
static int nr_actions;
static struct regulator regulator;
static struct regmap map;
static struct device dev;

#define CHECK(e) do { cases++;if(!(e)){fprintf(stderr,"line %d: %s\n",__LINE__,#e);abort();}}while(0)
void *devm_kzalloc(struct device *d,size_t n,int flags) { allocated=calloc(1,n);return allocated; }
int devm_add_action_or_reset(struct device *d,void (*fn)(void *),void *p)
{ actions[nr_actions]=fn;action_data[nr_actions++]=p;return 0; }
int samurai_apsd_tcpm_quiesce(struct device *d,struct regmap *m) { owner_joins++;worker_joined=1;return 0; }
void samurai_apsd_tcpm_release(struct device *d) { owner_releases++; }
s64 ktime_get_boottime(void) { return ++test_ms; }
s64 ktime_to_ms(s64 v) { return v; }
void msleep(unsigned int ms) { test_ms+=ms; }
static int io(unsigned int reg)
{
	io_count++;
	if(reg>=0x1700 && reg<0x1800) { CHECK(regulator.refs>0);pd_reads++; }
	return io_count==fail_io ? -EIO : 0;
}
int regmap_read(struct regmap *m,unsigned int reg,unsigned int *v)
{ int ret=io(reg);if(ret)return ret;*v=m->r[reg];return 0; }
int regmap_update_bits(struct regmap *m,unsigned int reg,unsigned int mask,unsigned int v)
{
	CHECK(worker_joined && !spin_depth);
	CHECK((reg==0x1362 && mask==0x6c)||(reg==0x1358 && mask==0x80));
	CHECK(v==0);writes++;
	if(io(reg))return -EIO;
	m->r[reg]=(m->r[reg]&~mask)|v;return 0;
}
static int regmap_write(struct regmap *m,unsigned int reg,unsigned int v)
{
	CHECK(regulator.refs>0 && resets>0);pd_writes++;
	if(io(reg))return -EIO;
	m->r[reg]=v;return 0;
}
static int regulator_enable(struct regulator *r)
{
	CHECK(!spin_depth);
	if(require_preflight)CHECK(adc_calls>=2 && worker_joined && adc_uv>=4750000 && adc_uv<=5500000);
	r->enables++;
	if(r->enable_error)return r->enable_error;
	r->refs++;return 0;
}
static int regulator_disable(struct regulator *r)
{
	CHECK(!spin_depth && r->refs>0);r->disables++;
	if(r->disable_error)return r->disable_error;
	r->refs--;return 0;
}
static void enable_irq(int irq) { irq_on++; }
static void disable_irq(int irq) { irq_off++; }
static void cancel_work_sync(struct work_struct *work) { cancelled++; }
#include "phy-structs.inc"
static int pmic_typec_pdphy_reset(struct pmic_typec_pdphy *p)
{ CHECK(p->supply_held && !p->handoff_powered && regulator.refs==1);resets++;return reset_error; }
#include "phy-functions.inc"

static int read_adc(void *context,int *uv)
{
	CHECK(!spin_depth);adc_calls++;
	if(adc_calls==slow_adc)test_ms+=300;
	if(adc_calls==qc_change_adc)map.r[0x1307]|=2;
	if(adc_calls==role_change_adc)map.r[0x150b]^=2;
	if(adc_calls==adc_error_call)return -EIO;
	*uv=adc_uv;return 0;
}
static const struct qcom_pmic_typec_apsd_start_ops ops={
	.read_vbus_uv=read_adc,.quiet_begin=qcom_pmic_typec_pdphy_apsd_begin,
	.quiet_verify=qcom_pmic_typec_pdphy_apsd_verify,
	.quiet_release=qcom_pmic_typec_pdphy_apsd_release,
};
static struct pmic_typec tcpm;
static struct pmic_typec_pdphy phy;
static struct pmic_typec_pdphy_irq_data irqs[2];

static void cleanup(void)
{
	while(nr_actions){nr_actions--;actions[nr_actions](action_data[nr_actions]);}
	free(allocated);allocated=NULL;
}
static void fresh(bool connected)
{
	cleanup();
	memset(&map,0,sizeof(map));memset(&regulator,0,sizeof(regulator));
	memset(&tcpm,0,sizeof(tcpm));memset(&phy,0,sizeof(phy));
	io_count=fail_io=slow_adc=adc_error_call=adc_calls=qc_change_adc=role_change_adc=0;
	writes=pd_reads=pd_writes=reset_error=resets=irq_on=irq_off=cancelled=0;
	owner_joins=owner_releases=worker_joined=spin_depth=0;test_ms=0;adc_uv=5000000;
	map.r[0x1362]=connected?0x9b:0xff;map.r[0x1358]=0xff;
	map.r[0x150a]=connected?0x20:0x40;
	if(connected){map.r[0x1310]=0x10;map.r[0x1506]=8;map.r[0x1509]=0x20;map.r[0x150b]=0x29;map.r[0x150d]=2;}
	phy.dev=&dev;phy.regmap=&map;phy.base=0x1700;phy.vdd_pdphy=&regulator;
	phy.nr_irqs=2;phy.irq_data=irqs;tcpm.dev=&dev;tcpm.pmic_typec_pdphy=&phy;
	tcpm.samurai_contract_shutdown=true;require_preflight=connected;
	CHECK(!devm_add_action_or_reset(&dev,qcom_pmic_typec_pdphy_apsd_cleanup,&tcpm));
}
static struct qcom_pmic_typec_apsd *prepare(const struct qcom_pmic_typec_apsd_start_ops *o)
{ return qcom_pmic_typec_apsd_prepare(&dev,&map,o,&tcpm); }
static void finish(void)
{
	qcom_pmic_typec_pdphy_quiesce_5v(&tcpm);
	tcpm.tcpm_port=NULL;tcpm.samurai_joined=true;
	CHECK(qcom_pmic_typec_pdphy_finish_5v(&tcpm)==0);
}
int main(void)
{
	struct qcom_pmic_typec_apsd *h;
	struct tcpm_port *port=(void *)0x1000;
	int max_io,i,before;
	const unsigned int controls[]={0x174e,0x1744,0x174c,0x1746};
	const int voltages[]={4749999,5500001,9000000,0,-1,5000};
	const int good_voltages[]={4750000,5000000,5500000};
	struct qcom_pmic_typec_apsd_start_ops missing;

	fresh(false);h=prepare(NULL);
	CHECK(!IS_ERR(h) && writes==2 && !adc_calls && !pd_reads && !regulator.enables);
	CHECK(qcom_pmic_typec_apsd_verify(h)==0);
	CHECK(map.r[0x1362]==0x93 && map.r[0x1358]==0x7f);
	cleanup();CHECK(!regulator.disables);

	fresh(true);h=prepare(&ops);
	CHECK(!IS_ERR(h));max_io=io_count;
	CHECK(adc_calls==6 && regulator.enables==1 && regulator.refs==1 && !regulator.disables);
	CHECK(phy.handoff_powered && !phy.supply_held && !resets && !pd_writes);
	CHECK(map.r[0x1362]==0x93 && map.r[0x1358]==0x7f);
	CHECK(qcom_pmic_typec_pdphy_apsd_begin(&tcpm)==-EBUSY && regulator.enables==1);
	/* This is the actual production start: same ref, then original protocol. */
	tcpm.apsd_handoff=h;tcpm.tcpm_port=port;
	CHECK(qcom_pmic_typec_pdphy_start(&tcpm,port)==0);
	CHECK(regulator.enables==1 && regulator.refs==1 && phy.supply_held && !phy.handoff_powered);
	CHECK(resets==1 && irq_on==2 && phy.tcpm_port==port);
	CHECK(qcom_pmic_typec_pdphy_apsd_release(&tcpm)==0 && !regulator.disables);
	finish();CHECK(regulator.refs==0 && regulator.disables==1 && irq_off==2 && cancelled==1);
	cleanup();CHECK(regulator.disables==1);

	/* Every PMIC call of measured takeover can fail; real pre-start supply
	 * ownership is cleaned, not merely its model bit reset.
	 */
	for(i=1;i<=max_io;i++){
		fresh(true);fail_io=i;h=prepare(&ops);
		CHECK(IS_ERR(h) && PTR_ERR(h)==-EIO);
		CHECK(!regulator.refs && !phy.handoff_powered && !resets && !irq_on && !pd_writes);
	}
	for(i=0;i<(int)ARRAY_SIZE(voltages);i++){
		fresh(true);adc_uv=voltages[i];h=prepare(&ops);
		CHECK(IS_ERR(h) && PTR_ERR(h)==-ERANGE && !regulator.enables && !writes);
	}
	for(i=0;i<(int)ARRAY_SIZE(good_voltages);i++){
		fresh(true);adc_uv=good_voltages[i];map.r[0x1506]=i==0?8:i==1?4:2;
		h=prepare(&ops);CHECK(!IS_ERR(h));cleanup();CHECK(regulator.refs==0);
	}
	/* Missing proof is never equivalent to physical 5V or quiet PD. */
	for(i=0;i<4;i++){
		fresh(true);missing=ops;
		switch(i){case 0:missing.read_vbus_uv=NULL;break;case 1:missing.quiet_begin=NULL;break;
		case 2:missing.quiet_verify=NULL;break;case 3:missing.quiet_release=NULL;break;}
		h=prepare(&missing);CHECK(IS_ERR(h) && PTR_ERR(h)==-EOPNOTSUPP && !regulator.enables);
	}
	/* Individual physical-role, QC and comparator negatives. */
	for(i=0;i<17;i++){
		fresh(true);
		switch(i){
		case 0:map.r[0x1310]=0;break;case 1:map.r[0x1310]|=1;break;
		case 2:map.r[0x1509]=0;break;case 3:map.r[0x150b]&=~0x20;break;
		case 4:map.r[0x150b]&=~1;break;case 5:map.r[0x150b]&=~8;break;
		case 6:map.r[0x150b]|=0x40;break;case 7:map.r[0x150b]|=0x80;break;
		case 8:map.r[0x150b]|=0x10;break;case 9:map.r[0x1506]=3;break;
		case 10:map.r[0x150d]|=1;break;case 11:map.r[0x150a]|=0x40;break;
		case 12:map.r[0x150a]=0;break;case 13:map.r[0x1307]|=2;break;
		case 14:map.r[0x1308]=0x20;break;case 15:map.r[0x1308]=0x40;break;
		case 16:map.r[0x1362]|=0x64;break;}
		h=prepare(&ops);CHECK(IS_ERR(h) && !regulator.enables && !writes);
	}
	for(i=1;i<=6;i++){
		fresh(true);adc_error_call=i;h=prepare(&ops);
		CHECK(IS_ERR(h) && PTR_ERR(h)==-EIO && !regulator.refs);
		fresh(true);slow_adc=i;h=prepare(&ops);
		CHECK(IS_ERR(h) && PTR_ERR(h)==-EAGAIN && !regulator.refs);
		fresh(true);qc_change_adc=i;h=prepare(&ops);
		CHECK(IS_ERR(h) && PTR_ERR(h)==-EBUSY && !regulator.refs);
		fresh(true);role_change_adc=i;h=prepare(&ops);
		CHECK(IS_ERR(h) && PTR_ERR(h)==-ESTALE && !regulator.refs);
	}
	/* Existing nonzero controls are read, refused and never reset/replayed. */
	for(i=0;i<4;i++){
		fresh(true);map.r[controls[i]]=1;h=prepare(&ops);
		CHECK(IS_ERR(h) && PTR_ERR(h)==-EBUSY);
		CHECK(regulator.enables==1 && regulator.disables==1 && !regulator.refs && !pd_writes);
	}
	fresh(true);regulator.enable_error=-EIO;h=prepare(&ops);
	CHECK(IS_ERR(h) && PTR_ERR(h)==-EIO && !pd_reads && !regulator.refs && !regulator.disables);
	fresh(true);map.r[0x1746]=1;regulator.disable_error=-EIO;h=prepare(&ops);
	CHECK(IS_ERR(h) && phy.handoff_powered && regulator.refs==1);
	regulator.disable_error=0;cleanup();CHECK(!regulator.refs && !phy.handoff_powered);

	/* A failed protocol startup retains the transferred reference until
	 * original IRQ/work/TCPM join -> finish. Devres never steals that ref.
	 */
	fresh(true);h=prepare(&ops);CHECK(!IS_ERR(h));tcpm.apsd_handoff=h;tcpm.tcpm_port=port;reset_error=-EIO;
	CHECK(qcom_pmic_typec_pdphy_start(&tcpm,port)==-EIO);
	CHECK(phy.supply_held && !phy.handoff_powered && regulator.refs==1 && !regulator.disables);
	cleanup();CHECK(regulator.refs==1 && !regulator.disables);
	finish();CHECK(!regulator.refs && regulator.disables==1);
	/* No reference: provider verifier must not touch unpowered analogue IO. */
	fresh(true);before=io_count;
	CHECK(qcom_pmic_typec_pdphy_apsd_verify(&tcpm)==-EBUSY && io_count==before);
	tcpm.tcpm_port=port;CHECK(qcom_pmic_typec_pdphy_apsd_begin(&tcpm)==-EBUSY && !regulator.enables);
	tcpm.tcpm_port=NULL;phy.irqs_started=true;
	CHECK(qcom_pmic_typec_pdphy_apsd_begin(&tcpm)==-EBUSY && !regulator.enables);phy.irqs_started=false;
	cleanup();CHECK(!regulator.refs);
	printf("measured helper + actual PHY supplier: %d assertions; %d PMIC IO fault points\n",cases,max_io);
	return 0;
}
