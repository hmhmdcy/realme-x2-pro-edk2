/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef _QCOM_EUD_COM_WINDOW_H
#define _QCOM_EUD_COM_WINDOW_H

#include <linux/types.h>

/* Built-in, explicit consumer only. No exported symbol or userspace switch.
 * This API suppresses COM software I/O; it never changes CSR/AHB2PHY and does
 * not grant DP/DM, analog high-Z, USB routing or charging permission.
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

#endif
