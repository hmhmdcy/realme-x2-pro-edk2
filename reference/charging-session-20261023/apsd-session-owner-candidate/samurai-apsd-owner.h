/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef _DWC3_SAMURAI_APSD_OWNER_H
#define _DWC3_SAMURAI_APSD_OWNER_H
#include <linux/kconfig.h>
struct dwc3;
enum dwc3_apsd_fence {
	DWC3_APSD_RUNTIME = 1,
	DWC3_APSD_SYSTEM = 2,
	DWC3_APSD_CORE = 4,
	DWC3_APSD_UDC = 8,
	DWC3_APSD_EXIT = 16,
};
#if IS_ENABLED(CONFIG_USB_DWC3_SAMURAI_APSD_OWNER)
void dwc3_apsd_owner_bind(struct dwc3 *dwc);
int dwc3_apsd_owner_pause(struct dwc3 *dwc, unsigned int reason);
void dwc3_apsd_owner_resume(struct dwc3 *dwc, unsigned int reason);
void dwc3_apsd_owner_stop_pre(struct dwc3 *dwc);
void dwc3_apsd_owner_stop_post(struct dwc3 *dwc);
void dwc3_apsd_owner_unbind(struct dwc3 *dwc);
void dwc3_apsd_owner_core_exit(struct dwc3 *dwc);
#else
static inline void dwc3_apsd_owner_bind(struct dwc3 *dwc) {}
static inline int dwc3_apsd_owner_pause(struct dwc3 *dwc, unsigned int r)
{
	return 0;
}
static inline void dwc3_apsd_owner_resume(struct dwc3 *dwc, unsigned int r) {}
static inline void dwc3_apsd_owner_stop_pre(struct dwc3 *dwc) {}
static inline void dwc3_apsd_owner_stop_post(struct dwc3 *dwc) {}
static inline void dwc3_apsd_owner_unbind(struct dwc3 *dwc) {}
static inline void dwc3_apsd_owner_core_exit(struct dwc3 *dwc) {}
#endif
#endif
