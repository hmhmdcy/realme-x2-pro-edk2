/* SPDX-License-Identifier: LGPL-2.1-or-later */
#pragma once
#include <array>
#include <cerrno>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <map>
#include <optional>

namespace libcamera::ipa::camss {

/* Owned pre-WB linear BHIST and its same-SOF sensor/IFE context. These are
 * observations, not HDR exposure slots or proof of the IPE input transfer. */
struct IpeFrameObservation {
	uint64_t epoch = 0, exposureNs = 0, population = 0;
	uint32_t sof = 0, exposureLines = 0, gainCode = 0, sensorSource = 0, ispRevision = 0;
	float analogueGain = 0, exposureIndex = 0, luxIndex = 0;
	bool luxValid = false, ifeGammaOverride = false;
	std::array<uint32_t, 1024> histogram{};
};

inline uint64_t histogramTrace(const IpeFrameObservation &frame)
{
	uint64_t value = 14695981039346656037ULL;
	for (uint32_t bin : frame.histogram)
		for (unsigned int shift = 0; shift < 32; shift += 8) {
			value ^= (bin >> shift) & 255;
			value *= 1099511628211ULL;
		}
	return value;
}

/* Bounded per-camera transactions. A successful queue/request/DQBUF is not a
 * commit: the pipeline must first finish image processing and RAW pairing.
 * Later successes may supersede older in-flight frames, never reverse history.
 * Numerical algorithm state can be carried with the owned observation later;
 * this class currently commits observations only, not TMC/LTM curves. */
class IpeFrameHistory {
public:
	struct Counters { uint64_t prepared = 0, committed = 0, discarded = 0, superseded = 0, aborted = 0; };
	enum Resolution { Discarded = 0, Committed = 1, Superseded = 2 };
	bool start(uint64_t epoch)
	{
		if (active_ || !epoch || epoch <= epoch_) return false;
		epoch_ = epoch; active_ = true; lastPrepared_.reset(); committed_.reset(); counters_ = {};
		return true;
	}
	void stop()
	{
		counters_.aborted += pending_.size(); pending_.clear(); active_ = false;
	}
	int prepare(const IpeFrameObservation &frame, uint64_t *token)
	{
		if (!token) return -EINVAL;
		if (!active_ || frame.epoch != epoch_) return -ESTALE;
		if (lastPrepared_ && frame.sof <= *lastPrepared_) return -EALREADY;
		uint64_t count = 0;
		for (uint32_t bin : frame.histogram) count += bin;
		if (!frame.exposureNs || !frame.exposureLines || !frame.population || count != frame.population ||
		    !std::isfinite(frame.analogueGain) || frame.analogueGain <= 0 ||
		    (frame.luxValid && (!std::isfinite(frame.exposureIndex) || !std::isfinite(frame.luxIndex)))) return -EINVAL;
		if (pending_.size() >= 64) return -ENOSPC;
		if (serial_ == std::numeric_limits<uint64_t>::max()) return -EOVERFLOW;
		const uint64_t next = serial_ + 1;
		pending_.emplace(next, frame); serial_ = next; lastPrepared_ = frame.sof;
		++counters_.prepared; *token = next;
		return 0;
	}
	int resolve(uint64_t epoch, uint32_t sof, uint64_t token, bool success)
	{
		if (!active_ || epoch != epoch_) return -ESTALE;
		auto it = pending_.find(token);
		if (it == pending_.end()) return -ENOENT;
		if (it->second.sof != sof) return -ESTALE;
		int result;
		if (!success) { ++counters_.discarded; result = Discarded; }
		else if (committed_ && sof <= committed_->sof) { ++counters_.superseded; result = Superseded; }
		else { committed_ = it->second; ++counters_.committed; result = Committed; }
		pending_.erase(it); return result;
	}
	const IpeFrameObservation *pending(uint64_t token) const
	{
		auto it = pending_.find(token); return it == pending_.end() ? nullptr : &it->second;
	}
	const std::optional<IpeFrameObservation> &committed() const { return committed_; }
	const Counters &counters() const { return counters_; }
	size_t pendingCount() const { return pending_.size(); }
private:
	uint64_t epoch_ = 0, serial_ = 0;
	bool active_ = false;
	std::optional<uint32_t> lastPrepared_;
	std::optional<IpeFrameObservation> committed_;
	std::map<uint64_t, IpeFrameObservation> pending_;
	Counters counters_;
};
} /* namespace libcamera::ipa::camss */
