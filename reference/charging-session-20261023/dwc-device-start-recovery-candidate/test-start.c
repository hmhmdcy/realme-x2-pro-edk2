/* Actual production start/stop/reset/recovery/PM functions are extracted.
 * Fake endpoint-command, MMIO, callback and PM boundaries are explicit here;
 * no DMA, Linux IRQ timing, host enumeration or physical recovery is emulated.
 */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
typedef uint32_t u32;
typedef uint64_t u64;
typedef int pm_message_t;
#define PMSG_RESUME 1
#define PMSG_AUTO_RESUME 2
#define PMSG_IS_AUTO(x) ((x) == PMSG_AUTO_RESUME)
#define DWC3_GCTL_PRTCAP_DEVICE 1
#define DWC3_GCTL_PRTCAP_HOST 2
#define DWC3_GCTL_PRTCAP_OTG 3
#define DWC3_OTG_ROLE_DEVICE 1
#define DWC3_OTG_ROLE_HOST 2
#define DWC3_ERR_NONE 0
#define DWC3_ERR_RECOVERY 1
#define DWC3_ERR_UNRECOVERABLE 2
#define DWC3_ERR_RECOVERY_MAX 3
#define DWC3_GUSB2PHYCFG(x) (0 + (x))
#define DWC3_DCTL 2
#define DWC3_DSTS 3
#define DWC3_DCFG 4
#define DWC3_DCFG1 5
#define DWC3_GRXTHRCFG 6
#define DWC3_DEV_IMOD(x) 7
#define DWC3_GEVNTCOUNT(x) 8
#define DWC3_DALEPENA 9
#define DWC3_DEVTEN 10
#define DWC3_DALEPENA_EP(x) (1u << (x))
#define DWC3_GEVNTCOUNT_EHB 1
#define DWC3_DCTL_RUN_STOP 1u
#define DWC3_DCTL_CSFTRST 2u
#define DWC3_DSTS_DEVCTRLHLT 1u
#define DWC3_DCTL_TRGTULST_MASK 4u
#define DWC3_DCTL_TRGTULST_RX_DET 8u
#define DWC3_DCTL_KEEP_CONNECT 16u
#define DWC3_GUSB2PHYCFG_SUSPHY 64u
#define DWC3_GUSB2PHYCFG_ENBLSLPM 128u
#define DWC3_GRXTHRCFG_PKTCNTSEL 1u
#define DWC31_GRXTHRCFG_PKTCNTSEL 2u
#define DWC3_DCFG_IGNSTRMPP 4u
#define DWC3_DCFG1_DIS_MST_ENH 8u
#define DWC3_DEPCFG_ACTION_INIT 0
#define DWC3_LINK_STATE_SS_DIS 0
#define DWC3_VER_IS_WITHIN(...) false
#define DWC3_VER_IS_PRIOR(...) false
#define DWC3_IP_IS(...) false
#define DWC3_MST_CAPABLE(...) false
#define DWC3_EP_STALL 1u
#define DWC3_EP_ENABLED 2u
#define DWC3_EP_TXFIFO_RESIZED 4u
#define DWC3_EP_RESOURCE_ALLOCATED 8u
#define DWC3_EP_DELAY_STOP 16u
#define DWC3_EP_TRANSFER_STARTED 32u
#define EP0_SETUP_PHASE 0
#define DWC3_PULL_UP_TIMEOUT 500
#define USB_STATE_NOTATTACHED 0
#define msecs_to_jiffies(x) (x)
#define cpu_to_le16(x) (x)
struct device { int rpm, refs, puts, enabled, marked, disabled, pm_enabled; };
struct usb_gadget { int state; };
struct dwc3;
struct dwc3_ep {
 struct dwc3 *dwc;
 unsigned flags, number;
 const char *name;
 bool stream_capable;
 int type;
 struct { void *desc, *comp_desc; } endpoint;
};
struct dwc3 {
 struct device *dev;
 struct usb_gadget *gadget;
 void *gadget_driver, *reset;
 int current_dr_role, current_otg_role, num_usb2_ports, num_usb3_ports;
 void *usb2_generic_phy[2], *usb3_generic_phy[2];
 bool needs_full_reinit, dis_u2_susphy_quirk, dis_enblslpm_quirk, susphy_state;
 bool pullups_connected, connected, softconnect, delayed_status, ep0_bounced, pending_events;
 int lock, connect_mutex, ep0state, ep0_in_setup, link_state, imod_interval, hwparams, irq_gadget;
 int err_state, err_recovery_work;
 u32 err_recovery_count;
 u64 err_event_seq;
 struct dwc3_ep *eps[2];
};
static struct { unsigned wMaxPacketSize; } dwc3_gadget_ep0_desc;
static struct dwc3 d;
static struct device dev;
static struct usb_gadget gadget;
static struct dwc3_ep eps[2];
static struct {
 u32 regs[16];
 int attempt, fail_stage[4], fail_errno[4], start_configs, enable_calls[2];
 int run_on, run_off, reset_count, stop_ep[2], irq_masks, irq_enable, irq_joins, callbacks;
 int event_setups, susphy, locks, mutex, logs, queues;
 int deassert_ret, clock_ret, init_ret, deasserts, clocks_on, clocks_off, asserts, inits;
 bool reset_timeout, run_on_timeout, run_off_timeout, running, powered, irq_disabled;
 char log[4096];
} f;
static void spin_take(void) { assert(!f.locks); f.locks++; }
static void spin_drop(void) { assert(f.locks == 1); f.locks--; }
#define spin_lock_irqsave(lock, flags) do { (void)(lock); (flags)=0; spin_take(); } while (0)
#define spin_unlock_irqrestore(lock, flags) do { (void)(lock); (void)(flags); spin_drop(); } while (0)
static void mutex_lock(int *p) { (void)p; assert(!f.mutex && !f.locks); f.mutex++; }
static void mutex_unlock(int *p) { (void)p; assert(f.mutex == 1 && !f.locks); f.mutex--; }
static void lockdep_assert_held(int *p) { (void)p; assert(f.mutex); }
static void dev_err(struct device *p, const char *fmt, ...)
{ (void)p; va_list a; va_start(a,fmt); size_t n=strlen(f.log); vsnprintf(f.log+n,sizeof(f.log)-n,fmt,a); va_end(a); f.logs++; }
#define dev_warn dev_err
static bool pm_runtime_suspended(struct device *p) { return p->rpm == 0; }
static bool device_may_wakeup(struct device *p) { (void)p; return false; }
static u32 dwc3_readl(struct dwc3 *p, unsigned reg)
{
 (void)p; assert(f.powered);
 if(reg == DWC3_DCTL && (f.regs[reg] & DWC3_DCTL_CSFTRST) && !f.reset_timeout)
  f.regs[reg] &= ~DWC3_DCTL_CSFTRST;
 if(reg == DWC3_DSTS) {
  if(f.running && f.run_on_timeout) return DWC3_DSTS_DEVCTRLHLT;
  if(!f.running && f.run_off_timeout) return 0;
  return f.running ? 0 : DWC3_DSTS_DEVCTRLHLT;
 }
 return f.regs[reg];
}
static void dwc3_writel(struct dwc3 *p, unsigned reg, u32 val)
{
 (void)p; assert(f.powered);
 if(reg == DWC3_DEVTEN && !val) { assert(f.locks); f.irq_masks++; }
 f.regs[reg]=val;
}
static void dwc3_gadget_dctl_write_safe(struct dwc3 *p, u32 val)
{
 (void)p; assert(f.powered); f.regs[DWC3_DCTL]=val;
 if(val & DWC3_DCTL_CSFTRST) { f.reset_count++; f.attempt++; }
 else if(val & DWC3_DCTL_RUN_STOP) f.run_on++; else f.run_off++;
 f.running=!!(val & DWC3_DCTL_RUN_STOP);
}
static void msleep(unsigned n) { (void)n; }
static void udelay(unsigned n) { (void)n; }
static void usleep_range(unsigned a, unsigned b) { (void)a; (void)b; }
static void __dwc3_gadget_set_speed(struct dwc3 *p) { (void)p; }
static void dwc3_pre_run_stop(struct dwc3 *p, int on) { (void)p; (void)on; }
static bool dwc3_has_imod(struct dwc3 *p) { (void)p; return false; }
static void dwc3_gadget_setup_nump(struct dwc3 *p) { (void)p; }
static int dwc3_gadget_start_config(struct dwc3 *p, int ep)
{ (void)p; (void)ep; f.start_configs++; return f.fail_stage[f.attempt] == 1 ? f.fail_errno[f.attempt] : 0; }
/* Real control __ep_enable returns before DALEPENA on set_config/resource
 * errno (actual source 932..953). Only a successful control enable sets it.
 */
static int __dwc3_gadget_ep_enable(struct dwc3_ep *ep, int action)
{
 (void)action; f.enable_calls[ep->number]++;
 if(f.fail_stage[f.attempt] == (int)ep->number + 2) return f.fail_errno[f.attempt];
 ep->flags |= DWC3_EP_ENABLED | DWC3_EP_RESOURCE_ALLOCATED;
 f.regs[DWC3_DALEPENA] |= DWC3_DALEPENA_EP(ep->number); return 0;
}
static void trace_dwc3_gadget_ep_disable(struct dwc3_ep *ep) { f.stop_ep[ep->number]++; }
static int __dwc3_gadget_ep_set_halt(struct dwc3_ep *ep,int on,bool protocol)
{ (void)on; (void)protocol; ep->flags &= ~DWC3_EP_STALL; return 0; }
static void dwc3_remove_requests(struct dwc3 *p, struct dwc3_ep *ep, int error)
{ (void)p; (void)ep; assert(error == -ESHUTDOWN); }
static void dwc3_ep0_out_start(struct dwc3 *p) { (void)p; }
static void dwc3_gadget_enable_irq(struct dwc3 *p)
{ f.irq_enable++; dwc3_writel(p,DWC3_DEVTEN,0xff); }
static void dwc3_enable_susphy(struct dwc3 *p, bool state) { (void)p; (void)state; f.susphy++; }
static void dwc3_ep0_send_delayed_status(struct dwc3 *p) { (void)p; }
static void dwc3_stop_active_transfers(struct dwc3 *p) { (void)p; assert(f.locks); }
static void reinit_completion(int *p) { *p=0; }
static int wait_for_completion_timeout(int *p, int t) { (void)p; (void)t; return 1; }
static void dwc3_ep0_reset_state(struct dwc3 *p) { p->ep0state=EP0_SETUP_PHASE; }
static void usb_gadget_set_state(struct usb_gadget *p,int state) { p->state=state; }
static int dwc3_event_buffers_setup(struct dwc3 *p) { (void)p; f.event_setups++; return 0; }
static void dwc3_disconnect_gadget_sleepable(struct dwc3 *p)
{ (void)p; assert(f.mutex && !f.locks); f.callbacks++; }
static void synchronize_irq(int irq) { (void)irq; assert(f.mutex && !f.locks); f.irq_joins++; }
static bool schedule_work(int *work) { (*work)++; f.queues++; return true; }
static int reset_control_deassert(void *p) { (void)p; f.deasserts++; return f.deassert_ret; }
static int reset_control_assert(void *p) { (void)p; f.asserts++; return 0; }
static int dwc3_clk_enable(struct dwc3 *p) { (void)p; f.clocks_on++; return f.clock_ret; }
static void dwc3_clk_disable(struct dwc3 *p) { (void)p; f.clocks_off++; f.powered=false; }
static int dwc3_core_init(struct dwc3 *p)
{ (void)p; f.inits++; if(!f.init_ret) f.powered=true; return f.init_ret; }
static void dwc3_set_prtcap(struct dwc3 *p,int role,bool keep) { (void)p; (void)role; (void)keep; }
static int phy_pm_runtime_get_sync(void *p) { (void)p; return 0; }
static void dwc3_otg_init(struct dwc3 *p) { (void)p; }
static void dwc3_otg_host_init(struct dwc3 *p) { (void)p; }
static void pm_runtime_put(struct device *p) { assert(p->refs==1); p->refs--; p->puts++; }
static void enable_irq(int irq) { (void)irq; assert(f.irq_disabled && f.powered); f.irq_disabled=false; dev.enabled++; }
static void pm_runtime_mark_last_busy(struct device *p) { p->marked++; }
static void pinctrl_pm_select_default_state(struct device *p) { (void)p; }
static void pm_runtime_disable(struct device *p) { p->disabled++; }
static int pm_runtime_set_active(struct device *p) { p->rpm=1; return 0; }
static void pm_runtime_set_suspended(struct device *p) { p->rpm=0; }
static void pm_runtime_enable(struct device *p) { p->pm_enabled++; }
#include "tested-functions.inc"
#include "previous-soft-connect.inc"
static void setup(void)
{
 memset(&d,0,sizeof(d)); memset(&dev,0,sizeof(dev)); memset(&gadget,0,sizeof(gadget));
 memset(eps,0,sizeof(eps)); memset(&f,0,sizeof(f));
 d.dev=&dev; d.gadget=&gadget; d.gadget_driver=&d; d.softconnect=true;
 d.current_dr_role=DWC3_GCTL_PRTCAP_DEVICE; d.current_otg_role=DWC3_OTG_ROLE_DEVICE;
 d.irq_gadget=7; d.susphy_state=true; dev.rpm=1; f.powered=true;
 for(unsigned i=0;i<2;i++) { eps[i].dwc=&d; eps[i].number=i; eps[i].name=i?"ep0in":"ep0out"; d.eps[i]=&eps[i]; }
}
static void fail(int attempt,int stage,int error) { f.fail_stage[attempt]=stage; f.fail_errno[attempt]=error; }
static void clean(void)
{
 assert(!(f.regs[DWC3_DALEPENA] & 3)); assert(!f.regs[DWC3_DEVTEN]);
 assert(!f.running && !d.pullups_connected); assert(!f.locks && !f.mutex);
 assert(!(eps[0].flags & DWC3_EP_ENABLED) && !(eps[1].flags & DWC3_EP_ENABLED));
}
static int groups, cases;
static void done(const char *message) { groups++; puts(message); }
static void previous_counterexample(void)
{
 for(int stage=1;stage<=3;stage++) {
  setup(); fail(1,stage,-EIO); assert(previous_soft_connect(&d)==0);
  assert(f.run_on==1 && d.pullups_connected); cases++;
 }
 done("previous actual soft_connect hides each of three start-stage errors and writes RUN_STOP");
}
static void cleanup_and_normal(void)
{
 const int errors[]={0,-EIO,-EINVAL,-ENOMEM};
 for(int stage=1;stage<=3;stage++) {
  setup(); fail(1,stage,errors[stage]); f.regs[DWC3_DALEPENA]=1u<<5;
  assert(dwc3_gadget_soft_connect(&d)==errors[stage]); clean();
  assert(!f.run_on && !f.run_off && f.irq_masks==1 && !f.irq_enable);
  assert(f.stop_ep[0]==(stage==3?2:1) && f.stop_ep[1]==1);
  assert(f.regs[DWC3_DALEPENA]==(1u<<5));
  assert(strstr(f.log,"RUN_STOP skipped")); cases++;
 }
 setup(); assert(!dwc3_gadget_soft_connect(&d));
 assert(f.run_on==1 && f.irq_enable==1 && !f.irq_masks && !f.stop_ep[0] && !f.stop_ep[1]);
 assert((f.regs[DWC3_DALEPENA]&3)==3 && d.pullups_connected); cases++;
 done("actual endpoint stop masks IRQ and clears only EP0 bits; normal start has no cleanup");
}
static void recovery(void)
{
 for(int stage=1;stage<=3;stage++) {
  setup(); fail(1,stage,-EIO); assert(dwc3_gadget_resume(&d)==-EIO);
  assert(f.attempt==2 && f.run_on==1 && f.callbacks==1 && f.irq_joins==1);
  assert(d.err_state==DWC3_ERR_NONE && d.err_recovery_count==1);
  assert(strstr(f.log,"primary=-5 recovery=0") && strstr(f.log,"stage=connect-complete")); cases++;
 }
 setup(); fail(1,3,-EIO); fail(2,2,-ENOMEM);
 assert(dwc3_gadget_resume(&d)==-EIO); clean();
 assert(f.attempt==2 && !f.run_on && d.err_state==DWC3_ERR_UNRECOVERABLE && d.err_recovery_count==1);
 assert(strstr(f.log,"primary=-5 recovery=-12") && strstr(f.log,"stage=connect")); cases++;
 done("actual DEVICE resume now consumes start errors; one recovery, primary and recovery errno separate");
}
static void old_failure_and_reset(void)
{
 setup(); fail(1,1,-EINVAL); d.err_state=DWC3_ERR_UNRECOVERABLE; d.err_recovery_count=2;
 assert(dwc3_gadget_resume(&d)==-EINVAL); clean();
 assert(f.attempt==1 && !f.callbacks && d.err_recovery_count==2 && d.err_state==DWC3_ERR_UNRECOVERABLE); cases++;
 setup(); f.reset_timeout=true; assert(dwc3_gadget_soft_connect(&d)==-ETIMEDOUT);
 assert(!f.start_configs && !f.irq_masks && !f.run_on); cases++;
 setup(); d.current_dr_role=DWC3_GCTL_PRTCAP_OTG; fail(1,2,-EINVAL);
 assert(dwc3_gadget_resume(&d)==-EINVAL && f.attempt==1 && !f.callbacks); clean(); cases++;
 done("old unrecoverable cannot be revived, reset failure is not called cleaned, OTG has no new retry");
}
static void halt_failure(void)
{
 setup(); f.run_on_timeout=true; f.run_off_timeout=true;
 assert(dwc3_gadget_resume(&d)==-ETIMEDOUT);
 assert(f.run_on==1 && f.run_off==1 && f.attempt==1 && f.callbacks==1 && !d.err_recovery_count);
 assert(d.err_state==DWC3_ERR_UNRECOVERABLE && f.powered);
 assert(strstr(f.log,"primary=-110 recovery=-110 stage=disconnect")); cases++;
 setup(); fail(1,1,-EIO); f.run_on_timeout=true;
 assert(dwc3_gadget_resume(&d)==-EIO && f.attempt==2 && d.pullups_connected);
 assert(strstr(f.log,"primary=-5 recovery=-110 stage=connect")); cases++;
 done("HALT/RUN_STOP timeouts remain bounded errors; no claim of physical cleanup or core exit");
}
static void pm_policy(void)
{
 setup(); f.powered=false; dev.rpm=2; dev.refs=1; d.pending_events=true; f.irq_disabled=true;
 fail(1,3,-EIO); fail(2,1,-ENOSPC);
 assert(!dwc3_runtime_resume(&d));
 assert(f.powered && dev.puts==1 && !dev.refs && dev.enabled==1 && !d.pending_events && !f.irq_disabled);
 assert(d.err_state==DWC3_ERR_UNRECOVERABLE && strstr(f.log,"primary=-5 recovery=-28")); cases++;
 setup(); f.powered=false; fail(1,1,-EIO); fail(2,2,-EINVAL);
 assert(!dwc3_pm_resume(&d) && f.powered && dev.rpm==1 && dev.disabled==1 && dev.pm_enabled==1);
 assert(f.susphy==1 && d.err_state==DWC3_ERR_UNRECOVERABLE); cases++;
 setup(); f.powered=false; f.init_ret=-EIO;
 assert(dwc3_runtime_resume(&d)==-EIO && !f.powered && !f.attempt);
 assert(f.clocks_off==1 && f.asserts==1); cases++;
 setup(); f.powered=false; f.clock_ret=-EIO;
 assert(dwc3_pm_resume(&d)==-EIO && !f.powered && !f.attempt && dev.rpm==0);
 assert(!f.clocks_off && f.asserts==1 && dev.pm_enabled==1); cases++;
 done("actual PM callers retain powered-success and pending tail; original init failures still unwind");
}
int main(void)
{
 previous_counterexample(); cleanup_and_normal(); recovery(); old_failure_and_reset(); halt_failure(); pm_policy();
 printf("{\"passed\":true,\"groups\":%d,\"cases\":%d,\"actual_functions\":14,\"hardware_emulated\":false}\n",groups,cases);
 return 0;
}
