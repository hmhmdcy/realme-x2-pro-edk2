/* Actual functions, fake MMIO/PM/callback boundaries. No DMA/IRQ emulation. */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uint32_t u32;
typedef int pm_message_t;
#define BIT(x) (1U << (x))
#define DWC3_USB2_MAX_PORTS 15
#define DWC3_USB3_MAX_PORTS 4
#define DWC3_GUSB2PHYCFG(n) (0xc200U + (n) * 4U)
#define DWC3_GUSB3PIPECTL(n) (0xc2c0U + (n) * 4U)
#define DWC3_GUSB2PHYCFG_SUSPHY BIT(6)
#define DWC3_GUSB3PIPECTL_SUSPHY BIT(17)
#define DWC3_GUSB2PHYCFG_ENBLSLPM BIT(8)
#define DWC3_GCTL_PRTCAP_HOST 1
#define DWC3_GCTL_PRTCAP_DEVICE 2
#define DWC3_GCTL_PRTCAP_OTG 3
#define DWC3_OTG_ROLE_HOST 1
#define DWC3_OTG_ROLE_DEVICE 2
#define PMSG_SUSPEND 1
#define PMSG_AUTO_SUSPEND 2
#define PMSG_IS_AUTO(msg) ((msg) == PMSG_AUTO_SUSPEND)
struct device { bool runtime_suspended, wakeup; };
struct dwc3 {
 struct device *dev;
 int current_dr_role, current_otg_role, num_usb2_ports, num_usb3_ports, irq_gadget;
 bool susphy_state, needs_full_reinit, dis_u2_susphy_quirk, dis_u3_susphy_quirk;
 bool dis_enblslpm_quirk, connected, softconnect;
 void *usb2_generic_phy[DWC3_USB2_MAX_PORTS], *usb3_generic_phy[DWC3_USB3_MAX_PORTS];
};
static struct device dev;
static struct dwc3 dwc;
static u32 u2[DWC3_USB2_MAX_PORTS], u3[DWC3_USB3_MAX_PORTS];
static u32 original2[DWC3_USB2_MAX_PORTS], original3[DWC3_USB3_MAX_PORTS];
struct write { u32 address, value; };
static struct write writes[128];
static unsigned nwrites, reads2, reads3, discalls, concalls, callbacks, exits, irqjoins, pinctrls, phy_puts;
static unsigned writes_at_connect;
static int disconnect_error, connect_error;
static bool mutate_other;
static char events[256];
static unsigned nevents, cases;
static void event(char e) { assert(nevents + 1 < sizeof(events)); events[nevents++] = e; events[nevents] = 0; }
static u32 dwc3_readl(struct dwc3 *d, u32 address)
{
 assert(d == &dwc);
 if(address >= DWC3_GUSB2PHYCFG(0) && address < DWC3_GUSB2PHYCFG(DWC3_USB2_MAX_PORTS)) {
  unsigned port=(address-DWC3_GUSB2PHYCFG(0))/4;
  assert(port < (unsigned)d->num_usb2_ports); reads2++; return u2[port];
 }
 assert(address >= DWC3_GUSB3PIPECTL(0) && address < DWC3_GUSB3PIPECTL(DWC3_USB3_MAX_PORTS));
 unsigned port=(address-DWC3_GUSB3PIPECTL(0))/4;
 assert(port < (unsigned)d->num_usb3_ports); reads3++; return u3[port];
}
static void dwc3_writel(struct dwc3 *d, u32 address, u32 value)
{
 assert(d == &dwc && nwrites < 128); writes[nwrites++] = (struct write){address,value}; event('W');
 if(address >= DWC3_GUSB2PHYCFG(0) && address < DWC3_GUSB2PHYCFG(DWC3_USB2_MAX_PORTS)) {
  unsigned port=(address-DWC3_GUSB2PHYCFG(0))/4;assert(port<(unsigned)d->num_usb2_ports);u2[port]=value;
 } else {
  unsigned port=(address-DWC3_GUSB3PIPECTL(0))/4;assert(port<(unsigned)d->num_usb3_ports);u3[port]=value;
 }
}
static bool pm_runtime_suspended(struct device *d) { assert(d==&dev);return d->runtime_suspended; }
static bool device_may_wakeup(struct device *d) { assert(d==&dev);return d->wakeup; }
static void synchronize_irq(int irq) { assert(irq==9);irqjoins++;event('I'); }
static void dwc3_core_exit(struct dwc3 *d) { assert(d==&dwc);exits++;event('X'); }
static void dwc3_otg_exit(struct dwc3 *d) { assert(d==&dwc);event('O'); }
static void phy_pm_runtime_put_sync(void *p) { (void)p;phy_puts++;event('P'); }
static void usleep_range(unsigned a,unsigned b) { assert(a==5000&&b==6000); }
static void pinctrl_pm_select_sleep_state(struct device *d) { assert(d==&dev);pinctrls++;event('S'); }
static int dwc3_gadget_soft_disconnect(struct dwc3 *d) { assert(d==&dwc);discalls++;event('D');return disconnect_error; }
static int dwc3_gadget_soft_connect(struct dwc3 *d)
{
 assert(d==&dwc);concalls++;writes_at_connect=nwrites;event('C');
 if(mutate_other){for(int i=0;i<d->num_usb2_ports;i++)u2[i]^=BIT(27);for(int i=0;i<d->num_usb3_ports;i++)u3[i]^=BIT(27);}
 return connect_error;
}
static void dwc3_disconnect_gadget_sleepable(struct dwc3 *d) { assert(d==&dwc);callbacks++;event('G'); }
static int dwc3_gadget_suspend(struct dwc3 *dwc);
#include "tested-functions.inc"
#include "original-suspend.inc"

static void reset(int n2,int n3,unsigned quirks,bool mixed)
{
 memset(&dev,0,sizeof(dev));memset(&dwc,0,sizeof(dwc));dwc.dev=&dev;
 dwc.current_dr_role=DWC3_GCTL_PRTCAP_DEVICE;dwc.current_otg_role=DWC3_OTG_ROLE_DEVICE;
 dwc.num_usb2_ports=n2;dwc.num_usb3_ports=n3;dwc.irq_gadget=9;dwc.softconnect=true;
 dwc.dis_u2_susphy_quirk=quirks&1;dwc.dis_u3_susphy_quirk=quirks&2;
 for(int i=0;i<n2;i++)u2[i]=BIT(24)|(u32)i<<10|((mixed&&i%2)?DWC3_GUSB2PHYCFG_SUSPHY:0);
 for(int i=0;i<n3;i++)u3[i]=BIT(25)|(u32)i<<10|((mixed&&i%2)?DWC3_GUSB3PIPECTL_SUSPHY:0);
 memcpy(original2,u2,sizeof(u2));memcpy(original3,u3,sizeof(u3));
 nwrites=reads2=reads3=discalls=concalls=callbacks=exits=irqjoins=pinctrls=phy_puts=writes_at_connect=nevents=0;events[0]=0;
 disconnect_error=connect_error=0;mutate_other=false;
}
static void same_bits(bool other_changed)
{
 u32 other=other_changed?BIT(27):0;
 for(int i=0;i<dwc.num_usb2_ports;i++)assert(u2[i]==(original2[i]^other));
 for(int i=0;i<dwc.num_usb3_ports;i++)assert(u3[i]==(original3[i]^other));
}
static unsigned changed_ports(void)
{
 unsigned changed=0;
 for(int i=0;i<dwc.num_usb2_ports;i++)changed+=(!!(original2[i]&DWC3_GUSB2PHYCFG_SUSPHY)!=!dwc.dis_u2_susphy_quirk);
 for(int i=0;i<dwc.num_usb3_ports;i++)changed+=(!!(original3[i]&DWC3_GUSB3PIPECTL_SUSPHY)!=!dwc.dis_u3_susphy_quirk);
 return changed;
}
static void error_proof(void)
{
 assert(discalls==1&&concalls==1&&callbacks==0&&exits==0&&irqjoins==0&&phy_puts==0&&pinctrls==0);
 assert(strchr(events,'D')<strchr(events,'C'));
 same_bits(mutate_other);
}
int main(void)
{
 /* Exact old code reproduces retained SUSPHY after failed active suspend. */
 reset(1,1,0,false);disconnect_error=-ETIMEDOUT;
 assert(original_suspend_common(&dwc,PMSG_SUSPEND)==-EAGAIN);
 assert(u2[0]&DWC3_GUSB2PHYCFG_SUSPHY);assert(u3[0]&DWC3_GUSB3PIPECTL_SUSPHY);assert(exits==0);cases++;
 reset(1,1,0,false);disconnect_error=-ETIMEDOUT;connect_error=-EIO;
 assert(dwc3_pm_suspend(&dwc)==-EAGAIN);error_proof();assert(nwrites-writes_at_connect==2);cases++;
 for(unsigned quirks=0;quirks<4;quirks++){
  reset(3,3,quirks,true);disconnect_error=-ETIMEDOUT;mutate_other=true;
  unsigned changed=changed_ports();assert(dwc3_suspend_common(&dwc,PMSG_SUSPEND)==-EAGAIN);
  error_proof();assert(nwrites-writes_at_connect==changed);cases++;
 }
 reset(DWC3_USB2_MAX_PORTS,DWC3_USB3_MAX_PORTS,3,true);disconnect_error=-EIO;
 assert(dwc3_suspend_common(&dwc,PMSG_SUSPEND)==-EAGAIN);error_proof();cases++;
 reset(0,2,0,true);disconnect_error=-EIO;assert(dwc3_suspend_common(&dwc,PMSG_SUSPEND)==-EAGAIN);
 error_proof();assert(reads2==0);cases++;
 reset(2,0,1,true);disconnect_error=-EIO;assert(dwc3_suspend_common(&dwc,PMSG_SUSPEND)==-EAGAIN);
 error_proof();assert(reads3==0);cases++;
 reset(0,0,0,false);disconnect_error=-EIO;assert(dwc3_suspend_common(&dwc,PMSG_SUSPEND)==-EAGAIN);
 error_proof();assert(reads2==reads3&&reads2==nwrites&&nwrites==0);cases++;
 reset(1,1,0,false);u2[0]|=DWC3_GUSB2PHYCFG_SUSPHY;memcpy(original2,u2,sizeof(u2));disconnect_error=-EIO;
 assert(dwc3_suspend_common(&dwc,PMSG_SUSPEND)==-EAGAIN);error_proof();assert(nwrites==0&&dwc.susphy_state);cases++;
 reset(1,1,0,false);disconnect_error=-EIO;dwc.current_dr_role=DWC3_GCTL_PRTCAP_OTG;
 assert(dwc3_suspend_common(&dwc,PMSG_SUSPEND)==-EAGAIN);error_proof();cases++;
 reset(1,1,0,false);disconnect_error=-EIO;
 assert(dwc3_runtime_suspend(&dwc)==-EAGAIN);error_proof();assert(nwrites==0);cases++;
 reset(1,1,0,false);dev.runtime_suspended=true;disconnect_error=-EIO;
 assert(dwc3_suspend_common(&dwc,PMSG_SUSPEND)==0&&nwrites==0&&discalls==0&&exits==0);cases++;
 reset(1,1,0,false);dwc.current_dr_role=DWC3_GCTL_PRTCAP_OTG;
 assert(dwc3_suspend_common(&dwc,PMSG_AUTO_SUSPEND)==0&&nwrites==0&&discalls==0&&exits==0);cases++;
 /* Successful DEVICE and HOST write sequences must remain the old sequence. */
 for(unsigned mode=0;mode<2;mode++)for(unsigned quirks=0;quirks<4;quirks++){
  struct write expected[128];unsigned count,old_exits,old_joins,old_puts;
  reset(3,2,quirks,true);if(mode)dwc.current_dr_role=DWC3_GCTL_PRTCAP_HOST;
  assert(original_suspend_common(&dwc,PMSG_SUSPEND)==0);count=nwrites;memcpy(expected,writes,count*sizeof(*writes));
  old_exits=exits;old_joins=irqjoins;old_puts=phy_puts;
  reset(3,2,quirks,true);if(mode)dwc.current_dr_role=DWC3_GCTL_PRTCAP_HOST;
  assert(dwc3_suspend_common(&dwc,PMSG_SUSPEND)==0&&count==nwrites&&!memcmp(expected,writes,count*sizeof(*writes)));
  assert(exits==old_exits&&irqjoins==old_joins&&phy_puts==old_puts);cases++;
 }
 /* Preserved unresolved old path: !softconnect can still swallow HALT error.
  * This control is explicitly not evidence of a full suspend/resume unwind.
  */
 reset(1,1,0,false);disconnect_error=-ETIMEDOUT;dwc.softconnect=false;
 assert(dwc3_suspend_common(&dwc,PMSG_SUSPEND)==0&&exits==1&&irqjoins==1);cases++;
 printf("{\"passed\":true,\"cases\":%u,\"actual_old_failure_reproduced\":true,\"success_write_sequences_unchanged\":true,\"full_resume_unwind_complete\":false,\"softconnect_false_old_gap_unchanged\":true}\n",cases);
 return 0;
}
