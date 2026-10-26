"""Extend the existing mapped-buffer module contract with an independent delayed sensor model."""
from pathlib import Path
HERE = Path(__file__).resolve().parent
s = (HERE.parent / 'kernel302/ipa-contract.cpp').read_text()
s = s.replace('#include <array>', '#include <array>\n#include <algorithm>\n#include <deque>')
s = s.replace('if (argc != 3)', 'if (argc != 4)')
anchor = '\tipa.reset(); dlclose(handle);'
assert s.count(anchor) == 1
s = s.replace(anchor, r'''
 // No uncalibrated profile silently enables automatic control.
 controls.set(controls::ExposureTimeMode, controls::ExposureTimeModeAuto);
 controls.set(controls::AnalogueGainMode, controls::AnalogueGainModeAuto);
 assert(start(3, controls) == -ENOTSUP);
 assert(ipa->configure(info, info.outputSize, sensorInfo, argv[3], &ipaControls, &configuration) == 0);
 assert(ipaControls.at(&controls::ExposureTimeMode).values().size() == 2);
 controls.set(controls::ExposureTimeMode, controls::ExposureTimeModeManual);
 assert(start(3, controls) == -ENOTSUP); // Mixed auto/manual is deliberately unsupported.
 controls.set(controls::ExposureTimeMode, controls::ExposureTimeModeAuto);
 controls.set(controls::ExposureTime, int32_t(5000));
 controls.set(controls::AnalogueGain, 2.0f);
 assert(ipa->mapBuffers({p}, {s}) == 0);
 assert(ipa->start(3, controls, nullptr) == -EINVAL);
 assert(start(3, controls) == 0);
 requested.clear(); requested.set(controls::ExposureTime, int32_t(8000));
 assert(ipa->convertControls(3, requested, &converted) == -ENOTSUP);
 ipa::camss::SensorContext actual{true, 503, 512, UINT32_MAX};
 ipa->processStats(3, 0, 100, statsBytes, actual);
 assert(!observation.statistics.status && !observation.statistics.automaticUpdate.valid);
 ipa->parametersApplied(3, 1);
 ipa->processStats(3, 1, 100, statsBytes, ipa::camss::SensorContext{});
 assert(!observation.statistics.automaticUpdate.valid && !observation.statistics.sensorControlsKnown);
 unsigned int proposals = 0, modelFrames = 0, heldFrames = 0;
 const double lineUs = 2080.0 * 1000000 / 209066666;
 struct Pending { unsigned int due; ipa::camss::AutoSensorUpdate update; };
 std::deque<Pending> pending;
 std::array<double, 4> scenes{.25, 4.0, 1.0, .01};
 for (unsigned int frame = 2; frame < 722; ++frame) {
  if (!pending.empty() && pending.front().due == frame) {
   auto update = pending.front().update; pending.pop_front();
   actual = {true, update.exposureLines, update.gainCode, update.revision};
  }
  double gain = 1024.0 / (1024 - actual.gainCode);
  double relative = std::clamp(.16 * scenes[(frame - 2) / 180] * actual.exposureLines * lineUs * gain / 20000, 0.0, 1.0);
  unsigned int bin = std::clamp<int>(std::lround(relative * CAMSS_STATS_BHIST_BINS - .5), 0, CAMSS_STATS_BHIST_BINS - 1);
  std::memset(histogram->bins, 0, sizeof(histogram->bins)); histogram->bins[bin] = 499392;
  ipa->processStats(3, frame, 100, statsBytes, actual);
  assert(observation.statistics.status == 0 && observation.statistics.sensorControlsKnown);
  assert(observation.metadata.get(controls::ExposureTimeMode).value_or(-1) == controls::ExposureTimeModeAuto);
  assert(observation.metadata.get(controls::AnalogueGainMode).value_or(-1) == controls::AnalogueGainModeAuto);
  assert(observation.metadata.get(controls::ExposureTime).value_or(0) == std::lround(actual.exposureLines * lineUs));
  assert(std::abs(observation.metadata.get(controls::AnalogueGain).value_or(0) - gain) < .00001);
  const auto update = observation.statistics.automaticUpdate;
  if (!pending.empty()) { ++heldFrames; assert(!update.valid); }
  if (update.valid) {
   assert(pending.empty() && update.revision == ++proposals);
   assert(update.exposureLines >= 4 && update.exposureLines <= 3332 && update.gainCode <= 960);
   pending.push_back({frame + 3, update}); // Independent three-frame sensor/IPC delay.
  }
  if ((frame - 2) % 180 >= 160 && (frame - 2) / 180 < 3) assert(std::abs(relative - .16) < .012);
  if (frame >= 702) assert(actual.exposureLines >= 3300 && actual.gainCode >= 959); // Unreachable dark target saturates safely.
  ++modelFrames;
 }
 // Stale, duplicate, malformed and missing context never create control proposals.
 ipa->processStats(3, 721, 100, statsBytes, actual);
 assert(observation.statistics.status == -EALREADY && !observation.statistics.automaticUpdate.valid);
 ipa->processStats(2, 722, 100, statsBytes, actual);
 assert(observation.statistics.status == -ESTALE && !observation.statistics.automaticUpdate.valid);
 ipa->processStats(3, 722, 100, statsBytes - 1, actual);
 assert(observation.statistics.status == -EINVAL && !observation.statistics.automaticUpdate.valid);
 ipa->processStats(3, 722, 100, statsBytes, ipa::camss::SensorContext{});
 assert(!observation.statistics.status && !observation.statistics.automaticUpdate.valid);
 ipa->stop();
 ipa->processStats(3, 723, 100, statsBytes, actual);
 assert(observation.statistics.status == -ESTALE && !observation.statistics.automaticUpdate.valid);
 assert(start(4, controls) == 0);
 ipa->parametersApplied(4, 0);
 actual = {true, 503, 512, UINT32_MAX};
 std::memset(histogram->bins, 0, sizeof(histogram->bins)); histogram->bins[10] = 499392;
 ipa->processStats(4, 0, 100, statsBytes, actual);
 assert(!observation.statistics.status && observation.statistics.automaticUpdate.valid && observation.statistics.automaticUpdate.revision == 1);
 ipa->stop(); ipa->unmapBuffers({1, 100});
 std::cout << "AE_MODEL_PASS frames=" << modelFrames << " proposals=" << proposals << " held=" << heldFrames
  << " scene_steps=4 converged_steps=3 bounds=pass stale/duplicate/unknown/stop/restart=pass" << std::endl;
''' + anchor)
(HERE / 'ipa-contract.cpp').write_text(s)
print('Prepared real-module contract and independent delay model')
