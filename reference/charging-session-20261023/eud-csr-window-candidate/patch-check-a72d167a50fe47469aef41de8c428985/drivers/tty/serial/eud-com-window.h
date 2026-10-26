/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef _QCOM_EUD_COM_WINDOW_H
#define _QCOM_EUD_COM_WINDOW_H

#include <linux/types.h>

/* Built-in, explicit consumer only. No exported symbol or userspace switch.
 * Software calls suppress COM I/O; the separate explicit CSR stage saves and
 * restores only known 0/1 CSR_EUD_EN values. Neither grants DP/DM, analog
 * high-Z, USB routing or charging permission. AHB2PHY is never borrowed.
 */
enum eud_com_window_state {
        EUD_COM_ACTIVE,
        EUD_COM_QUIETING,
        EUD_COM_QUIET,
        EUD_COM_CANCELLED,
        EUD_COM_REMOVED,
};

struct eud_com_window_result {
        u64 cookie;
        enum eud_com_window_state state;
        bool software_quiet;
        bool cancelled;
        bool restored;
        bool csr_touched;
        bool hardware_owned;
        bool ahb2phy_touched;
        int error;
        int restore_error;
};

/* Process context outside EUD callbacks; no UART/tx/console lock held.
 * Calls return with no EUD lock held. A bounded owner session
 * must cancel/end explicitly. Cancellation never resumes hardware producers.
 * A removed endpoint invalidates the token and cannot be restored by end().
 */
int eud_com_quiet_begin(struct eud_com_window_result *result);
int eud_com_quiet_cancel(u64 cookie, struct eud_com_window_result *result);
int eud_com_quiet_end(u64 cookie, struct eud_com_window_result *result);

/* Same-image internal API only. No callback/atomic context or held EUD lock.
 * The caller owns powered MMIO and pre-remove cancellation/join separately.
 * begin requires completed software quiet and a current exact cookie; it
 * consumes one supported CSR borrow per quiet session, including old value 0.
 * restore is explicit, including after cancel; readback failure keeps the
 * hardware owner and prevents quiet_end from resuming producers. A successful
 * retry reports restored while retaining first enter/restore error history;
 * error is this call's result. Removed MMIO can never be restored by this API.
 * disabled_verified attests only the last CSR read, not electrical routing.
 */
struct eud_com_csr_result {
        u64 cookie;
        bool software_quiet;
        bool cancelled;
        bool hardware_owned;
        bool saved_valid;
        bool readback_valid;
        bool disabled_verified;
        bool restored;
        bool removed;
        bool csr_touched;
        u32 saved_value;
        u32 readback;
        int error;
        int enter_error;
        int restore_error;
};

int eud_com_csr_begin(u64 cookie, struct eud_com_csr_result *result);
int eud_com_csr_restore(u64 cookie, struct eud_com_csr_result *result);

#endif
