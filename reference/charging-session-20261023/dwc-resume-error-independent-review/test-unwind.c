#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
typedef uint32_t u32;
typedef int pm_message_t;
#define EXPORT_SYMBOL_GPL(x)
#define PMSG_AUTO_RESUME 1
#define PMSG_RESUME 0
#define PMSG_IS_AUTO(x) ((x) == PMSG_AUTO_RESUME)
#define DWC3_GCTL_PRTCAP_HOST 1
#define DWC3_GCTL_PRTCAP_DEVICE 2
#define DWC3_GCTL_PRTCAP_OTG 3
#define DWC3_OTG_ROLE_HOST 1
#define DWC3_OTG_ROLE_DEVICE 2
#define DWC3_GUSB2PHYCFG(i) (i)
#define DWC3_GUSB2PHYCFG_SUSPHY 1
#define DWC3_GUSB2PHYCFG_ENBLSLPM 2
#define ACTIVE 1
#define SUSPENDED 0
struct clock { int count; };
struct reset { bool asserted; };
struct device { int runtime_status, disabled; };
struct dwc3 {
        int current_dr_role, current_otg_role, num_usb2_ports, num_usb3_ports;
        bool needs_full_reinit, dis_u2_susphy_quirk, dis_enblslpm_quirk, susphy_state;
        bool pending_events, softconnect;
        struct device *dev;
        void **usb2_generic_phy, **usb3_generic_phy;
        struct clock *bus_clk, *ref_clk, *susp_clk, *utmi_clk, *pipe_clk;
        struct reset *reset;
        void *gadget_driver;
        int irq_gadget;
};
static struct clock clocks[5];
static struct device device;
static struct dwc3 dwc;
static int init_error, run_error, phy_init_refs, phy_power_refs;
static int events_setup, events_cleanup, gadget_start, marks_busy;
static int reset_deassert_calls, reset_assert_calls;
static bool gate;
static int clk_prepare_enable(struct clock *c) { if(c)c->count++; return 0; }
static void clk_disable_unprepare(struct clock *c) { if(c){assert(c->count > 0); c->count--;} }
static int reset_control_deassert(struct reset *r) { reset_deassert_calls++;if(r)r->asserted = false; return 0; }
static int reset_control_assert(struct reset *r) { reset_assert_calls++;if(r)r->asserted = true; return 0; }
/* Hardware boundaries: successful core init acquires PHY init/power state.
 * The actual surrounding init_for_resume and core_exit bodies are included.
 */
static int dwc3_core_init(struct dwc3 *d) {
        if (init_error) return init_error;
        phy_init_refs++; phy_power_refs++; return 0;
}
static void dwc3_event_buffers_cleanup(struct dwc3 *d) { events_cleanup++; }
static void dwc3_phy_power_off(struct dwc3 *d) { assert(phy_power_refs > 0); phy_power_refs--; }
static void dwc3_phy_exit(struct dwc3 *d) { assert(phy_init_refs > 0); phy_init_refs--; }
static int dwc3_core_soft_reset(struct dwc3 *d) { return 0; }
static void dwc3_event_buffers_setup(struct dwc3 *d) { events_setup++; }
static int __dwc3_gadget_start(struct dwc3 *d) { gadget_start++; return 0; }
static int dwc3_gadget_run_stop(struct dwc3 *d, int on) { assert(on); return run_error; }
static bool dwc3_gadget_window_busy(struct dwc3 *d) { return false; }
static int dwc3_gadget_window_pm_enter(struct dwc3 *d) { assert(!gate); gate = true; return 0; }
static void dwc3_gadget_window_pm_exit(struct dwc3 *d) { assert(gate); gate = false; }
static void dwc3_set_prtcap(struct dwc3 *d, int role, bool force) { }
static bool device_may_wakeup(struct device *d) { return false; }
static u32 dwc3_readl(struct dwc3 *d, u32 reg) { return 0; }
static void dwc3_writel(struct dwc3 *d, u32 reg, u32 value) { }
static void phy_pm_runtime_get_sync(void *p) { }
static void dwc3_otg_init(struct dwc3 *d) { }
static void dwc3_otg_host_init(struct dwc3 *d) { }
static void dwc3_enable_susphy(struct dwc3 *d, bool on) { }
static void pm_runtime_put(struct device *d) { }
static void enable_irq(int irq) { }
static void pm_runtime_mark_last_busy(struct device *d) { marks_busy++; }
static void pinctrl_pm_select_default_state(struct device *d) { }
static void pm_runtime_disable(struct device *d) { d->disabled++; }
static int pm_runtime_set_active(struct device *d) { d->runtime_status = ACTIVE; return 0; }
static void pm_runtime_set_suspended(struct device *d) { d->runtime_status = SUSPENDED; }
static void pm_runtime_enable(struct device *d) { assert(d->disabled > 0); d->disabled--; }
#include "actual-functions.inc"

static void setup(void)
{
        memset(clocks, 0, sizeof(clocks)); memset(&device, 0, sizeof(device));
        /* This board's legacy child has no core clocks/reset properties;
         * the parent glue owns those resources. NULL optional APIs are no-op.
         */
        dwc = (struct dwc3) { .current_dr_role = DWC3_GCTL_PRTCAP_DEVICE,
            .dev = &device, .gadget_driver = &device, .softconnect = true };
        init_error = run_error = phy_init_refs = phy_power_refs = 0;
        events_setup = events_cleanup = gadget_start = marks_busy = 0; gate = false;
        reset_deassert_calls = reset_assert_calls = 0;
}
static void resources_left_enabled(void)
{
        for (int i = 0; i < 5; i++) assert(clocks[i].count == 0);
        assert(phy_init_refs == 1 && phy_power_refs == 1);
        assert(reset_deassert_calls == 1 && !reset_assert_calls);
        assert(events_setup == 1 && gadget_start == 1 && !events_cleanup && !gate);
}
int main(void)
{
        setup(); run_error = -ETIMEDOUT;
        assert(dwc3_runtime_resume(&dwc) == -ETIMEDOUT);
        resources_left_enabled(); assert(!marks_busy);
        puts("reproduced: legacy runtime child returns failure with PHY/core initialized and no unwind");

        setup(); run_error = -ETIMEDOUT;
        assert(dwc3_pm_resume(&dwc) == -ETIMEDOUT);
        resources_left_enabled(); assert(device.runtime_status == SUSPENDED && !device.disabled);
        puts("reproduced: legacy system caller marks runtime suspended while PHY/core remain initialized");

        setup(); init_error = -EIO;
        assert(dwc3_pm_resume(&dwc) == -EIO);
        for (int i = 0; i < 5; i++) assert(!clocks[i].count);
        assert(reset_assert_calls == 1 && !phy_init_refs && !phy_power_refs && !gadget_start);
        assert(device.runtime_status == SUSPENDED && !device.disabled && !gate);
        puts("control: original core-init failure runs clock/reset unwind before suspended result");
        return 0;
}
