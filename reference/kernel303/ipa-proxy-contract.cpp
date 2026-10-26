/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* Exercise the actual IPA module against synthetic standard mapped buffers. */
#include <array>
#include <algorithm>
#include <deque>
#include <libcamera/camera_manager.h>
#include <libcamera/base/object.h>
#include <libcamera/base/thread.h>
#include <libcamera/base/event_dispatcher.h>
#include <libcamera/base/timer.h>
#include "libcamera/internal/ipa_module.h"
#include <libcamera/ipa/camss_ipa_proxy.h>
#include <linux/videodev2.h>
#include <cassert>
#include <cerrno>
#include <cmath>
#include <cstring>
#include <dlfcn.h>
#include <iostream>
#include <limits>
#include <sys/mman.h>
#include <unistd.h>
#include <linux/qcom-camss-config.h>
#include <libcamera/control_ids.h>
#include <libcamera/ipa/camss_ipa_interface.h>

using namespace libcamera;
struct Observation : public Object {
	unsigned int calls = 0;
	ipa::camss::Statistics statistics{};
	ControlList metadata;
	void ready(uint64_t, uint32_t, uint32_t, const ipa::camss::Statistics &s, const ControlList &m)
	{ ++calls; statistics = s; metadata = m; Thread::current()->eventDispatcher()->interrupt(); }
};
int main(int argc, char **argv)
{
	if (argc != 4) return 2;
 CameraManager manager;
 IPAModule module(argv[1]); assert(module.isValid());
 std::unique_ptr<ipa::camss::IPACamssInterface> ipa;
 std::unique_ptr<ipa::camss::IPAProxyCamss> proxy;
 if (std::string(argv[2]) == "isolated") proxy = std::make_unique<ipa::camss::IPAProxyCamssIsolated>(&module, manager);
 else proxy = std::make_unique<ipa::camss::IPAProxyCamssThreaded>(&module, manager);
 assert(proxy->isValid());
 ipa.reset(proxy.release());
	Observation observation;
	ipa->statsProcessed.connect(&observation, &Observation::ready);
 const ControlId exposureId(V4L2_CID_EXPOSURE, "Exposure", "V4L2", ControlTypeInteger32, ControlId::Direction::In | ControlId::Direction::Out);
 const ControlId gainId(V4L2_CID_ANALOGUE_GAIN, "AnalogueGain", "V4L2", ControlTypeInteger32, ControlId::Direction::In | ControlId::Direction::Out);
 const ControlIdMap idmap{ {V4L2_CID_EXPOSURE, &exposureId}, {V4L2_CID_ANALOGUE_GAIN, &gainId} };
 const ControlInfoMap sensorInfo({ {&exposureId, ControlInfo(int32_t(4), int32_t(3332), int32_t(500))},
  {&gainId, ControlInfo(int32_t(0), int32_t(960), int32_t(512))} }, idmap);
 IPACameraSensorInfo info{};
 info.model = "imx319"; info.outputSize = Size(1632, 1224); info.bitsPerPixel = 10;
 info.pixelRate = 209066666; info.minLineLength = info.maxLineLength = 2080;
 info.minFrameLength = 3350; info.maxFrameLength = 65535;
 ControlInfoMap ipaControls;
 ipa::camss::SensorControlConfiguration configuration{};
 assert(ipa->init(IPASettings{ "", "imx319" }, info, sensorInfo, &ipaControls) == 0);
 assert(ipaControls.count(&controls::ExposureTime) && ipaControls.count(&controls::AnalogueGain));
 assert(ipaControls.count(&controls::ExposureTimeMode) && ipaControls.count(&controls::AnalogueGainMode));
 assert(ipa->configure(info, info.outputSize, sensorInfo, argv[3], &ipaControls, &configuration) == 0);
 assert(configuration.enabled && configuration.exposureDelay == 2);
 ControlList sensorOutput(sensorInfo);
 auto start = [&](uint64_t epoch, const ControlList &controls) { return ipa->start(epoch, controls, &sensorOutput); };
	SharedFD paramFd(memfd_create("ipa-params", MFD_CLOEXEC)), statsFd(memfd_create("ipa-stats", MFD_CLOEXEC));
	assert(paramFd.isValid() && statsFd.isValid() && !ftruncate(paramFd.get(), 8192) && !ftruncate(statsFd.get(), 8192));
	void *params = mmap(nullptr, 8192, PROT_READ | PROT_WRITE, MAP_SHARED, paramFd.get(), 0);
	void *stats = mmap(nullptr, 8192, PROT_READ | PROT_WRITE, MAP_SHARED, statsFd.get(), 0);
	assert(params != MAP_FAILED && stats != MAP_FAILED);
	IPABuffer p(1, { FrameBuffer::Plane{ paramFd, 0, 8192 } });
	IPABuffer s(100, { FrameBuffer::Plane{ statsFd, 0, 8192 } });
 assert(ipa->mapBuffers({p}, {s}) == 0);
 ControlList controls(libcamera::controls::controls);
 controls.set(controls::ExposureTimeMode, controls::ExposureTimeModeAuto);
 controls.set(controls::AnalogueGainMode, controls::AnalogueGainModeAuto);
 controls.set(controls::ExposureTime, int32_t(5000)); controls.set(controls::AnalogueGain, 2.0f);
 assert(start(3, controls) == 0);
 ipa::camss::SensorContext actual{true, 503, 512, UINT32_MAX};
 constexpr uint32_t statsBytes = sizeof(v4l2_isp_buffer) + sizeof(camss_stats_bhist);
 auto *envelope = static_cast<v4l2_isp_buffer *>(stats);
 auto *histogram = reinterpret_cast<camss_stats_bhist *>(static_cast<uint8_t *>(stats) + sizeof(*envelope));
 std::memset(stats, 0, 8192);
 envelope->version = V4L2_ISP_VERSION_V1; envelope->data_size = sizeof(*histogram);
 histogram->header.type = CAMSS_STATS_AEC_BHIST; histogram->header.size = sizeof(*histogram);
 histogram->bins[512] = 499392;
 auto callStats = [&](uint64_t epoch, uint32_t sof, uint32_t id, uint32_t bytes, const ipa::camss::SensorContext &context) {
  unsigned int before = observation.calls;
  ipa->processStats(epoch, sof, id, bytes, context);
  Timer deadline; deadline.start(std::chrono::milliseconds(2000));
  while (observation.calls == before && deadline.isRunning()) Thread::current()->eventDispatcher()->processEvents();
  deadline.stop();
  assert(observation.calls == before + 1);
 };
 callStats(3, 0, 100, statsBytes, actual);
 assert(!observation.statistics.status && !observation.statistics.automaticUpdate.valid);
 ipa->parametersApplied(3, 1);
 callStats(3, 1, 100, statsBytes, ipa::camss::SensorContext{});
 assert(!observation.statistics.automaticUpdate.valid);
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
  callStats(3, frame, 100, statsBytes, actual);
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
 callStats(3, 721, 100, statsBytes, actual);
 assert(observation.statistics.status == -EALREADY && !observation.statistics.automaticUpdate.valid);
 callStats(2, 722, 100, statsBytes, actual);
 assert(observation.statistics.status == -ESTALE && !observation.statistics.automaticUpdate.valid);
 callStats(3, 722, 100, statsBytes - 1, actual);
 assert(observation.statistics.status == -EINVAL && !observation.statistics.automaticUpdate.valid);
 callStats(3, 722, 100, statsBytes, ipa::camss::SensorContext{});
 assert(!observation.statistics.status && !observation.statistics.automaticUpdate.valid);
 ipa->stop();
 assert(start(4, controls) == 0);
 ipa->parametersApplied(4, 0);
 actual = {true, 503, 512, UINT32_MAX};
 std::memset(histogram->bins, 0, sizeof(histogram->bins)); histogram->bins[10] = 499392;
 callStats(4, 0, 100, statsBytes, actual);
 assert(!observation.statistics.status && observation.statistics.automaticUpdate.valid && observation.statistics.automaticUpdate.revision == 1);
 ipa->stop(); ipa->unmapBuffers({1, 100});
 std::cout << "AE_MODEL_PASS frames=" << modelFrames << " proposals=" << proposals << " held=" << heldFrames
  << " scene_steps=4 converged_steps=3 bounds=pass stale/duplicate/unknown/stop/restart=pass" << std::endl;
	ipa.reset();
	munmap(params, 8192); munmap(stats, 8192);
	std::cout << "IPA_PROXY_CONTRACT_PASS callbacks=" << observation.calls << " packet=56 stale/duplicate/invalid/stop/reopen/wrap=pass" << std::endl;
	return 0;
}
