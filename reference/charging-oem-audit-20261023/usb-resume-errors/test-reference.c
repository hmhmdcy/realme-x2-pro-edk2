/* Fake MMIO/PM boundaries around verbatim cached production functions.
 * No timing, DMA, IRQ, PHY or enumeration is emulated. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <errno.h>
#include <string.h>
typedef uint32_t u32;
typedef int pm_message_t;
#define PMSG_IS_AUTO(x) ((x) == 1)
#define DWC3_GCTL_PRTCAP_DEVICE 1
#define DWC3_GCTL_PRTCAP_HOST 2
#define DWC3_GCTL_PRTCAP_OTG 3
#define DWC3_OTG_ROLE_DEVICE 1
#define DWC3_OTG_ROLE_HOST 2
#define DWC3_GUSB2PHYCFG(x) (0 + (x))
#define DWC3_GUSB3PIPECTL(x) (10 + (x))
#define DWC3_DCTL 2
#define DWC3_DSTS 3
#define DWC3_DCFG 4
#define DWC3_DCFG1 5
#define DWC3_GRXTHRCFG 6
#define DWC3_DEV_IMOD(x) 7
#define DWC3_GEVNTCOUNT(x) 8
#define DWC3_GEVNTCOUNT_EHB 1
#define DWC3_DCTL_RUN_STOP (1u << 0)
#define DWC3_DCTL_CSFTRST (1u << 1)
#define DWC3_DSTS_DEVCTRLHLT (1u << 0)
#define DWC3_DCTL_TRGTULST_MASK (1u << 2)
#define DWC3_DCTL_TRGTULST_RX_DET (1u << 3)
#define DWC3_DCTL_KEEP_CONNECT (1u << 4)
#define DWC3_GUSB2PHYCFG_SUSPHY (1u << 6)
#define DWC3_GUSB2PHYCFG_ENBLSLPM (1u << 8)
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
#define EP0_SETUP_PHASE 0
#define DWC3_PULL_UP_TIMEOUT 500
#define USB_STATE_NOTATTACHED 0
#define PWR_EVNT_LPM_IN_L2_MASK (1u << 4)
#define PWR_EVNT_LPM_OUT_L2_MASK (1u << 5)
#define spin_lock_irqsave(lock, flags) ((void)(lock), (flags) = 0)
#define spin_unlock_irqrestore(lock, flags) ((void)(lock), (void)(flags))
#define msecs_to_jiffies(x) (x)
#define cpu_to_le16(x) (x)
struct device { bool runtime_suspended, may_wakeup; };
struct usb_gadget { int state; };
struct dwc3_ep { unsigned flags; const char *name; };
struct dwc3 {
    struct device *dev;
    struct usb_gadget *gadget;
    void *gadget_driver;
    int current_dr_role, current_otg_role, num_usb2_ports, num_usb3_ports;
    void *usb2_generic_phy[2], *usb3_generic_phy[2];
    bool needs_full_reinit, dis_u2_susphy_quirk, dis_enblslpm_quirk, susphy_state;
    bool pullups_connected, connected, softconnect, delayed_status, ep0_bounced;
    int lock, ep0state, ep0_in_setup, link_state, imod_interval, hwparams;
    struct dwc3_ep *eps[2];
};
struct dwc3_qcom_port { int usb2_speed; };
struct dwc3_qcom {
    struct device *dev;
    unsigned char *qscratch_base;
    bool is_suspended;
    int num_ports, num_clocks;
    int *clks[2];
    struct dwc3_qcom_port ports[2];
};
static unsigned pwr_evnt_irq_stat_reg[2] = { 0, 4 };
static struct { unsigned wMaxPacketSize; } dwc3_gadget_ep0_desc;
static struct {
    u32 regs[16];
    bool reset_timeout, run_timeout, running;
    int init_ret, start_config_ret, enable0_ret, enable1_ret;
    int icc_disable_ret, icc_enable_ret, clk_fail_index;
    int setup_wait, log_error, log_warn, clocks_disabled, clocks_enabled;
    int icc_disabled, icc_enabled, run_calls, delay_calls, reset_calls;
    int start_calls, stop_calls, event_setup, disconnect_calls, ep0_resets;
    int irq_enable, ep_disable, otg_init, role_set, susphy_restore;
} fake;
#define dev_err(...) (++fake.log_error)
#define dev_warn(...) (++fake.log_warn)
static bool pm_runtime_suspended(struct device *d) { return d->runtime_suspended; }
static bool device_may_wakeup(struct device *d) { return d->may_wakeup; }
static u32 readl(void *address) { u32 v; memcpy(&v, address, sizeof(v)); return v; }
static bool dwc3_qcom_is_host(struct dwc3_qcom *q) { (void)q; return false; }
static void clk_disable_unprepare(int *c) { (void)c; fake.clocks_disabled++; }
static int clk_prepare_enable(int *c) { fake.clocks_enabled++; return *c == fake.clk_fail_index ? -EIO : 0; }
static int dwc3_qcom_interconnect_disable(struct dwc3_qcom *q) { (void)q; fake.icc_disabled++; return fake.icc_disable_ret; }
static int dwc3_qcom_interconnect_enable(struct dwc3_qcom *q) { (void)q; fake.icc_enabled++; return fake.icc_enable_ret; }
static int dwc3_qcom_read_usb2_speed(struct dwc3_qcom *q, int i) { (void)q; (void)i; return 0; }
static void dwc3_qcom_enable_interrupts(struct dwc3_qcom *q) { (void)q; }
static void dwc3_qcom_disable_interrupts(struct dwc3_qcom *q) { (void)q; }
static void dwc3_qcom_setbits(void *base, unsigned off, u32 bits) { (void)base; (void)off; (void)bits; }
static u32 dwc3_readl(struct dwc3 *d, unsigned reg) {
    (void)d;
    if (reg == DWC3_DCTL && (fake.regs[reg] & DWC3_DCTL_CSFTRST) && !fake.reset_timeout)
        fake.regs[reg] &= ~DWC3_DCTL_CSFTRST;
    if (reg == DWC3_DSTS)
        return (fake.running ^ fake.run_timeout) ? 0 : DWC3_DSTS_DEVCTRLHLT;
    return fake.regs[reg];
}
static void dwc3_writel(struct dwc3 *d, unsigned reg, u32 value) { (void)d; fake.regs[reg] = value; }
static void dwc3_gadget_dctl_write_safe(struct dwc3 *d, u32 value) {
    (void)d;
    if (value & DWC3_DCTL_CSFTRST) fake.reset_calls++;
    else fake.run_calls++;
    fake.regs[DWC3_DCTL] = value;
    fake.running = !!(value & DWC3_DCTL_RUN_STOP);
}
static void msleep(unsigned n) { (void)n; fake.delay_calls++; }
static void udelay(unsigned n) { (void)n; fake.delay_calls++; }
static void usleep_range(unsigned a, unsigned b) { (void)a; (void)b; fake.delay_calls++; }
static void __dwc3_gadget_set_speed(struct dwc3 *d) { (void)d; }
static void dwc3_pre_run_stop(struct dwc3 *d, int on) { (void)d; (void)on; }
static bool dwc3_has_imod(struct dwc3 *d) { (void)d; return false; }
static void dwc3_gadget_setup_nump(struct dwc3 *d) { (void)d; }
static int dwc3_gadget_start_config(struct dwc3 *d, int ep) { (void)d; (void)ep; fake.start_calls++; return fake.start_config_ret; }
static int __dwc3_gadget_ep_enable(struct dwc3_ep *ep, int action) { (void)action; return strcmp(ep->name, "ep0out") ? fake.enable1_ret : fake.enable0_ret; }
static void __dwc3_gadget_ep_disable(struct dwc3_ep *ep) { (void)ep; fake.ep_disable++; }
static void dwc3_ep0_out_start(struct dwc3 *d) { (void)d; }
static void dwc3_gadget_enable_irq(struct dwc3 *d) { (void)d; fake.irq_enable++; }
static void dwc3_enable_susphy(struct dwc3 *d, bool state) { (void)d; (void)state; fake.susphy_restore++; }
static void dwc3_ep0_send_delayed_status(struct dwc3 *d) { (void)d; }
static void dwc3_stop_active_transfers(struct dwc3 *d) { (void)d; }
static void reinit_completion(int *c) { *c = 0; }
static int wait_for_completion_timeout(int *c, int timeout) { (void)c; (void)timeout; return fake.setup_wait; }
static void dwc3_ep0_reset_state(struct dwc3 *d) { d->ep0state = EP0_SETUP_PHASE; fake.ep0_resets++; }
static void __dwc3_gadget_stop(struct dwc3 *d) { (void)d; fake.stop_calls++; }
static void usb_gadget_set_state(struct usb_gadget *g, int state) { g->state = state; }
static int dwc3_event_buffers_setup(struct dwc3 *d) { (void)d; fake.event_setup++; return 0; }
static void dwc3_disconnect_gadget_sleepable(struct dwc3 *d) { (void)d; fake.disconnect_calls++; }
static int dwc3_core_init_for_resume(struct dwc3 *d) { (void)d; return fake.init_ret; }
static void dwc3_set_prtcap(struct dwc3 *d, int role, bool ignore) { (void)d; (void)role; (void)ignore; fake.role_set++; }
static int phy_pm_runtime_get_sync(void *p) { (void)p; return 0; }
static void dwc3_otg_init(struct dwc3 *d) { (void)d; fake.otg_init++; }
static void dwc3_otg_host_init(struct dwc3 *d) { (void)d; }
#ifdef VARIANT_ORIGINAL
#include "reference-functions.inc"
#elif defined(VARIANT_DIAGNOSTIC)
#include "reference-functions-diagnostic.inc"
#else
#include "reference-functions-propagate.inc"
#endif
static int checks;
#define CHECK(expr) do { assert(expr); checks++; } while (0)
static struct device dev;
static struct usb_gadget gadget;
static struct dwc3_ep ep0 = { 0, "ep0out" }, ep1 = { 0, "ep0in" };
static struct dwc3 d;
static void reset(void) {
    memset(&fake, 0, sizeof(fake)); memset(&dev, 0, sizeof(dev));
    memset(&gadget, 0, sizeof(gadget)); memset(&d, 0, sizeof(d));
    fake.clk_fail_index = -1; fake.setup_wait = 1;
    d.dev = &dev; d.gadget = &gadget; d.gadget_driver = &d;
    d.softconnect = true; d.current_dr_role = DWC3_GCTL_PRTCAP_DEVICE;
    d.current_otg_role = DWC3_OTG_ROLE_DEVICE; d.eps[0] = &ep0; d.eps[1] = &ep1;
}
static void resume_error(int error) {
    int ret = dwc3_resume_common(&d, 0);
#ifdef VARIANT_PROPAGATE
    CHECK(ret == error);
#else
    (void)error; CHECK(ret == 0);
#endif
    CHECK(fake.susphy_restore > 0);
}
int main(void) {
    u32 status[2] = { 0, 0 }; int c0 = 0, c1 = 1;
    struct dwc3_qcom q = { .dev = &dev, .qscratch_base = (unsigned char *)status,
        .num_ports = 1, .num_clocks = 2, .clks = { &c0, &c1 } };
    reset(); CHECK(dwc3_qcom_suspend(&q, true) == 0);
    CHECK(fake.log_error == 1 && fake.clocks_disabled == 2 && q.is_suspended);
    reset(); q.is_suspended = false; status[0] = PWR_EVNT_LPM_IN_L2_MASK;
    CHECK(dwc3_qcom_suspend(&q, true) == 0 && fake.log_error == 0);
    reset(); q.is_suspended = false; fake.icc_disable_ret = -EIO;
    CHECK(dwc3_qcom_suspend(&q, true) == 0 && fake.log_warn == 1 && q.is_suspended);
    reset(); q.is_suspended = true; fake.icc_enable_ret = -EIO;
    CHECK(dwc3_qcom_resume(&q, true) == 0 && fake.log_warn == 1 && !q.is_suspended);
    reset(); q.is_suspended = true; fake.clk_fail_index = 1;
    CHECK(dwc3_qcom_resume(&q, true) == -EIO && q.is_suspended && fake.clocks_disabled == 1);
    reset(); fake.reset_timeout = true;
    CHECK(dwc3_gadget_soft_connect(&d) == -ETIMEDOUT && fake.run_calls == 0);
    reset(); fake.run_timeout = true;
    CHECK(dwc3_gadget_soft_connect(&d) == -ETIMEDOUT && d.pullups_connected);
    CHECK(fake.delay_calls == 2000);
    reset(); fake.run_timeout = true; d.pullups_connected = true; d.connected = true;
    CHECK(dwc3_gadget_soft_disconnect(&d) == -ETIMEDOUT);
    CHECK(!d.pullups_connected && !d.connected && gadget.state == USB_STATE_NOTATTACHED);
    reset(); d.pullups_connected = true; d.ep0state = 1; fake.setup_wait = 0;
    CHECK(dwc3_gadget_soft_disconnect(&d) == 0 && fake.log_warn == 1 && fake.ep0_resets == 1);
    reset(); d.gadget_driver = NULL;
    CHECK(dwc3_gadget_resume(&d) == 0 && fake.event_setup == 0);
    reset(); d.softconnect = false;
    CHECK(dwc3_gadget_resume(&d) == 0 && fake.event_setup == 0);
    reset(); fake.reset_timeout = true; resume_error(-ETIMEDOUT);
#ifdef VARIANT_ORIGINAL
    CHECK(fake.log_error == 0);
#else
    CHECK(fake.log_error == 1);
#endif
    reset(); fake.run_timeout = true; resume_error(-ETIMEDOUT);
#ifdef VARIANT_ORIGINAL
    CHECK(fake.log_error == 0);
#else
    CHECK(fake.log_error == 1);
#endif
    reset(); fake.reset_timeout = true; d.current_dr_role = DWC3_GCTL_PRTCAP_OTG;
    resume_error(-ETIMEDOUT);
    reset(); fake.reset_timeout = true; d.current_dr_role = DWC3_GCTL_PRTCAP_OTG;
    CHECK(dwc3_resume_common(&d, 1) == 0 && fake.reset_calls == 0);
    reset(); fake.init_ret = -EIO;
    CHECK(dwc3_resume_common(&d, 0) == -EIO && fake.reset_calls == 0);
    for (int stage = 0; stage < 3; stage++) {
        reset();
        if (stage == 0) fake.start_config_ret = -EIO;
        else if (stage == 1) fake.enable0_ret = -EINVAL;
        else fake.enable1_ret = -ENOMEM;
        int expected = stage == 0 ? -EIO : stage == 1 ? -EINVAL : -ENOMEM;
        CHECK(__dwc3_gadget_start(&d) == expected);
        int old_errors = fake.log_error;
        int ret = dwc3_gadget_soft_connect(&d);
#ifdef VARIANT_PROPAGATE
        CHECK(ret == expected && fake.run_calls == 0);
#else
        CHECK(ret == 0 && fake.run_calls == 1 && d.pullups_connected);
#endif
        /* Original start already logs its own failure; callback errno is lost. */
#ifdef VARIANT_ORIGINAL
        CHECK(fake.log_error == old_errors + 1);
#else
        CHECK(fake.log_error == old_errors + 2);
#endif
        reset();
        if (stage == 0) fake.start_config_ret = -EIO;
        else if (stage == 1) fake.enable0_ret = -EINVAL;
        else fake.enable1_ret = -ENOMEM;
        resume_error(expected);
    }
    reset(); fake.run_timeout = true; d.pullups_connected = true;
    CHECK(dwc3_gadget_suspend(&d) == -EAGAIN); /* recovery attempt does not authorize suspend */
    reset(); fake.run_timeout = true; d.pullups_connected = true; d.softconnect = false;
    CHECK(dwc3_gadget_suspend(&d) == 0); /* actual conditional: stop timeout is ignored if !softconnect */
    reset(); CHECK(dwc3_resume_common(&d, 0) == 0 && d.pullups_connected);
#ifdef VARIANT_ORIGINAL
    const char *variant = "original";
#elif defined(VARIANT_DIAGNOSTIC)
    const char *variant = "diagnostic";
#else
    const char *variant = "propagate";
#endif
    printf("{\"variant\":\"%s\",\"assertions\":%d,\"actual_functions_extracted\":10,\"fake_boundaries_only\":true,\"phone_accessed\":false}\n", variant, checks);
    return 0;
}
