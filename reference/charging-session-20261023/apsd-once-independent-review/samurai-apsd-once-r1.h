/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef SAMURAI_APSD_ONCE_H
#define SAMURAI_APSD_ONCE_H

/* Protocol core only: no I/O, locks, current allowance or implicit retry.
 * The bound session owner serializes every call. An attach/detach is a
 * physical PMIC observation, never a logical gadget disconnect/reconnect.
 * Before claim/write, that owner must hold valid PD/role/route, power,
 * EUD, DWC HALT and PHY high-Z ownership. This header cannot establish it.
 */
#ifdef __KERNEL__
#include <linux/errno.h>
#else
#include <errno.h>
#endif

enum samurai_apsd_phase {
	SAMURAI_APSD_DETACHED,
	SAMURAI_APSD_FIRST,
	SAMURAI_APSD_READY,
	SAMURAI_APSD_WRITING,
	SAMURAI_APSD_WAIT_CLEAR,
	SAMURAI_APSD_WAIT_DONE,
	SAMURAI_APSD_COMPLETE,
	SAMURAI_APSD_BYPASSED,
	SAMURAI_APSD_FAILED,
	SAMURAI_APSD_CANCELLED,
};

enum samurai_apsd_action {
	SAMURAI_APSD_WAIT,
	SAMURAI_APSD_REQUEST,
	SAMURAI_APSD_NEW_DONE,
	SAMURAI_APSD_NO_RERUN,
};

struct samurai_apsd_once {
	unsigned long long epoch;
	unsigned long long last_ms;
	unsigned long long last_read_serial;
	unsigned long long deadline_ms;
	enum samurai_apsd_phase phase;
	unsigned char first_result;
	unsigned char new_result;
	int attempted;
	int error;
};

/* Zero initialization is DETACHED. Epochs are never reused, even at overflow.
 * Repeated attach cannot rearm a failed, cancelled or completed session.
 */
static inline int samurai_apsd_attach(struct samurai_apsd_once *s,
		unsigned long long now_ms)
{
	if (s->phase != SAMURAI_APSD_DETACHED)
		return -EBUSY;
	if (s->epoch == ~0ULL)
		return -EOVERFLOW;
	*s = (struct samurai_apsd_once) {
		.epoch = s->epoch + 1,
		.last_ms = now_ms,
		.phase = SAMURAI_APSD_FIRST,
	};
	return 0;
}

static inline int samurai_apsd_epoch(struct samurai_apsd_once *s,
		unsigned long long epoch)
{
	return !epoch || epoch != s->epoch ||
		s->phase == SAMURAI_APSD_DETACHED ? -ESTALE : 0;
}

/* This invalidates protocol work; it does not release a hardware token.
 * The owner must cancel/join and restore its components independently.
 */
static inline void samurai_apsd_detach(struct samurai_apsd_once *s)
{
	s->phase = SAMURAI_APSD_DETACHED;
	s->error = -ENODEV;
}

static inline int samurai_apsd_fail(struct samurai_apsd_once *s,
		unsigned long long epoch, int error)
{
	int ret = samurai_apsd_epoch(s, epoch);

	if (ret)
		return ret;
	if (s->phase == SAMURAI_APSD_FAILED ||
	    s->phase == SAMURAI_APSD_CANCELLED)
		return s->error;
	s->error = error < 0 ? error : -EIO;
	s->phase = SAMURAI_APSD_FAILED;
	return s->error;
}

static inline int samurai_apsd_cancel(struct samurai_apsd_once *s,
		unsigned long long epoch)
{
	int ret = samurai_apsd_epoch(s, epoch);

	if (ret)
		return ret;
	if (s->phase == SAMURAI_APSD_FAILED ||
	    s->phase == SAMURAI_APSD_CANCELLED)
		return s->error;
	s->error = -ECANCELED;
	s->phase = SAMURAI_APSD_CANCELLED;
	return s->error;
}

static inline int samurai_apsd_clock(struct samurai_apsd_once *s,
		unsigned long long epoch, unsigned long long now_ms)
{
	int ret = samurai_apsd_epoch(s, epoch);

	if (ret)
		return ret;
	if (s->phase == SAMURAI_APSD_FAILED ||
	    s->phase == SAMURAI_APSD_CANCELLED)
		return s->error;
	if (now_ms < s->last_ms)
		return samurai_apsd_fail(s, epoch, -ERANGE);
	s->last_ms = now_ms;
	if ((s->phase == SAMURAI_APSD_WRITING ||
	     s->phase == SAMURAI_APSD_WAIT_CLEAR ||
	     s->phase == SAMURAI_APSD_WAIT_DONE) &&
	    now_ms >= s->deadline_ms)
		return samurai_apsd_fail(s, epoch, -ETIMEDOUT);
	return 0;
}

/* A serial identifies a NEW stable two-snapshot PMIC read in this session.
 * Cached/repeated reads cannot supply the clear -> new DONE observation.
 * Only exact SDP/CDP is eligible: ambiguous/QC/other results bypass rerun.
 * This intentionally does not copy the OEM mixed-result bit test.
 */
static inline int samurai_apsd_sample(struct samurai_apsd_once *s,
		unsigned long long epoch, unsigned long long now_ms,
		unsigned long long read_serial, unsigned char status,
		unsigned char result)
{
	int ret = samurai_apsd_epoch(s, epoch);

	if (ret)
		return ret;
	if (!read_serial || read_serial <= s->last_read_serial)
		return -ESTALE;
	ret = samurai_apsd_clock(s, epoch, now_ms);
	if (ret)
		return ret;
	if (s->phase == SAMURAI_APSD_WRITING)
		return -EBUSY;
	s->last_read_serial = read_serial;
	result &= 0x7f;
	switch (s->phase) {
	case SAMURAI_APSD_FIRST:
		if (!(status & 1))
			return SAMURAI_APSD_WAIT;
		s->first_result = result;
		if (!(status & 2) && (result == 1 || result == 4)) {
			s->phase = SAMURAI_APSD_READY;
			return SAMURAI_APSD_REQUEST;
		}
		s->phase = SAMURAI_APSD_BYPASSED;
		return SAMURAI_APSD_NO_RERUN;
	case SAMURAI_APSD_READY:
		/* Do not execute a previously selected request after the stable
		 * source changed before the owner obtained all hardware windows.
		 */
		if (!(status & 1) || (status & 2) || result != s->first_result)
			return samurai_apsd_fail(s, epoch, -EAGAIN);
		return SAMURAI_APSD_REQUEST;
	case SAMURAI_APSD_WAIT_CLEAR:
		if (!(status & 1))
			s->phase = SAMURAI_APSD_WAIT_DONE;
		return SAMURAI_APSD_WAIT;
	case SAMURAI_APSD_WAIT_DONE:
		if (!(status & 1))
			return SAMURAI_APSD_WAIT;
		s->new_result = result;
		s->phase = SAMURAI_APSD_COMPLETE;
		return SAMURAI_APSD_NEW_DONE;
	case SAMURAI_APSD_COMPLETE:
		return SAMURAI_APSD_WAIT; /* completion is emitted once */
	case SAMURAI_APSD_BYPASSED:
		return SAMURAI_APSD_NO_RERUN;
	default:
		return -EINVAL;
	}
}

/* Claim BEFORE the one command transfer. An unsuccessful or uncertain
 * transfer consumes the attempt until actual detach; it must not be retried
 * by polling. The caller's absolute deadline uses the same monotonic clock.
 * Revalidate physical/PD/role/token state immediately before the bus write.
 */
static inline int samurai_apsd_claim(struct samurai_apsd_once *s,
		unsigned long long epoch, unsigned long long now_ms,
		unsigned long long deadline_ms)
{
	int ret = samurai_apsd_clock(s, epoch, now_ms);

	if (ret)
		return ret;
	if (s->phase != SAMURAI_APSD_READY || s->attempted)
		return -EALREADY;
	if (deadline_ms <= now_ms)
		return -EINVAL;
	s->attempted = 1;
	s->deadline_ms = deadline_ms;
	s->phase = SAMURAI_APSD_WRITING;
	return 0;
}

static inline int samurai_apsd_write_done(struct samurai_apsd_once *s,
		unsigned long long epoch, unsigned long long now_ms, int write_error)
{
	int ret = samurai_apsd_clock(s, epoch, now_ms);

	if (ret)
		return ret;
	if (s->phase != SAMURAI_APSD_WRITING)
		return -EALREADY;
	if (write_error)
		return samurai_apsd_fail(s, epoch, write_error);
	s->phase = SAMURAI_APSD_WAIT_CLEAR;
	return 0;
}

#endif
