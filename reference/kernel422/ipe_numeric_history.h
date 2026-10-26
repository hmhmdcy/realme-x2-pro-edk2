/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once
#include <cerrno>
#include <cstdint>
#include <limits>
#include <optional>

namespace libcamera::ipa::camss {
/* Numerical state is deliberately independent from the observation ledger.
 * Only one uncommitted calculation is allowed per camera. Other requests may
 * reuse a committed program, but may never compute from an unacknowledged
 * proposal or pretend that reuse advances algorithm history. */
template<class State> class IpeNumericHistory {
public:
	struct Proposal { uint64_t epoch, token, baseRevision; uint32_t sof; State next; };
	bool start(uint64_t epoch)
	{
		if (active_ || !epoch || epoch <= epoch_) return false;
		epoch_ = epoch; active_ = true; revision_ = 0; state_ = {}; lastSof_.reset(); pending_.reset();
		return true;
	}
	void stop() { pending_.reset(); active_ = false; }
	int prepare(uint64_t epoch, uint32_t sof, uint64_t token, uint64_t baseRevision, const State &next)
	{
		if (!active_ || epoch != epoch_) return -ESTALE;
		if (pending_) return -EBUSY;
		if (!token || token <= lastToken_ || (lastSof_ && sof <= *lastSof_)) return -EALREADY;
		if (baseRevision != revision_) return -ESTALE;
		if (revision_ == std::numeric_limits<uint64_t>::max()) return -EOVERFLOW;
		pending_ = Proposal{ epoch, token, baseRevision, sof, next };
		lastToken_ = token; lastSof_ = sof; return 0;
	}
	int resolve(uint64_t epoch, uint32_t sof, uint64_t token, bool success)
	{
		if (!active_ || epoch != epoch_) return -ESTALE;
		if (!pending_ || token != pending_->token) return -ENOENT;
		if (sof != pending_->sof || pending_->baseRevision != revision_) return -ESTALE;
		if (success) { state_ = pending_->next; ++revision_; }
		pending_.reset(); return success ? 1 : 0;
	}
	bool busy() const { return pending_.has_value(); }
	uint64_t revision() const { return revision_; }
	const State &state() const { return state_; }
	const std::optional<Proposal> &pending() const { return pending_; }
private:
	bool active_ = false;
	uint64_t epoch_ = 0, revision_ = 0, lastToken_ = 0;
	std::optional<uint32_t> lastSof_;
	State state_{};
	std::optional<Proposal> pending_;
};
} /* namespace libcamera::ipa::camss */
