/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "hardware_agc.h"
#include <algorithm>
#include <cerrno>
#include <chrono>
#include <cmath>
#include <libcamera/control_ids.h>
#include "../libipa/camera_sensor_helper.h"

namespace libcamera::ipa::camss {

int HardwareAgc::initialise(const ValueNode &tuning, double lineUs, int32_t minLines,
 int32_t maxLines, double minGain, double maxGain, const CameraSensorHelper *helper)
{
 if (!tuning.isDictionary() || !helper || !std::isfinite(lineUs) || lineUs <= 0 ||
     minLines <= 0 || maxLines < minLines || !std::isfinite(minGain) || !std::isfinite(maxGain) ||
     minGain <= 0 || maxGain < minGain) return -EINVAL;
 /* Require explicit policy. It is experimental tuning, not factory calibration. */
 auto target = tuning["relativeLuminanceTarget"].get<double>();
 if (!target || !std::isfinite(*target) || *target <= 0 || *target > .95 ||
     !tuning["AeConstraintMode"].isDictionary() || !tuning["AeExposureMode"].isDictionary()) return -EINVAL;
 const auto &constraints = tuning["AeConstraintMode"]["ConstraintNormal"];
 const auto &exposure = tuning["AeExposureMode"]["ExposureNormal"];
 if (tuning["AeConstraintMode"].size() != 1 || tuning["AeExposureMode"].size() != 1 ||
     !constraints.isDictionary() || !constraints.size() || !exposure.isDictionary()) return -EINVAL;
 for (const auto &[name, bound] : constraints.asDict()) {
  auto lo = bound["qLo"].get<double>(), hi = bound["qHi"].get<double>(), y = bound["yTarget"].get<double>();
  if ((name != "lower" && name != "upper") || !lo || !hi || !y ||
      !std::isfinite(*lo) || !std::isfinite(*hi) || !std::isfinite(*y) ||
      *lo < 0 || *hi > 1 || *lo >= *hi || *y <= 0 || *y > .95) return -EINVAL;
 }
 auto times = exposure["exposureTime"].get<std::vector<uint32_t>>();
 auto gains = exposure["gain"].get<std::vector<double>>();
 if (!times || !gains || times->empty() || times->size() != gains->size()) return -EINVAL;
 for (size_t i = 0; i < times->size(); ++i)
  if (!(*times)[i] || !std::isfinite((*gains)[i]) || (*gains)[i] <= 0 ||
      (i && ((*times)[i] < (*times)[i - 1] || (*gains)[i] < (*gains)[i - 1]))) return -EINVAL;
 int ret = parseTuningData(tuning);
 if (ret) return ret;
 if (constraintModes().size() != 1 || !constraintModes().count(controls::ConstraintNormal) ||
     exposureModeHelpers().size() != 1 || !exposureModeHelpers().count(controls::ExposureNormal)) return -ENOTSUP;
 lineUs_ = lineUs; minLines_ = minLines; maxLines_ = maxLines;
 minGain_ = minGain; maxGain_ = maxGain; helper_ = helper;
 configure(std::chrono::duration<double, std::micro>(lineUs), helper);
 setLimits(std::chrono::duration<double, std::micro>(minLines * lineUs),
           std::chrono::duration<double, std::micro>(maxLines * lineUs), minGain, maxGain, {});
 resetFrameCount();
 return 0;
}

double HardwareAgc::estimateLuminance(double gain) const
{
 double weighted = 0;
 /* Bin centres avoid a zero estimate for a nonempty first bin. */
 for (unsigned int i = 0; i < bins_.size(); ++i)
  weighted += bins_[i] * std::min(1.0, (i + .5) / bins_.size() * gain);
 return weighted / population_;
}

int HardwareAgc::calculate(Span<const uint32_t> bins, uint32_t exposureLines, uint32_t gainCode,
 uint32_t *nextLines, uint32_t *nextCode)
{
 if (!helper_ || !nextLines || !nextCode || bins.size() != bins_.size() ||
     exposureLines < uint32_t(minLines_) || exposureLines > uint32_t(maxLines_)) return -EINVAL;
 double actualGain = helper_->gain(gainCode);
 if (!std::isfinite(actualGain) || actualGain < minGain_ || actualGain > maxGain_) return -ERANGE;
 population_ = 0;
 std::copy(bins.begin(), bins.end(), bins_.begin());
 for (uint32_t count : bins_) population_ += count;
 if (!population_) return -ENODATA;
 Histogram histogram(bins);
 const auto [time, gain, quantization, digital] = calculateNewEv(controls::ConstraintNormal, controls::ExposureNormal,
  histogram, std::chrono::duration<double, std::micro>(exposureLines * lineUs_ * actualGain));
 (void)quantization; (void)digital;
 double timeUs = std::chrono::duration<double, std::micro>(time).count();
 if (!std::isfinite(timeUs) || !std::isfinite(gain) || timeUs <= 0 || gain <= 0) return -ERANGE;
 const uint32_t lines = std::clamp<int64_t>(std::llround(timeUs / lineUs_), minLines_, maxLines_);
 const uint32_t code = helper_->gainCode(std::clamp(gain, minGain_, maxGain_));
 const double quantizedGain = helper_->gain(code);
 if (!std::isfinite(quantizedGain) || quantizedGain < minGain_ || quantizedGain > maxGain_) return -ERANGE;
 *nextLines = lines; *nextCode = code;
 return 0;
}
}
