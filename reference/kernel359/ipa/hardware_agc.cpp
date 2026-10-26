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
 int32_t maxLines, double minGain, double maxGain, const CameraSensorHelper *helper,
 const ValueNode &program, uint64_t frameNs, uint32_t minimumGainCode, uint32_t maximumGainCode)
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
 if (maximumGainCode < minimumGainCode) return -ERANGE;
 int profileStatus = ExposureProgram::configure(program, std::llround(minLines * lineUs * 1000),
  std::llround(maxLines * lineUs * 1000), frameNs, minGain, &program_);
 if (profileStatus) return profileStatus;
 lineUs_ = lineUs; minLines_ = minLines; maxLines_ = maxLines;
 minGain_ = minGain; maxGain_ = maxGain; helper_ = helper;
 minimumGainCode_ = minimumGainCode; maximumGainCode_ = maximumGainCode;
 configure(std::chrono::duration<double, std::micro>(lineUs), helper);
 setLimits(std::chrono::duration<double, std::micro>(minLines * lineUs),
           std::chrono::duration<double, std::micro>(maxLines * lineUs), minGain, maxGain, {});
 return resetControls();
}

bool HardwareAgc::algorithmControl(unsigned int id)
{
 return id == controls::ExposureValue.id() || id == controls::AeFlickerMode.id() ||
        id == controls::AeFlickerPeriod.id();
}

int HardwareAgc::validateControls(const ControlList &values) const
{
 for (const auto &[id, value] : values) {
  if (!algorithmControl(id)) continue;
  if (id == controls::ExposureValue.id()) {
   if (value.type() != ControlTypeFloat || value.isArray()) return -EINVAL;
   float ev = value.get<float>();
   if (!std::isfinite(ev) || ev < -8 || ev > 8) return -ERANGE;
  } else {
   if (!program_) return -ENOTSUP;
   if (value.type() != ControlTypeInteger32 || value.isArray()) return -EINVAL;
   int32_t requested = value.get<int32_t>();
   if (id == controls::AeFlickerMode.id() && requested != controls::FlickerOff &&
       requested != controls::FlickerManual) return -ENOTSUP;
   if (id == controls::AeFlickerPeriod.id() && requested < 0) return -ERANGE;
  }
 }
 return 0;
}

int HardwareAgc::applyControls(const ControlList &values, uint32_t firstSof)
{
 int ret = validateControls(values);
 if (ret) return ret;
 bool change = false;
 for (const auto &[id,value] : values) change |= algorithmControl(id);
 if (change && !history_.empty() && firstSof < history_.rbegin()->first) return -ESTALE;
 float ev = values.get(controls::ExposureValue).value_or(evStops_);
 auto program = program_;
 if (program && ev != evStops_ && !program->adjust(ev)) return -ERANGE;
 program_ = std::move(program); evStops_ = ev;
 flickerMode_ = values.get(controls::AeFlickerMode).value_or(flickerMode_);
 flickerPeriodUs_ = values.get(controls::AeFlickerPeriod).value_or(flickerPeriodUs_);
 setExposureCompensation(std::exp2(double(ev)));
 if (change) {
  history_[firstSof] = { evStops_, flickerMode_, flickerPeriodUs_ };
  while (history_.size() > 64) history_.erase(history_.begin());
 }
 return 0;
}

int HardwareAgc::resetControls()
{
 if (program_ && !program_->adjust(0)) return -ERANGE;
 evStops_ = 0; flickerMode_ = controls::FlickerOff; flickerPeriodUs_ = 0;
 history_.clear(); history_[0] = { evStops_, flickerMode_, flickerPeriodUs_ };
 setExposureCompensation(1); resetFrameCount();
 return 0;
}

void HardwareAgc::metadata(uint32_t sof, ControlList *values) const
{
 auto state = history_.upper_bound(sof);
 if (state == history_.begin()) return;
 --state;
 values->set(controls::ExposureValue, state->second.ev);
 if (program_) {
  values->set(controls::AeFlickerMode, state->second.mode);
  values->set(controls::AeFlickerPeriod, state->second.periodUs);
 }
}

double HardwareAgc::estimateLuminance(double gain) const
{
 double weighted = 0;
 /* Bin centres avoid a zero estimate for a nonempty first bin. */
 for (unsigned int i = 0; i < bins_.size(); ++i)
  weighted += bins_[i] * std::min(1.0, (i + .5) / bins_.size() * gain);
 return weighted / population_;
}

int HardwareAgc::calculate(uint32_t sof, Span<const uint32_t> bins, uint32_t exposureLines, uint32_t gainCode,
 uint32_t *nextLines, uint32_t *nextCode)
{
 if (!helper_ || !nextLines || !nextCode || bins.size() != bins_.size() ||
     exposureLines < uint32_t(minLines_) || exposureLines > uint32_t(maxLines_)) return -EINVAL;
 double actualGain = helper_->gain(gainCode);
 if (!std::isfinite(actualGain) || actualGain < minGain_ || actualGain > maxGain_) return -ERANGE;
 auto state = history_.upper_bound(sof);
 if (state == history_.begin()) return -ENODATA;
 --state;
 const ExposureProgram *program = program_ ? &*program_ : nullptr;
 std::optional<ExposureProgram> historicalProgram;
 if (program && state->second.ev != evStops_) {
  historicalProgram = *program;
  if (!historicalProgram->adjust(state->second.ev)) return -ERANGE;
  program = &*historicalProgram;
 }
 setExposureCompensation(std::exp2(double(state->second.ev)));
 population_ = 0;
 std::copy(bins.begin(), bins.end(), bins_.begin());
 for (uint32_t count : bins_) population_ += count;
 if (!population_) return -ENODATA;
 Histogram histogram(bins);
 const auto current = std::chrono::duration<double, std::micro>(exposureLines * lineUs_ * actualGain);
 auto allocation = [&]() {
  if (!program) return calculateNewEv(controls::ConstraintNormal, controls::ExposureNormal, histogram, current);
  auto target = calculateNewExposureValue(controls::ConstraintNormal, histogram, current);
  AecExposureAllocation selected;
  uint64_t period = state->second.mode == controls::FlickerManual ? uint64_t(state->second.periodUs) * 1000 : 0;
  if (!program->allocate(std::chrono::duration<double, std::nano>(target).count(), period, &selected))
   return std::tuple<utils::Duration, double, double, double>{ {}, 0, 0, 0 };
  /* The common helper performs the final real line/gain quantization and
   * range enforcement. A factory knee is not a sensor gain limit. */
  std::array<std::pair<utils::Duration, double>, 1> stage{{
   { std::chrono::duration<double, std::nano>(selected.exposureTimeNs), selected.gain }
  }};
  ExposureModeHelper quantizer(stage);
  quantizer.configure(std::chrono::duration<double, std::micro>(lineUs_), helper_);
  quantizer.setLimits(std::chrono::duration<double, std::micro>(minLines_ * lineUs_),
   std::chrono::duration<double, std::micro>(maxLines_ * lineUs_), minGain_, maxGain_);
  return quantizer.splitExposure(std::chrono::duration<double, std::nano>(
   double(selected.exposureTimeNs) * selected.gain));
 };
 const auto [time, gain, quantization, digital] = allocation();
 (void)quantization; (void)digital;
 double timeUs = std::chrono::duration<double, std::micro>(time).count();
 if (!std::isfinite(timeUs) || !std::isfinite(gain) || timeUs <= 0 || gain <= 0) return -ERANGE;
 const uint32_t lines = std::clamp<int64_t>(std::llround(timeUs / lineUs_), minLines_, maxLines_);
 const uint32_t code = std::clamp(helper_->gainCode(std::clamp(gain, minGain_, maxGain_)),
  minimumGainCode_, maximumGainCode_);
 const double quantizedGain = helper_->gain(code);
 if (!std::isfinite(quantizedGain) || quantizedGain < minGain_ || quantizedGain > maxGain_) return -ERANGE;
 *nextLines = lines; *nextCode = code;
 return 0;
}
}
