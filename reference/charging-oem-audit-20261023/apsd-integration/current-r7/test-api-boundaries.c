/* Unmodified actual functions. Fake OS objects only; no hardware access. */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#define EXPORT_SYMBOL_GPL(x)
#define KOBJ_CHANGE 1
#define __must_hold(x)
#define IS_ERR_OR_NULL(x) (!(x))
#define trace_usb_gadget_connect(g,r) ((void)0)
#define trace_usb_gadget_disconnect(g,r) ((void)0)
#define trace_usb_gadget_activate(g,r) ((void)0)
#define trace_usb_gadget_deactivate(g,r) ((void)0)
#define spin_lock_irqsave(l,f) do { (f)=0;assert(!*(l));++*(l); }while(0)
#define spin_unlock_irqrestore(l,f) do { (void)(f);assert(*(l)==1);--*(l); }while(0)
typedef uint32_t u32;
enum phy_mode {PHY_MODE_INVALID,PHY_MODE_USB_HOST,PHY_MODE_USB_DEVICE};
enum usb_dr_mode {USB_DR_MODE_UNKNOWN,USB_DR_MODE_HOST,USB_DR_MODE_PERIPHERAL,USB_DR_MODE_OTG};
enum usb_role {USB_ROLE_NONE,USB_ROLE_HOST,USB_ROLE_DEVICE};
#define DWC3_GCTL_PRTCAP_HOST 1
#define DWC3_GCTL_PRTCAP_DEVICE 2
struct phy;
struct phy_ops {int(*set_mode)(struct phy *,enum phy_mode,int);};
struct qcom_snps_hsphy {enum phy_mode mode;};
struct phy {int mutex;struct phy_ops *ops;struct {enum phy_mode mode;}attrs;struct qcom_snps_hsphy *data;};
static void *phy_get_drvdata(struct phy *p){return p->data;}
static void mutex_lock(int *l){assert(!*l);++*l;}
static void mutex_unlock(int *l){assert(*l==1);--*l;}
struct dwc3;
struct usb_role_switch {struct dwc3 *data;bool registered;int lock;enum usb_role role;
 int(*set)(struct usb_role_switch*,enum usb_role);struct {int kobj;}dev;};
struct usb_gadget;
struct usb_gadget_ops {int(*pullup)(struct usb_gadget*,int);};
struct usb_gadget_driver {void(*disconnect)(struct usb_gadget*);};
struct usb_udc {int connect_lock;bool allow_connect,started;struct usb_gadget_driver *driver;};
struct usb_gadget {struct usb_udc *udc;struct usb_gadget_ops *ops;bool connected,deactivated;struct dwc3 *owner;};
struct dwc3 {enum usb_dr_mode dr_mode,role_switch_default_mode;u32 desired_dr_role;
 int lock,drd_work;bool softconnect,pullups_connected;void *dev;int irq_gadget,connect_mutex;};
static struct dwc3 *usb_role_switch_get_drvdata(struct usb_role_switch *s){return s->data;}
static struct dwc3 *gadget_to_dwc(struct usb_gadget *g){return g->owner;}
static int queued,pre_calls,uevents,pulls,disc_callbacks,udc_lock;
static enum usb_role last_pre;
static void *system_freezable_wq;
static void queue_work(void *q,int *w){queued++;}
static void dwc3_pre_set_role(struct dwc3 *d,enum usb_role r){pre_calls++;last_pre=r;}
static void kobject_uevent(int *k,int e){uevents++;}
static bool runtime_suspended;
static int pm_result,pm_gets,pm_puts,pm_barriers,irq_syncs,soft_discs,soft_conns,soft_error,set_suspended;
static bool pm_runtime_suspended(void *d){return runtime_suspended;}
static int pm_runtime_get_sync(void *d){pm_gets++;return pm_result;}
static void pm_runtime_put(void *d){pm_puts++;}
static void pm_runtime_barrier(void *d){pm_barriers++;}
static void pm_runtime_set_suspended(void *d){set_suspended++;}
static void synchronize_irq(int irq){irq_syncs++;}
static int dwc3_gadget_soft_disconnect(struct dwc3 *d){assert(d->connect_mutex==1);soft_discs++;return soft_error;}
static int dwc3_gadget_soft_connect(struct dwc3 *d){assert(d->connect_mutex==1);soft_conns++;return soft_error;}
static int pull_error;
static int counted_pullup(struct usb_gadget *g,int on){assert(g->udc->connect_lock==1);pulls++;return pull_error;}
static void counted_disconnect(struct usb_gadget *g){assert(udc_lock==1);disc_callbacks++;}
#include "actual-functions.inc"

static void reset(void)
{queued=pre_calls=uevents=pulls=disc_callbacks=udc_lock=0;runtime_suspended=false;
 pm_result=1;pm_gets=pm_puts=pm_barriers=irq_syncs=soft_discs=soft_conns=soft_error=set_suspended=pull_error=0;}
static void test_phy_mode_is_not_high_z(void)
{
 struct qcom_snps_hsphy state={PHY_MODE_USB_HOST};struct phy_ops ops={qcom_snps_hsphy_set_mode};
 struct phy p={.ops=&ops,.data=&state,.attrs={PHY_MODE_USB_HOST}};
 assert(phy_set_mode_ext(&p,PHY_MODE_USB_DEVICE,73)==0);
 assert(state.mode==PHY_MODE_USB_DEVICE&&p.attrs.mode==PHY_MODE_USB_DEVICE&&!p.mutex);
 assert(phy_set_mode_ext(NULL,PHY_MODE_USB_DEVICE,73)==0);
}
static void test_none_is_default_and_peripheral_ignores_setmode(void)
{
 reset();struct dwc3 d={.dr_mode=USB_DR_MODE_PERIPHERAL,.role_switch_default_mode=USB_DR_MODE_PERIPHERAL};
 struct usb_role_switch s={.data=&d,.registered=true,.set=dwc3_usb_role_switch_set};
 assert(usb_role_switch_set_role(&s,USB_ROLE_NONE)==0);
 assert(s.role==USB_ROLE_NONE&&last_pre==USB_ROLE_NONE&&pre_calls==1&&queued==0&&d.desired_dr_role==0);
 d.dr_mode=USB_DR_MODE_OTG;assert(usb_role_switch_set_role(&s,USB_ROLE_NONE)==0);
 assert(d.desired_dr_role==DWC3_GCTL_PRTCAP_DEVICE&&queued==1);
 d.role_switch_default_mode=USB_DR_MODE_HOST;assert(usb_role_switch_set_role(&s,USB_ROLE_NONE)==0);
 assert(d.desired_dr_role==DWC3_GCTL_PRTCAP_HOST&&queued==2);
 assert(usb_role_switch_set_role(NULL,USB_ROLE_NONE)==0);
}
static void test_pullup_returns_do_not_prove_halt_or_phy_mode(void)
{
 reset();struct dwc3 d={.pullups_connected=true};struct usb_gadget g={.owner=&d};
 runtime_suspended=true;assert(dwc3_gadget_pullup(&g,0)==0);
 assert(!d.softconnect&&pm_barriers==1&&!pm_gets&&!soft_discs&&!irq_syncs);
 reset();pm_result=0;assert(dwc3_gadget_pullup(&g,0)==0);assert(pm_gets==1&&!soft_discs&&pm_puts==1);
 reset();pm_result=-EIO;assert(dwc3_gadget_pullup(&g,0)==-EIO);assert(set_suspended==1&&!soft_discs);
 reset();soft_error=-ETIMEDOUT;assert(dwc3_gadget_pullup(&g,0)==-ETIMEDOUT);
 assert(soft_discs==1&&irq_syncs==1&&!d.connect_mutex&&pm_puts==1);
}
static void setup_gadget(struct usb_gadget *g,struct usb_udc *u,struct usb_gadget_ops *o,struct usb_gadget_driver *r)
{*u=(struct usb_udc){.allow_connect=true,.started=true,.driver=r};*g=(struct usb_gadget){.udc=u,.ops=o,.connected=true};}
static void test_deactivate_preserves_desire_and_activate_can_fail(void)
{
 reset();struct usb_udc u;struct usb_gadget g;struct usb_gadget_ops o={counted_pullup};struct usb_gadget_driver r={counted_disconnect};
 setup_gadget(&g,&u,&o,&r);assert(usb_gadget_deactivate(&g)==0);
 assert(g.deactivated&&g.connected&&pulls==1&&disc_callbacks==1);
 pull_error=-EIO;assert(usb_gadget_activate(&g)==-EIO);
 assert(!g.deactivated&&!g.connected&&pulls==2);
}
static void test_existing_deactivation_is_not_a_new_owner_lease(void)
{
 reset();struct usb_udc u;struct usb_gadget g;struct usb_gadget_ops o={counted_pullup};struct usb_gadget_driver r={counted_disconnect};
 setup_gadget(&g,&u,&o,&r);g.deactivated=true;
 assert(usb_gadget_deactivate(&g)==0&&pulls==0);
 assert(usb_gadget_activate(&g)==0&&!g.deactivated&&pulls==1);
}
static void test_queued_udc_connect_is_not_physical_restore(void)
{
 reset();struct usb_udc u;struct usb_gadget g;struct usb_gadget_ops o={counted_pullup};struct usb_gadget_driver r={counted_disconnect};
 setup_gadget(&g,&u,&o,&r);g.connected=false;u.allow_connect=false;
 mutex_lock(&u.connect_lock);assert(usb_gadget_connect_locked(&g)==0);mutex_unlock(&u.connect_lock);
 assert(g.connected&&!pulls);
}
int main(void)
{
 test_phy_mode_is_not_high_z();test_none_is_default_and_peripheral_ignores_setmode();
 test_pullup_returns_do_not_prove_halt_or_phy_mode();test_deactivate_preserves_desire_and_activate_can_fail();
 test_existing_deactivation_is_not_a_new_owner_lease();test_queued_udc_connect_is_not_physical_restore();
 puts("6 actual API boundary groups passed; no driver patch, no hardware");return 0;
}
