/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uint32_t u32;
typedef int pm_message_t;
#define PMSG_IS_AUTO(msg) ((msg) == 1)
#define DWC3_GCTL_PRTCAP_HOST 1
#define DWC3_GCTL_PRTCAP_DEVICE 2
#define DWC3_GCTL_PRTCAP_OTG 3
#define DWC3_OTG_ROLE_HOST 1
#define DWC3_OTG_ROLE_DEVICE 2
#define DWC3_GUSB2PHYCFG(i) (i)
#define DWC3_GUSB2PHYCFG_SUSPHY 1
#define DWC3_GUSB2PHYCFG_ENBLSLPM 2
struct dwc3 {
    int current_dr_role, current_otg_role, num_usb2_ports, num_usb3_ports;
    bool needs_full_reinit, dis_u2_susphy_quirk, dis_enblslpm_quirk, susphy_state;
    void *dev;
    void **usb2_generic_phy, **usb3_generic_phy;
};
static int enter_error, init_error, resume_error;
static int enters, exits, inits, resumes, role_sets, susphy_sets, gate_owned;
static bool wakeup;
static void reset(void) {
    enter_error=init_error=resume_error=0;
    enters=exits=inits=resumes=role_sets=susphy_sets=gate_owned=0;
    wakeup=false;
}
static int dwc3_gadget_window_pm_enter(struct dwc3 *d) {
    enters++;if(enter_error)return enter_error;assert(!gate_owned);gate_owned=1;return 0;
}
static void dwc3_gadget_window_pm_exit(struct dwc3 *d) { assert(gate_owned);gate_owned=0;exits++; }
static int dwc3_core_init_for_resume(struct dwc3 *d) { assert(gate_owned);inits++;return init_error; }
static void dwc3_set_prtcap(struct dwc3 *d,int role,bool force) { assert(gate_owned);role_sets++; }
static int dwc3_gadget_resume(struct dwc3 *d) { assert(gate_owned);resumes++;return resume_error; }
static bool device_may_wakeup(void *d) { return wakeup; }
static u32 dwc3_readl(struct dwc3 *d,u32 reg) { return 0; }
static void dwc3_writel(struct dwc3 *d,u32 reg,u32 value) { }
static void phy_pm_runtime_get_sync(void *p) { }
static void dwc3_otg_init(struct dwc3 *d) { }
static void dwc3_otg_host_init(struct dwc3 *d) { }
static void dwc3_enable_susphy(struct dwc3 *d,bool on) { susphy_sets++; }
#define dwc3_resume_common original_resume_common
#include "original-resume.inc"
#undef dwc3_resume_common
#include "candidate-resume.inc"

int main(void) {
    struct dwc3 d={.current_dr_role=DWC3_GCTL_PRTCAP_DEVICE};
    reset();resume_error=-ETIMEDOUT;
    assert(original_resume_common(&d,1)==0 && resumes==1 && exits==1);
    puts("original: gadget timeout incorrectly returned success");

    reset();resume_error=-ETIMEDOUT;
    assert(dwc3_resume_common(&d,1)==-ETIMEDOUT && resumes==1 && exits==1 && !gate_owned);
    puts("ok: runtime gadget error propagated and gate released");

    reset();resume_error=-EREMOTEIO;
    assert(dwc3_resume_common(&d,0)==-EREMOTEIO && resumes==1 && exits==1 && !susphy_sets);
    puts("ok: system gadget error propagated without later success actions");

    reset();init_error=-EIO;
    assert(dwc3_resume_common(&d,0)==-EIO && !resumes && exits==1 && !gate_owned);
    puts("ok: original core-init error path preserved");

    reset();
    assert(!dwc3_resume_common(&d,0) && resumes==1 && exits==1 && susphy_sets==1);
    puts("ok: successful device resume preserved");

    reset();enter_error=-EBUSY;
    assert(dwc3_resume_common(&d,1)==-EBUSY && !inits && !resumes && !exits);
    puts("ok: rejected PM claim does not release another gate");

    reset();d.current_dr_role=DWC3_GCTL_PRTCAP_OTG;d.current_otg_role=DWC3_OTG_ROLE_DEVICE;resume_error=-EIO;
    assert(dwc3_resume_common(&d,0)==-EIO && resumes==1 && exits==1 && !gate_owned);
    puts("ok: matching OTG device branch reports its error");

    reset();d.current_dr_role=DWC3_GCTL_PRTCAP_HOST;
    assert(!dwc3_resume_common(&d,0) && !resumes && inits==1 && exits==1);
    puts("ok: host full-init path preserved");

    reset();d.current_dr_role=DWC3_GCTL_PRTCAP_OTG;
    assert(!dwc3_resume_common(&d,1) && !resumes && !inits && exits==1);
    puts("ok: automatic OTG no-op path preserved");
    return 0;
}
