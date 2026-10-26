/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef SAMURAI_CHARGE_CYCLE_HOLD_H
#define SAMURAI_CHARGE_CYCLE_HOLD_H
#include "charge-cycle.h"

/* The caller may exclude an interval only after this same driver successfully
 * stopped hardware charging. It also requires a fresh, complete known-source
 * sample; an unknown source or failed stop must retain conservative counting.
 * This pauses accumulated time. It never completes a cycle or erases a timeout.
 */
static inline unsigned int sm_cycle_update_held(struct sm_charge_cycle *c,
		sm_cycle_ns now, int source, int full_good, int confirmed_hold)
{
	if (confirmed_hold && source == 1 && c->attached && !c->timed_out &&
	    now >= c->last_ns && c->anchor_ns <= c->last_ns)
		c->anchor_ns += now - c->last_ns;
	return sm_cycle_update(c, now, source, full_good);
}
#endif
