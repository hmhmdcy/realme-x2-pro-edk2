/* Actual extracted gadget/core functions; fake MMIO, request, IRQ/PM boundaries.
 * No DMA, Linux IRQ timing or physical HALT is emulated or certified.
 */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uint32_t u32;
typedef int pm_message_t;
#define BIT(n) (1U<<(n))
#define DWC3_GUSB2PHYCFG(n) (0x10U+(n))
#define DWC3_GUSB3PIPECTL(n) (0x20U+(n))
#define DWC3_DCTL 0x30U
#define DWC3_DSTS 0x31U
#define DWC3_DALEPENA 0x32U
#define DWC3_DEVTEN 0x33U
#define DWC3_GUSB2PHYCFG_SUSPHY BIT(6)
#define DWC3_GUSB2PHYCFG_ENBLSLPM BIT(8)
#define DWC3_GUSB3PIPECTL_SUSPHY BIT(17)
#define DWC3_DCTL_RUN_STOP BIT(0)
#define DWC3_DCTL_TRGTULST_MASK BIT(1)
#define DWC3_DCTL_TRGTULST_RX_DET BIT(2)
#define DWC3_DCTL_KEEP_CONNECT BIT(3)
#define DWC3_DSTS_DEVCTRLHLT BIT(0)
#define DWC3_DALEPENA_EP(n) BIT(n)
#define DWC3_EP_STALL BIT(0)
#define DWC3_EP_TXFIFO_RESIZED BIT(1)
#define DWC3_EP_RESOURCE_ALLOCATED BIT(2)
#define DWC3_EP_DELAY_STOP BIT(3)
#define DWC3_EP_TRANSFER_STARTED BIT(4)
#define DWC3_GCTL_PRTCAP_HOST 1
#define DWC3_GCTL_PRTCAP_DEVICE 2
#define DWC3_GCTL_PRTCAP_OTG 3
#define DWC3_OTG_ROLE_DEVICE 2
#define EP0_SETUP_PHASE 0
#define DWC3_PULL_UP_TIMEOUT 500
#define USB_STATE_NOTATTACHED 0
#define PMSG_SUSPEND 1
#define PMSG_AUTO_SUSPEND 2
#define PMSG_IS_AUTO(x) ((x)==PMSG_AUTO_SUSPEND)
#define DWC3_VER_IS_WITHIN(...) false
#define DWC3_VER_IS_PRIOR(...) false
#define msecs_to_jiffies(x) (x)
struct device { bool runtime_suspended,wakeup; };
struct usb_gadget { int state; };
struct dwc3;
struct dwc3_ep { struct dwc3 *dwc;u32 flags,number;bool stream_capable;int type;
 struct {void *desc,*comp_desc;} endpoint; };
struct dwc3 {
 struct device *dev;struct usb_gadget *gadget;struct dwc3_ep *eps[2];
 bool pullups_connected,connected,softconnect,delayed_status,susphy_state;
 bool dis_u2_susphy_quirk,dis_u3_susphy_quirk,dis_enblslpm_quirk,needs_full_reinit;
 int lock,ep0state,ep0_in_setup,current_dr_role,current_otg_role,num_usb2_ports,num_usb3_ports,irq_gadget;
 void *usb2_generic_phy[2],*usb3_generic_phy[2];
};
static struct device dev;
static struct usb_gadget gadget;
static struct dwc3 dwc;
static struct dwc3_ep eps[2];
static struct {
 u32 reg[0x40];bool halt_fault,halt_seen,core_active,phy_active,event_buffer_live,irq_registered;
 bool inject_run_after_halt_read,inject_run_in_callback;
 int locks,polls,run_off,remove[2],stop_all,masks,callbacks,reconnects,connect_errno;
 int exits,unsafe_exits,irq_joins,phy_puts,pinctrls,otg_exits,delayed_sends,resets;
 char events[256];unsigned events_len;
} f;
static unsigned cases;
static void event(char c){assert(f.events_len+1<sizeof(f.events));f.events[f.events_len++]=c;f.events[f.events_len]=0;}
#define spin_lock_irqsave(lock,flags) do {(void)(lock);(flags)=0;assert(f.locks==0);f.locks++;}while(0)
#define spin_unlock_irqrestore(lock,flags) do {(void)(lock);(void)(flags);assert(f.locks==1);f.locks--;}while(0)
static bool pm_runtime_suspended(struct device *d){assert(d==&dev);return d->runtime_suspended;}
static bool device_may_wakeup(struct device *d){assert(d==&dev);return d->wakeup;}
static u32 dwc3_readl(struct dwc3 *d,u32 reg){
 assert(d==&dwc&&f.core_active&&f.phy_active&&f.event_buffer_live);
 if(reg==DWC3_DSTS){f.polls++;if(f.halt_fault)return 0;f.halt_seen=true;if(f.inject_run_after_halt_read){f.reg[DWC3_DCTL]|=DWC3_DCTL_RUN_STOP;f.halt_seen=false;f.inject_run_after_halt_read=false;}return DWC3_DSTS_DEVCTRLHLT;}
 assert(reg<0x40);return f.reg[reg];
}
static void dwc3_writel(struct dwc3 *d,u32 reg,u32 value){
 assert(d==&dwc&&f.core_active&&reg<0x40);f.reg[reg]=value;
 if(reg==DWC3_DEVTEN&&value==0){assert(f.locks==1);f.masks++;event('M');}
}
static void dwc3_gadget_dctl_write_safe(struct dwc3 *d,u32 value){
 assert(d==&dwc&&f.core_active&&f.locks==0);f.reg[DWC3_DCTL]=value;
 if(!(value&DWC3_DCTL_RUN_STOP)){f.run_off++;event('R');}
}
static void usleep_range(unsigned a,unsigned b){(void)a;(void)b;}
static void __dwc3_gadget_set_speed(struct dwc3 *d){assert(d==&dwc);}
static void dwc3_pre_run_stop(struct dwc3 *d,int on){assert(d==&dwc&&!on);}
static void trace_dwc3_gadget_ep_disable(struct dwc3_ep *p){assert(f.locks==1);event('E');(void)p;}
static void __dwc3_gadget_ep_set_halt(struct dwc3_ep *p,int value,bool protocol){(void)p;(void)value;(void)protocol;assert(f.locks==1);}
/* Request removal/DMA ownership is an unchanged opaque boundary here. */
static void dwc3_remove_requests(struct dwc3 *d,struct dwc3_ep *p,int status){assert(d==&dwc&&f.locks==1&&status==-ESHUTDOWN);f.remove[p->number]++;}
static void dwc3_stop_active_transfers(struct dwc3 *d){assert(d==&dwc&&f.locks==1);f.stop_all++;event('T');}
static void dwc3_ep0_send_delayed_status(struct dwc3 *d){assert(d==&dwc&&f.locks==1);f.delayed_sends++;event('D');}
static void reinit_completion(int *p){assert(p==&dwc.ep0_in_setup);}
static int wait_for_completion_timeout(int *p,unsigned timeout){assert(p==&dwc.ep0_in_setup&&timeout==DWC3_PULL_UP_TIMEOUT);return 0;}
static void dev_warn(struct device *d,const char *text){assert(d==&dev);(void)text;}
static void dwc3_ep0_reset_state(struct dwc3 *d){assert(d==&dwc&&f.locks==1);d->ep0state=EP0_SETUP_PHASE;f.resets++;}
static void usb_gadget_set_state(struct usb_gadget *g,int state){assert(g==&gadget&&f.locks==0);g->state=state;event('N');}
static int dwc3_gadget_soft_connect(struct dwc3 *d){assert(d==&dwc&&f.core_active&&f.locks==0);f.reconnects++;event('K');return f.connect_errno;}
static void dwc3_disconnect_gadget_sleepable(struct dwc3 *d){assert(d==&dwc&&f.locks==0);f.callbacks++;event('C');if(f.inject_run_in_callback){f.reg[DWC3_DCTL]|=DWC3_DCTL_RUN_STOP;d->pullups_connected=true;f.halt_seen=false;}}
static void synchronize_irq(int irq){assert(irq==7&&f.irq_registered);f.irq_joins++;event('I');}
static void dwc3_core_exit(struct dwc3 *d){assert(d==&dwc&&f.core_active);f.exits++;if(!f.halt_seen)f.unsafe_exits++;f.core_active=f.phy_active=false;event('X');}
static void dwc3_otg_exit(struct dwc3 *d){assert(d==&dwc);f.otg_exits++;event('O');}
static void phy_pm_runtime_put_sync(void *p){(void)p;f.phy_puts++;}
static void pinctrl_pm_select_sleep_state(struct device *d){assert(d==&dev);f.pinctrls++;event('P');}
#include "tested-functions.inc"
#include "previous-functions.inc"

static void reset(bool softconnect,bool fail,int role){
 memset(&f,0,sizeof(f));memset(&dev,0,sizeof(dev));memset(&dwc,0,sizeof(dwc));memset(eps,0,sizeof(eps));
 f.core_active=f.phy_active=f.event_buffer_live=f.irq_registered=true;f.halt_fault=fail;
 dwc.dev=&dev;dwc.gadget=&gadget;dwc.softconnect=softconnect;dwc.pullups_connected=true;dwc.connected=true;
 dwc.current_dr_role=role;dwc.current_otg_role=DWC3_OTG_ROLE_DEVICE;dwc.num_usb2_ports=dwc.num_usb3_ports=1;dwc.irq_gadget=7;
 for(int i=0;i<2;i++){eps[i].dwc=&dwc;eps[i].number=i;eps[i].flags=DWC3_EP_RESOURCE_ALLOCATED;dwc.eps[i]=&eps[i];}
 f.reg[DWC3_GUSB2PHYCFG(0)]=BIT(24)|DWC3_GUSB2PHYCFG_ENBLSLPM;
 f.reg[DWC3_GUSB3PIPECTL(0)]=BIT(25);f.reg[DWC3_DCTL]=DWC3_DCTL_RUN_STOP;f.reg[DWC3_DALEPENA]=3;f.reg[DWC3_DEVTEN]=~0U;
 gadget.state=9;
}
static void retained_failure(bool expected_soft){
 assert(f.locks==0&&f.core_active&&f.phy_active&&f.event_buffer_live&&f.irq_registered);
 assert(f.exits==0&&f.unsafe_exits==0&&f.irq_joins==0&&f.phy_puts==0&&f.pinctrls==0&&f.otg_exits==0);
 assert(!dwc.pullups_connected&&!dwc.connected&&gadget.state==USB_STATE_NOTATTACHED);
 assert(f.polls==2000&&f.run_off==1&&!f.halt_seen&&f.masks==1&&f.remove[0]==1&&f.remove[1]==1);
 assert(f.reg[DWC3_DEVTEN]==0&&(f.reg[DWC3_DALEPENA]&3)==0&&!(f.reg[DWC3_DCTL]&DWC3_DCTL_RUN_STOP));
 assert(f.callbacks==0&&f.reconnects==(expected_soft?1:0));
 assert(f.reg[DWC3_GUSB2PHYCFG(0)]==(BIT(24)|DWC3_GUSB2PHYCFG_ENBLSLPM));
 assert(f.reg[DWC3_GUSB3PIPECTL(0)]==BIT(25));
 assert(strchr(f.events,'T')<strchr(f.events,'R')&&strchr(f.events,'R')<strchr(f.events,'M'));
}
static void no_repeat(void){
 assert(f.core_active&&f.phy_active&&f.event_buffer_live&&f.irq_registered&&f.locks==0);
 assert(f.exits==0&&f.irq_joins==0&&f.phy_puts==0&&f.pinctrls==0&&f.callbacks==0);
 assert(f.stop_all==1&&f.run_off==1&&f.masks==1&&f.remove[0]==1&&f.remove[1]==1);
 assert(f.reg[DWC3_GUSB2PHYCFG(0)]==(BIT(24)|DWC3_GUSB2PHYCFG_ENBLSLPM));
 assert(f.reg[DWC3_GUSB3PIPECTL(0)]==BIT(25));
}
static void never_connected(bool halt){
 reset(false,!halt,DWC3_GCTL_PRTCAP_DEVICE);dwc.pullups_connected=dwc.connected=false;f.reg[DWC3_DCTL]=0;
}
int main(void){
 /* Old errno fix prevents the first exit, but old flag-only retry still exits. */
 reset(false,true,DWC3_GCTL_PRTCAP_DEVICE);
 assert(previous_suspend_common(&dwc,PMSG_SUSPEND)==-ETIMEDOUT);
 assert(f.core_active&&!dwc.pullups_connected&&f.run_off==1);
 assert(previous_suspend_common(&dwc,PMSG_SUSPEND)==0&&f.exits==1&&f.unsafe_exits==1);cases++;
 for(int role=DWC3_GCTL_PRTCAP_DEVICE;role<=DWC3_GCTL_PRTCAP_OTG;role++){
  reset(false,true,role);assert(dwc3_pm_suspend(&dwc)==-ETIMEDOUT);retained_failure(false);
  assert(dwc3_pm_suspend(&dwc)==-EAGAIN);no_repeat();assert(f.reconnects==0&&f.polls==2001);
  assert(dwc3_pm_suspend(&dwc)==-EAGAIN);no_repeat();assert(f.reconnects==0&&f.polls==2002);cases++;
  reset(false,true,role);assert(dwc3_pm_suspend(&dwc)==-ETIMEDOUT);f.halt_fault=false;
  assert(dwc3_pm_suspend(&dwc)==0&&f.exits==1&&f.unsafe_exits==0&&f.irq_joins==1&&f.callbacks==1);
  assert(f.run_off==1&&f.stop_all==1&&f.masks==1&&f.polls==2001);cases++;
  /* First real stop keeps its original true-intent reconnect policy. A later
   * no-pullup miss must not blindly reset/reconnect or repeat DMA teardown.
   */
  reset(true,true,role);f.connect_errno=-EIO;
  assert(dwc3_pm_suspend(&dwc)==-EAGAIN&&f.reconnects==1);
  assert(dwc3_pm_suspend(&dwc)==-EAGAIN);no_repeat();assert(f.reconnects==1);
  f.halt_fault=false;assert(dwc3_pm_suspend(&dwc)==0&&f.reconnects==1&&f.run_off==1&&f.unsafe_exits==0);cases++;
 }
 never_connected(true);assert(dwc3_pm_suspend(&dwc)==0&&f.run_off==0&&f.stop_all==0&&f.masks==0&&f.exits==1&&f.unsafe_exits==0);cases++;
 never_connected(false);assert(dwc3_pm_suspend(&dwc)==-EAGAIN&&f.polls==1&&f.stop_all==0&&f.run_off==0&&f.reconnects==0&&f.exits==0);cases++;
 never_connected(true);f.reg[DWC3_DCTL]=DWC3_DCTL_RUN_STOP;
 assert(dwc3_pm_suspend(&dwc)==-EAGAIN&&f.stop_all==0&&f.run_off==0&&f.exits==0);cases++;
 never_connected(false);dev.runtime_suspended=true;f.core_active=f.phy_active=false;
 assert(dwc3_gadget_suspend(&dwc)==0&&f.polls==0&&f.stop_all==0&&f.callbacks==1);cases++;
 never_connected(false);dev.runtime_suspended=true;f.core_active=f.phy_active=false;
 assert(dwc3_pm_suspend(&dwc)==0&&f.polls==0&&f.callbacks==0&&f.exits==0);cases++;
 /* Model the real fact that run/stop writers are not all under dwc.lock:
  * a request arriving between the two status reads is caught by DCTL.
  */
 never_connected(true);f.inject_run_after_halt_read=true;
 assert(dwc3_pm_suspend(&dwc)==-EAGAIN&&f.exits==0&&f.stop_all==0&&f.run_off==0);cases++;
 /* Explicit limitation control: this snapshot is not a later lifetime lock.
  * A separate producer injected AFTER the gate can still invalidate HALT.
  * This is not counted as a concurrency/PM safety success.
  */
 never_connected(true);f.inject_run_in_callback=true;
 assert(dwc3_pm_suspend(&dwc)==0&&f.unsafe_exits==1);cases++;
 reset(false,false,DWC3_GCTL_PRTCAP_DEVICE);
 assert(dwc3_pm_suspend(&dwc)==0&&f.run_off==1&&f.stop_all==1&&f.polls==1&&f.unsafe_exits==0);cases++;
 printf("{\"passed\":true,\"cases\":%u,\"old_two_attempt_failure_reproduced\":true,\"new_retry_miss_no_repeated_DMA_or_reset\":true,\"late_halt_allows_existing_path\":true,\"post_snapshot_producer_lifetime_not_serialized\":true,\"full_resume_unwind_complete\":false}\n",cases);
 return 0;
}
