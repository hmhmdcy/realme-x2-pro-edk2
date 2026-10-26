/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* Bounded contrast AF search, independent of sensor, lens and statistics ABI. */
#pragma once

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
#include <optional>
#include <vector>

namespace libcamera::ipa {

class ContrastAf
{
public:
	enum class State { Idle, Scanning, Focused, Failed };
	struct Config {
		int32_t minimum;
		int32_t maximum;
		int32_t coarseStep;
		int32_t fineStep;
		unsigned int samples;
		uint64_t settleNs;
		uint64_t timeoutNs;
		int32_t minimumPeak;
		double peakRatio;
		double verifyRatio;
	};
	struct Move { uint32_t serial; int32_t position; };

	bool configure(const Config &config)
	{
		cancel();
		int64_t extent = int64_t(config.maximum) - config.minimum;
		if (config.minimum < 0 || extent <= 0 || config.coarseStep <= 0 ||
		    config.fineStep <= 0 || config.fineStep > config.coarseStep ||
		    extent / config.coarseStep > 126 ||
		    (int64_t(config.coarseStep) * 2) / config.fineStep > 126 ||
		    !config.samples || config.samples > 9 || config.minimumPeak < 0 ||
		    config.settleNs > 5000000000ULL || config.timeoutNs <= config.settleNs ||
		    config.timeoutNs > 600000000000ULL ||
		    !std::isfinite(config.peakRatio) || config.peakRatio <= 1 ||
		    !std::isfinite(config.verifyRatio) || config.verifyRatio <= 0 || config.verifyRatio > 1)
			return configured_ = false;
		config_ = config;
		return configured_ = true;
	}

	void trigger(uint64_t now)
	{
		if (!configured_ || state_ == State::Scanning)
			return;
		if (!now || now > std::numeric_limits<uint64_t>::max() - config_.timeoutNs) {
			state_ = State::Failed;
			return;
		}
		state_ = State::Scanning;
		phase_ = Phase::Coarse;
		deadline_ = now + config_.timeoutNs;
		coarseMinimum_ = std::numeric_limits<int32_t>::max();
		bestScore_ = -1;
		bestPosition_ = config_.minimum;
		lastSample_ = 0;
		makePoints(config_.minimum, config_.maximum, config_.coarseStep);
	}

	void cancel()
	{
		state_ = State::Idle;
		awaiting_ = false;
		needMove_ = false;
		points_.clear();
		scores_.clear();
	}
	void cancelScan()
	{
		if (state_ == State::Scanning)
			cancel();
	}

	State state() const { return state_; }
	std::optional<int32_t> selectedPosition() const
	{
		return state_ == State::Focused ? std::optional<int32_t>(bestPosition_) : std::nullopt;
	}

	std::optional<Move> takeMove(uint64_t now)
	{
		if (state_ != State::Scanning || !needMove_)
			return std::nullopt;
		if (!now || now > deadline_ || serial_ == std::numeric_limits<uint32_t>::max()) {
			fail();
			return std::nullopt;
		}
		needMove_ = false;
		awaiting_ = true;
		issued_ = now;
		return Move{ ++serial_, points_[point_] };
	}

	void applied(uint32_t serial, int status, uint64_t timestamp)
	{
		if (state_ != State::Scanning || !awaiting_ || serial != serial_)
			return;
		awaiting_ = false;
		if (status || !timestamp || timestamp < issued_ ||
		    timestamp > std::numeric_limits<uint64_t>::max() - config_.settleNs) {
			fail();
			return;
		}
		settled_ = timestamp + config_.settleNs;
	}

	/* All timestamps use CLOCK_MONOTONIC; guard includes exposure and readout. */
	void process(bool valid, int32_t score, uint64_t captured,
		     uint64_t guard, uint64_t now)
	{
		if (state_ != State::Scanning)
			return;
		if (!now || !captured || captured > now || now > deadline_) {
			fail();
			return;
		}
		if (awaiting_ || needMove_ || !valid || score < 0 ||
		    guard > std::numeric_limits<uint64_t>::max() - settled_ ||
		    captured <= settled_ + guard || captured <= lastSample_)
			return;
		lastSample_ = captured;
		scores_.push_back(score);
		if (scores_.size() < config_.samples)
			return;
		std::sort(scores_.begin(), scores_.end());
		int32_t median = scores_[scores_.size() / 2];
		scores_.clear();

		if (phase_ == Phase::Verify) {
			state_ = median >= config_.minimumPeak &&
				 median >= bestScore_ * config_.verifyRatio
				 ? State::Focused : State::Failed;
			return;
		}
		if (phase_ == Phase::Coarse)
			coarseMinimum_ = std::min(coarseMinimum_, median);
		if (median > bestScore_) {
			bestScore_ = median;
			bestPosition_ = points_[point_];
		}
		if (++point_ < points_.size()) {
			needMove_ = true;
			return;
		}
		if (phase_ == Phase::Coarse) {
			if (!usefulPeak()) {
				fail();
				return;
			}
			phase_ = Phase::Fine;
			int32_t minimum = std::max<int64_t>(config_.minimum, int64_t(bestPosition_) - config_.coarseStep);
			int32_t maximum = std::min<int64_t>(config_.maximum, int64_t(bestPosition_) + config_.coarseStep);
			bestScore_ = -1;
			makePoints(minimum, maximum, config_.fineStep);
		} else {
			if (!usefulPeak()) {
				fail();
				return;
			}
			phase_ = Phase::Verify;
			points_ = { bestPosition_ };
			point_ = 0;
			needMove_ = true;
		}
	}

private:
	enum class Phase { Coarse, Fine, Verify };
	bool usefulPeak() const
	{
		return bestScore_ >= config_.minimumPeak && bestScore_ > 0 &&
		       bestScore_ >= coarseMinimum_ * config_.peakRatio;
	}
	void makePoints(int32_t minimum, int32_t maximum, int32_t step)
	{
		points_.clear();
		for (int64_t position = minimum; position < maximum; position += step)
			points_.push_back(position);
		points_.push_back(maximum);
		point_ = 0;
		scores_.clear();
		awaiting_ = false;
		needMove_ = true;
	}
	void fail()
	{
		state_ = State::Failed;
		awaiting_ = false;
		needMove_ = false;
	}
	Config config_{};
	bool configured_ = false;
	State state_ = State::Idle;
	Phase phase_ = Phase::Coarse;
	uint32_t serial_ = 0;
	bool awaiting_ = false;
	bool needMove_ = false;
	uint64_t deadline_ = 0, issued_ = 0, settled_ = 0, lastSample_ = 0;
	std::vector<int32_t> points_, scores_;
	size_t point_ = 0;
	int32_t coarseMinimum_ = 0, bestScore_ = 0, bestPosition_ = 0;
};

} /* namespace libcamera::ipa */
