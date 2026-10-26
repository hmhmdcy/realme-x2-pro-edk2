/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef LINUX_SAMURAI_EUD_HANDOFF_H
#define LINUX_SAMURAI_EUD_HANDOFF_H
#include <linux/efi.h>
#include <linux/init.h>
#include <linux/kconfig.h>
#include "samurai-eud-handoff-wire.h"

/* Discovery belongs to the actual EFI configuration-table parser, never a
 * module parameter, text log, userspace file or inferred absent COM device.
 * copy validates boot evidence only; it grants no resource/route ownership.
 */
#if IS_ENABLED(CONFIG_QCOM_SAMURAI_EUD_HANDOFF)
void __init samurai_eud_handoff_config(const efi_guid_t *guid, unsigned long table);
int samurai_eud_handoff_copy(struct samurai_eud_handoff *record);
#else
static inline void samurai_eud_handoff_config(const efi_guid_t *guid, unsigned long table) { }
static inline int samurai_eud_handoff_copy(struct samurai_eud_handoff *record)
{
	return -EOPNOTSUPP;
}
#endif
#endif
