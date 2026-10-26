/* SPDX-License-Identifier: GPL-2.0-only */
/* Offline candidate only. No I2C access and no production whitelist change. */
#ifndef SM_TCA_REFERENCE_H
#define SM_TCA_REFERENCE_H
#include "../../charging-management-20261023/gauge-protocol.h"

enum sm_tca_class {
	SM_TCA_EXISTING_FAULT, SM_TCA_UNVERIFIED, SM_TCA_INCOHERENT,
	SM_TCA_ALERT_OR_FAULT, SM_TCA_BAD_OPERATION, SM_TCA_NO_REQUEST,
	SM_TCA_UNEXPLAINED, SM_TCA_TC_REQUEST_HOLD, SM_TCA_NORMAL_TERMINATION,
};

/* TI SLUUA65E 12.2.26/28/32 show 32-bit status. 0056 explicitly includes
 * the fourth reserved byte: do not shorten it to three bytes/length seven.
 * 0055 ChargingStatus is a separate 16-bit status.
 */
static inline int sm_tca_payload_bytes(unsigned int command)
{
	switch (command) {
	case 0x0050: case 0x0052: case 0x0056: return 4;
	case 0x0055: return 2;
	default: return -EINVAL;
	}
}

/* Decode a supplied saved packet only. A valid frame does not assert that
 * factory 2719 implements the standard TI 2610 status layout/causal model.
 */
static inline int sm_tca_decode(const unsigned char *packet, unsigned int bytes,
			       unsigned int command, unsigned int *value)
{
	unsigned int i, sum = 0;
	int payload = sm_tca_payload_bytes(command);

	if (!packet || !value || payload < 0) return -EINVAL;
	if (bytes != 36 || packet[35] != payload + 4) return -EMSGSIZE;
	if (sm_le16(packet) != command) return -EAGAIN;
	for (i = 0; i < (unsigned int)payload + 2; i++) sum += packet[i];
	if (((sum + packet[34]) & 255U) != 255U) return -EBADMSG;
	*value = payload == 4 ? sm_le32(packet + 2) : sm_le16(packet + 2);
	return 0;
}

struct sm_tca_evidence {
	/* compatibility_verified is an independently established pack-specific
 * evidence gate; successful sm_tca_decode must never set it automatically.
 */
	int compatibility_verified, complete_fresh, coherent;
	int existing_hard_latch, existing_timeout, source_allowed, policy_good_except_tca;
	int independent_full;
	unsigned int battery_before, battery_after;
	unsigned int safety_alert, safety_status, pf_alert, pf_status;
	unsigned int gauging, operation, manufacturing;
};

static inline enum sm_tca_class sm_tca_classify(const struct sm_tca_evidence *e)
{
	const unsigned int status_mask = 0xd860U; /* OCA/TCA/OTA/TDA/DSG/FC */
	const unsigned int gauging_known = 0x001fbeffU;

	/* An old error is authoritative even if a new normal termination arrives. */
	if (e->existing_hard_latch || e->existing_timeout)
		return SM_TCA_EXISTING_FAULT;
	if (!e->compatibility_verified || !e->complete_fresh)
		return SM_TCA_UNVERIFIED;
	if (!e->coherent || ((e->battery_before ^ e->battery_after) & status_mask))
		return SM_TCA_INCOHERENT;
	if (e->safety_alert || e->safety_status || e->pf_alert || e->pf_status ||
	    (e->battery_after & 0x9800U)) /* OCA/OTA/TDA never explain normal TC */
		return SM_TCA_ALERT_OR_FAULT;
	if ((e->gauging & ~gauging_known) ||
	    sm_gauge_protection_state(0x2719, e->safety_status, e->pf_status,
				     e->operation, e->manufacturing))
		return SM_TCA_BAD_OPERATION;
	if (!(e->battery_after & 0x4000U))
		return SM_TCA_NO_REQUEST;
	/* TCA causal rule in 4.8: with zero SafetyAlert it needs TC and CHARGE
 * mode. FET CHG bit2 is not this mode; it may be off at normal termination.
 */
	if (!(e->gauging & 0x08U) || (e->gauging & 0x40U) ||
	    (e->battery_after & 0x40U))
		return SM_TCA_UNEXPLAINED;
	if (!e->source_allowed || !e->policy_good_except_tca || !e->independent_full)
		return SM_TCA_TC_REQUEST_HOLD;
	return SM_TCA_NORMAL_TERMINATION;
}

/* Classification can end a successfully completed charging cycle only. It
 * neither clears an old latch nor authorizes charging/recharge or FET writes.
 */
static inline int sm_tca_may_end_cycle(enum sm_tca_class result)
{
	return result == SM_TCA_NORMAL_TERMINATION;
}
#endif
