/* Existing function behavior only; no fabricated PD-safe gate implementation. */
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <errno.h>
#define BIT(n) (1U << (n))
#define container_of(p,t,m) ((t *)((char *)(p)-offsetof(t,m)))
typedef uint32_t u32;
typedef int irqreturn_t;
#define IRQ_HANDLED 1
#define GFP_ATOMIC 0
#define dev_err(dev,...) ((void)(dev))
#define dev_dbg(dev,...) ((void)(dev))
#define str_on_off(on) ((on)?"on":"off")
#define spin_lock_irqsave(lock,flags) do {(flags)=0;spin_lock(lock);} while(0)
#define spin_unlock_irqrestore(lock,flags) do {(void)(flags);spin_unlock(lock);} while(0)
struct device { int tag; };
struct regmap { int tag; };
struct mutex { int depth; };
typedef struct { int depth; } spinlock_t;
static void mutex_lock(struct mutex *m) { assert(!m->depth);m->depth=1; }
static void mutex_unlock(struct mutex *m) { assert(m->depth);m->depth=0; }
static void spin_lock(spinlock_t *m) { assert(!m->depth);m->depth=1; }
static void spin_unlock(spinlock_t *m) { assert(m->depth);m->depth=0; }
struct kthread_work { void (*fn)(struct kthread_work *); };
struct work_struct { int pending; };
struct kthread_worker { int tag; };
enum tcpm_transmit_type { TCPC_TX_SOP };
enum tcpm_transmit_status { TCPC_TX_SUCCESS, TCPC_TX_DISCARDED, TCPC_TX_FAILED };
struct pd_message { uint16_t header;uint32_t payload[7]; };
struct tcpm_port { spinlock_t pd_event_lock;u32 pd_events;struct kthread_worker *wq;struct kthread_work event_work;bool pd_capable,explicit_contract; };
struct pd_rx_event { struct kthread_work work;struct tcpm_port *port;struct pd_message msg;enum tcpm_transmit_type rx_sop_type; };
struct pmic_typec_pdphy { struct device *dev;struct tcpm_port *tcpm_port;struct regmap *regmap;u32 base;struct work_struct reset_work;spinlock_t lock; };
struct pmic_typec_port { struct device *dev;struct regmap *regmap;u32 base;bool vbus_enabled;struct mutex vbus_lock; };
struct tcpc_dev { int tag; };
struct pmic_typec { struct device *dev;struct tcpc_dev tcpc;struct pmic_typec_pdphy *pmic_typec_pdphy;struct pmic_typec_port *pmic_typec_port; };
struct pmic_typec_pdphy_irq_data { int virq,irq;struct pmic_typec_pdphy *pmic_typec_pdphy; };
#define tcpc_to_tcpm(p) container_of(p,struct pmic_typec,tcpc)
#define TYPEC_MISC_STATUS_REG 0x0b
#define TYPEC_VBUS_DETECT BIT(5)
#define USB_PDPHY_RX_ACKNOWLEDGE_REG 0x4b
#define USB_PDPHY_MSG_CONFIG_REG 0x40
#define MSG_CONFIG_PORT_DATA_ROLE BIT(3)
#define MSG_CONFIG_PORT_POWER_ROLE BIT(2)
#define TCPM_CC_EVENT BIT(0)
#define TCPM_RESET_EVENT BIT(2)
#define PMIC_PDPHY_SIG_TX_IRQ 0
#define PMIC_PDPHY_SIG_RX_IRQ 1
#define PMIC_PDPHY_MSG_TX_IRQ 2
#define PMIC_PDPHY_MSG_RX_IRQ 3
#define PMIC_PDPHY_MSG_TX_FAIL_IRQ 4
#define PMIC_PDPHY_MSG_TX_DISCARD_IRQ 5
enum typec_role { TYPEC_SINK,TYPEC_SOURCE };
enum typec_data_role { TYPEC_DEVICE,TYPEC_HOST };
static int queued,logs[16],nlog,io_errno,reads,writes,alloc_fail;
static u32 read_word,last_reg,last_value,last_mask;
static void *allocation;
static void tcpm_pd_rx_handler(struct kthread_work *w) { (void)w;assert(0); }
static void *fake_alloc(size_t size) { if(alloc_fail)return NULL;assert(!allocation);return allocation=calloc(1,size); }
#define kzalloc_obj(what,flags) fake_alloc(sizeof(what))
static void kthread_init_work(struct kthread_work *w,void (*fn)(struct kthread_work *)) {w->fn=fn;}
static bool kthread_queue_work(struct kthread_worker *q,struct kthread_work *w) {(void)q;(void)w;queued++;logs[nlog++]=3;return false;}
static bool schedule_work(struct work_struct *w) {w->pending=1;return true;}
static int regmap_read(struct regmap *m,u32 reg,unsigned int *word) {(void)m;reads++;last_reg=reg;if(!io_errno)*word=read_word;return io_errno;}
static int regmap_write(struct regmap *m,u32 reg,u32 value) {(void)m;writes++;last_reg=reg;last_value=value;return io_errno;}
static int regmap_update_bits(struct regmap *m,u32 reg,u32 mask,u32 value) {last_mask=mask;return regmap_write(m,reg,value);}
static void qcom_pmic_typec_pdphy_reset_on(struct pmic_typec_pdphy *p) {(void)p;logs[nlog++]=1;}
static void qcom_pmic_typec_pdphy_reset_off(struct pmic_typec_pdphy *p) {(void)p;logs[nlog++]=2;}
static void tcpm_pd_transmit_complete(struct tcpm_port *p,enum tcpm_transmit_status x) {(void)p;(void)x;}
static void qcom_pmic_typec_pdphy_pd_receive(struct pmic_typec_pdphy *p) {(void)p;}
#include "actual-functions.inc"
int main(void) {
 struct device dev={0};struct regmap map={0};struct tcpm_port port={0};
 struct pmic_typec_pdphy pd={.dev=&dev,.tcpm_port=&port,.regmap=&map,.base=0x1700};
 struct pmic_typec_port cc={.dev=&dev,.regmap=&map,.base=0x1500};
 struct pmic_typec tcpm={.dev=&dev,.pmic_typec_pdphy=&pd,.pmic_typec_port=&cc};
 struct pd_message msg={.header=0x1234};
 tcpm_pd_receive(&port,&msg,TCPC_TX_SOP);
 assert(queued==1 && port.pd_events==0 && !port.pd_capable && !port.explicit_contract);
 assert(((struct pd_rx_event *)allocation)->msg.header==0x1234);
 free(allocation);allocation=NULL;alloc_fail=1;tcpm_pd_receive(&port,&msg,TCPC_TX_SOP);
 assert(queued==1 && port.pd_events==0);alloc_fail=0;
 puts("ok actual PD RX has a separate pending work path; allocation failure has no shared-state event");
 struct pmic_typec_pdphy_irq_data irq={.virq=PMIC_PDPHY_SIG_RX_IRQ,.pmic_typec_pdphy=&pd};
 nlog=0;queued=0;qcom_pmic_typec_pdphy_isr(0,&irq);
 assert(pd.reset_work.pending==1 && port.pd_events==0 && nlog==0);
 qcom_pmic_typec_pdphy_sig_reset_work(&pd.reset_work);
 assert(nlog==3 && logs[0]==1 && logs[1]==2 && logs[2]==3 && port.pd_events==TCPM_RESET_EVENT);
 puts("ok actual SIG_RX/reset work changes PDPHY before TCPM hard-reset notification");
 port.explicit_contract=true;port.pd_capable=true;writes=0;
 assert(qcom_pmic_typec_pdphy_set_pd_rx(&tcpm.tcpc,false)==0);
 assert(writes==1 && last_reg==0x174b && last_value==1 && port.explicit_contract && port.pd_capable);
 assert(qcom_pmic_typec_pdphy_set_roles(&tcpm.tcpc,true,TYPEC_SINK,TYPEC_DEVICE)==0);
 assert(last_reg==0x1740 && last_mask==12 && last_value==0 && port.explicit_contract);
 puts("ok actual RX-disable/role callbacks do not clear or report the TCPM PD contract");
 io_errno=-EIO;reads=0;assert(qcom_pmic_typec_port_get_vbus(&tcpm.tcpc)==0 && reads==1);
 cc.vbus_enabled=true;reads=0;assert(qcom_pmic_typec_port_get_vbus(&tcpm.tcpc)==1 && reads==0);
 cc.vbus_enabled=false;io_errno=0;read_word=TYPEC_VBUS_DETECT;
 assert(qcom_pmic_typec_port_get_vbus(&tcpm.tcpc)==1);
 puts("ok actual VBUS callback erases read errno and cached source enable is not a fresh sink proof");
 port.pd_events=0;queued=0;nlog=0;tcpm_cc_change(&port);tcpm_cc_change(&port);
 assert(port.pd_events==TCPM_CC_EVENT && queued==2);
 puts("ok actual CC event bit coalesces repeated events; it is not a unique cancellation generation");
 return 0;
}
