/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef SAMURAI_USBIN_INIT_CORE_H
#define SAMURAI_USBIN_INIT_CORE_H
/* Only this bit is writable. Times/sample intervals are conservative
 * engineering choices for this diagnostic, not an OEM timing requirement. */
#define UI_CFG 0x1358U
#define UI_BIT 0x80U
#define UI_WAIT_MS 300000ULL
#define UI_STABLE_MS 500ULL
#define UI_POLL_MS 250U
#define UI_FRESH_MS 250ULL
enum ui_phase { UI_OBSERVED, UI_WAIT_OFF, UI_CLEAR_VERIFIED, UI_RESTORED,
	UI_COMMITTED, UI_TIMEOUT, UI_ERROR, UI_CANCELLED };
enum ui_op { UI_OBSERVE, UI_CLEAR, UI_RESTORE };
struct ui_snapshot { unsigned char raw[7], cfg; };
struct ui_ops {
	void *ctx;
	int (*snapshot)(void *ctx, struct ui_snapshot *s);
	int (*config)(void *ctx, unsigned int *value);
	int (*write_bit)(void *ctx, unsigned int value);
	unsigned long long (*now_ms)(void *ctx);
};
struct ui_state {
	enum ui_phase phase;
	enum ui_op op;
	unsigned long long started_ms, deadline_ms, first_ms;
	unsigned long long pre_started_ms, prewrite_ms, post_ms;
	unsigned int off_samples;
	int running, clear_used, have_first, old_valid, old_bit;
	int write_attempted, write_return, readback_error, post_error, error;
	int pending_restore, commit_allowed, committed, unknown_write, changed;
	int clear_error, clear_write_return;
	unsigned int before_cfg, after_cfg;
	struct ui_snapshot first, pre, post, saved;
};
static inline int ui_off(const struct ui_snapshot *s)
{
	/* Same physical-off predicates as the fixed input provider: USBIN
	 * plugin, Type-C VBUS/CC attach and state attach must independently be off. */
	return !(s->raw[2] & 0x10) && !(s->raw[5] & 0x21) && !(s->raw[4] & 0x20);
}
static inline int ui_raw_equal(const struct ui_snapshot *a, const struct ui_snapshot *b)
{
	unsigned int i;
	for (i = 0; i < 7; i++) if (a->raw[i] != b->raw[i]) return 0;
	return 1;
}
static inline int ui_equal(const struct ui_snapshot *a, const struct ui_snapshot *b)
{
	return ui_raw_equal(a,b) && a->cfg == b->cfg;
}
static inline void ui_terminal(struct ui_state *s, enum ui_phase phase, int error)
{
	s->running = 0; s->phase = phase; s->error = error;
	if (s->op == UI_CLEAR) {
		s->clear_error = error; s->clear_write_return = s->write_return;
	}
}
static inline int ui_start(struct ui_state *s, enum ui_op op, unsigned long long now)
{
	if (s->running) return -EBUSY;
	if (op != UI_CLEAR && op != UI_RESTORE) return -EINVAL;
	if (op == UI_CLEAR && (s->clear_used || s->pending_restore)) return -EALREADY;
	if (op == UI_RESTORE && (!s->pending_restore || !s->old_valid)) return -ENOENT;
	s->op = op; s->phase = UI_WAIT_OFF; s->running = 1;
	s->started_ms = now; s->deadline_ms = now + UI_WAIT_MS;
	s->have_first = 0; s->off_samples = 0;
	s->pre_started_ms = s->prewrite_ms = s->post_ms = 0;
	s->write_attempted = s->write_return = s->readback_error = s->post_error = s->error = 0;
	s->commit_allowed = 0;
	if (op == UI_CLEAR) s->clear_used = 1;
	return 0;
}
static inline int ui_step(struct ui_state *s, const struct ui_ops *io, unsigned long long now)
{
	struct ui_snapshot sample;
	unsigned int cfg = 0, target;
	unsigned long long pre_started, write_now;
	int ret, read_ret;
	if (!s->running) return -EINVAL;
	if (now < s->started_ms || (s->have_first && now < s->first_ms)) {
		ui_terminal(s, UI_ERROR, -EIO); return -EIO;
	}
	if (now >= s->deadline_ms) {
		ui_terminal(s, UI_TIMEOUT, -ETIMEDOUT); return -ETIMEDOUT;
	}
	ret = io->snapshot(io->ctx, &sample);
	if (ret) { ui_terminal(s, UI_ERROR, ret); return ret; }
	if (!ui_off(&sample)) {
		s->have_first = 0; s->off_samples = 0; return -EINPROGRESS;
	}
	if (!s->have_first || !ui_equal(&s->first, &sample)) {
		s->first = sample; s->first_ms = now; s->have_first = 1; s->off_samples = 1;
		return -EINPROGRESS;
	}
	s->off_samples++;
	/* Keep the original first-off anchor across unchanged 250ms ticks. */
	if (now - s->first_ms < UI_STABLE_MS) return -EINPROGRESS;
	pre_started = io->now_ms(io->ctx);
	s->pre_started_ms = pre_started;
	if (pre_started < now) { ui_terminal(s, UI_ERROR, -EIO); return -EIO; }
	ret = io->snapshot(io->ctx, &s->pre);
	if (ret) { ui_terminal(s, UI_ERROR, ret); return ret; }
	if (!ui_off(&s->pre) || !ui_equal(&sample, &s->pre)) {
		s->have_first = 0; s->off_samples = 0; return -EINPROGRESS;
	}
	ret = io->config(io->ctx, &cfg);
	if (ret) { ui_terminal(s, UI_ERROR, ret); return ret; }
	if (cfg != s->pre.cfg) { s->have_first = 0; s->off_samples = 0; return -EINPROGRESS; }
	s->before_cfg = cfg;
	if (s->op == UI_CLEAR) {
		s->saved = s->pre; s->old_valid = 1; s->old_bit = cfg & UI_BIT;
	}
	target = s->op == UI_CLEAR ? 0 : s->old_bit;
	/* Re-read actual BOOTTIME immediately before starting the sole write.
	 * A blocked snapshot/config or scheduling gap cannot reuse old off
	 * evidence past the deadline. A single regmap transfer is not preempted. */
	write_now = io->now_ms(io->ctx);
	s->prewrite_ms = write_now;
	if (write_now < pre_started) { ui_terminal(s, UI_ERROR, -EIO); return -EIO; }
	if (write_now >= s->deadline_ms) { ui_terminal(s, UI_TIMEOUT, -ETIMEDOUT); return -ETIMEDOUT; }
	if (write_now - pre_started > UI_FRESH_MS) { ui_terminal(s, UI_ERROR, -EAGAIN); return -EAGAIN; }
	if ((cfg & UI_BIT) != target) {
		/* A reported regmap error does not prove that no write took effect. */
		s->write_attempted = 1; s->pending_restore = 1;
		s->write_return = io->write_bit(io->ctx, target);
	}
	read_ret = io->config(io->ctx, &s->after_cfg);
	s->readback_error = read_ret;
	if (!read_ret && ((s->after_cfg & UI_BIT) != target ||
		((s->after_cfg ^ s->before_cfg) & ~UI_BIT))) s->readback_error = -EIO;
	s->post_error = io->snapshot(io->ctx, &s->post);
	s->post_ms = io->now_ms(io->ctx);
	if (s->post_ms < write_now && !s->post_error) s->post_error = -EIO;
	if (!s->post_error && (!ui_off(&s->post) || !ui_raw_equal(&s->pre,&s->post) || s->post.cfg != s->after_cfg))
		s->post_error = -EAGAIN;
	s->changed = !read_ret && (s->after_cfg & UI_BIT) != (unsigned int)s->old_bit;
	ret = s->write_return ? s->write_return : s->readback_error ? s->readback_error : s->post_error;
	if (ret) {
		if (s->write_attempted || s->pending_restore) s->unknown_write = 1;
		ui_terminal(s, UI_ERROR, ret); return ret;
	}
	s->unknown_write = 0;
	if (s->op == UI_CLEAR) {
		s->commit_allowed = 1;
		ui_terminal(s, UI_CLEAR_VERIFIED, 0);
	} else {
		s->pending_restore = 0; s->changed = 0;
		ui_terminal(s, UI_RESTORED, 0);
	}
	return 0;
}
static inline int ui_commit(struct ui_state *s)
{
	if (s->running || s->phase != UI_CLEAR_VERIFIED || !s->commit_allowed ||
	    s->unknown_write || s->error || s->write_return || s->readback_error || s->post_error)
		return -EPERM;
	s->pending_restore = 0; s->commit_allowed = 0; s->committed = 1; s->phase = UI_COMMITTED;
	return 0;
}
#endif
