// SPDX-License-Identifier: GPL-2.0-only
#include <linux/efi.h>
#include <linux/errno.h>
#include <linux/init.h>
#include <linux/io.h>
#include <linux/of.h>
#include <linux/string.h>
#include "samurai-eud-handoff.h"

#define SAMURAI_EUD_EFI_GUID_EXPAND(...) EFI_GUID(__VA_ARGS__)
static const efi_guid_t handoff_guid = SAMURAI_EUD_EFI_GUID_EXPAND(SAMURAI_EUD_GUID_WORDS);
static unsigned long handoff_physical __ro_after_init = EFI_INVALID_TABLE_ADDR;
static bool handoff_seen __initdata;

void __init samurai_eud_handoff_config(const efi_guid_t *guid, unsigned long table)
{
	if (efi_guidcmp(*guid, handoff_guid))
		return;
	/* Duplicate/invalid first publication is sticky for this kernel boot. */
	if (handoff_seen)
		handoff_physical = EFI_INVALID_TABLE_ADDR;
	else
		handoff_physical = table;
	handoff_seen = true;
}

int samurai_eud_handoff_copy(struct samurai_eud_handoff *record)
{
	struct samurai_eud_handoff first, second;
	efi_memory_desc_t descriptor;
	unsigned long physical = handoff_physical;
	unsigned long long size, offset;
	void *mapping;
	int ret;

	if (!record)
		return -EINVAL;
	if (!efi_enabled(EFI_BOOT) || !efi_enabled(EFI_CONFIG_TABLES) ||
	    !efi_enabled(EFI_64BIT) || !of_machine_is_compatible("realme,samurai"))
		return -EOPNOTSUPP;
	if (physical == EFI_INVALID_TABLE_ADDR || !physical || (physical & 4095UL))
		return -ENODATA;
	ret = efi_mem_desc_lookup(physical, &descriptor);
	if (ret)
		return ret;
	if (descriptor.type != EFI_RESERVED_TYPE || !(descriptor.attribute & EFI_MEMORY_WB) ||
	    (descriptor.attribute & (EFI_MEMORY_RUNTIME | EFI_MEMORY_RP)) ||
	    !descriptor.num_pages || descriptor.num_pages > (~0ULL >> EFI_PAGE_SHIFT) ||
	    physical < descriptor.phys_addr)
		return -EPROTO;
	size = descriptor.num_pages << EFI_PAGE_SHIFT;
	offset = physical - descriptor.phys_addr;
	if (offset >= size || size - offset < sizeof(first))
		return -EOVERFLOW;
	mapping = memremap(physical, sizeof(first), MEMREMAP_WB);
	if (!mapping)
		return -ENOMEM;
	memcpy(&first, mapping, sizeof(first));
	rmb();
	memcpy(&second, mapping, sizeof(second));
	memunmap(mapping);
	if (memcmp(&first, &second, sizeof(first)))
		return -EAGAIN;
	if (!samurai_eud_handoff_valid(&first, physical))
		return -EBADMSG;
	*record = first;
	return 0;
}
