/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* Exercise the actual IPA module against synthetic standard mapped buffers. */
#include <array>
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
struct Observation {
	unsigned int calls = 0;
	ipa::camss::Statistics statistics{};
	ControlList metadata;
	void ready(uint64_t, uint32_t, uint32_t, const ipa::camss::Statistics &s, const ControlList &m)
	{ ++calls; statistics = s; metadata = m; }
};
int main(int argc, char **argv)
{
	if (argc != 3) return 2;
	void *handle = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
	if (!handle) { std::cerr << dlerror() << std::endl; return 3; }
	auto create = reinterpret_cast<IPAInterface *(*)()>(dlsym(handle, "ipaCreate"));
	assert(create);
	std::unique_ptr<ipa::camss::IPACamssInterface> ipa(static_cast<ipa::camss::IPACamssInterface *>(create()));
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
 assert(ipa->configure(info, info.outputSize, sensorInfo, argv[2], &ipaControls, &configuration) == 0);
 assert(configuration.enabled && configuration.exposureDelay == 2 && configuration.gainDelay == 2);
 ++info.pixelRate;
 assert(ipa->configure(info, info.outputSize, sensorInfo, argv[2], &ipaControls, &configuration) == -EINVAL);
 --info.pixelRate;
 assert(ipa->configure(info, info.outputSize, sensorInfo, argv[2], &ipaControls, &configuration) == 0);
 ControlList sensorOutput(sensorInfo);
 auto start = [&](uint64_t epoch, const ControlList &controls) { return ipa->start(epoch, controls, &sensorOutput); };
	SharedFD paramFd(memfd_create("ipa-params", MFD_CLOEXEC)), statsFd(memfd_create("ipa-stats", MFD_CLOEXEC));
	assert(paramFd.isValid() && statsFd.isValid() && !ftruncate(paramFd.get(), 8192) && !ftruncate(statsFd.get(), 8192));
	void *params = mmap(nullptr, 8192, PROT_READ | PROT_WRITE, MAP_SHARED, paramFd.get(), 0);
	void *stats = mmap(nullptr, 8192, PROT_READ | PROT_WRITE, MAP_SHARED, statsFd.get(), 0);
	assert(params != MAP_FAILED && stats != MAP_FAILED);
	IPABuffer p(1, { FrameBuffer::Plane{ paramFd, 0, 8192 } });
	IPABuffer s(100, { FrameBuffer::Plane{ statsFd, 0, 8192 } });
	IPABuffer conflict(1, { FrameBuffer::Plane{ statsFd, 0, 8192 } });
	assert(ipa->mapBuffers({p}, {conflict}) < 0);
	assert(ipa->mapBuffers({p}, {s}) == 0);
	assert(ipa->mapBuffers({p}, {}) < 0);
	ControlList controls(libcamera::controls::controls);
	const std::array<float, 2> gains{ 2, 3 };
	const std::array<float, 2> invalid{ std::numeric_limits<float>::quiet_NaN(), 3 };
	controls.set(controls::ColourGains, Span<const float, 2>(invalid));
	assert(start(1, controls) == -ERANGE);
	controls.set(controls::ColourGains, Span<const float, 2>(gains));
	assert(start(1, controls) == 0);
 ControlList requested(controls::controls), converted(sensorInfo);
 requested.set(controls::ExposureTime, int32_t(5000)); requested.set(controls::AnalogueGain, 4.0f);
 assert(ipa->convertControls(0, requested, &converted) == -ESTALE);
 assert(ipa->convertControls(1, requested, &converted) == 0);
 assert(converted.get(V4L2_CID_EXPOSURE).get<int32_t>() == 503);
 assert(converted.get(V4L2_CID_ANALOGUE_GAIN).get<int32_t>() == 768);
 requested.set(controls::AnalogueGain, std::numeric_limits<float>::infinity());
 assert(ipa->convertControls(1, requested, &converted) == -ERANGE);
 assert(converted.get(V4L2_CID_EXPOSURE).get<int32_t>() == 503 && converted.get(V4L2_CID_ANALOGUE_GAIN).get<int32_t>() == 768);
 requested.set(controls::AnalogueGain, 2.0f); requested.set(controls::ExposureTime, int32_t(0));
 assert(ipa->convertControls(1, requested, &converted) == -ERANGE);
 requested.clear(); requested.set(controls::ExposureTimeMode, controls::ExposureTimeModeAuto);
 assert(ipa->convertControls(1, requested, &converted) == -ENOTSUP);
 requested.set(controls::ExposureTimeMode, controls::ExposureTimeModeManual);
 requested.set(controls::AnalogueGainMode, controls::AnalogueGainModeManual);
 assert(ipa->convertControls(1, requested, &converted) == 0 && converted.empty());

	std::memset(params, 0xa5, 8192);
	uint32_t used = 0;
	assert(ipa->prepareParameters(0, 1, &used) == -ESTALE && !used && static_cast<uint8_t *>(params)[0] == 0xa5);
	assert(ipa->prepareParameters(1, 1, &used) == 0 && used == 56);
	auto *wb = reinterpret_cast<camss_params_wb_gain *>(static_cast<uint8_t *>(params) + 8);
	assert(wb->r_sub == 3840 && wb->g_sub == 3840 && wb->b_sub == 3840);
	assert(wb->g_gain == 1088 && wb->r_gain == 2175 && wb->b_gain == 3263);
	camss_params_wb_gain wantedWb{};
	wantedWb.header = { CAMSS_PARAMS_WB_GAIN, V4L2_ISP_PARAMS_FL_BLOCK_ENABLE, sizeof(wantedWb) };
	wantedWb.r_sub = wantedWb.g_sub = wantedWb.b_sub = 3840;
	wantedWb.r_gain = 2175; wantedWb.g_gain = 1088; wantedWb.b_gain = 3263;
	camss_params_aec_bhist wantedHistogram{};
	wantedHistogram.header = { CAMSS_PARAMS_AEC_BHIST, V4L2_ISP_PARAMS_FL_BLOCK_ENABLE, sizeof(wantedHistogram) };
	wantedHistogram.width = 1632; wantedHistogram.height = 1224;
	const std::array<uint32_t, 2> wantedHeader{ V4L2_ISP_VERSION_V1, sizeof(wantedWb) + sizeof(wantedHistogram) };
	std::array<uint8_t, 56> expected{};
	std::memcpy(expected.data(), wantedHeader.data(), 8);
	std::memcpy(expected.data() + 8, &wantedWb, sizeof(wantedWb));
	std::memcpy(expected.data() + 8 + sizeof(wantedWb), &wantedHistogram, sizeof(wantedHistogram));
	assert(!std::memcmp(params, expected.data(), expected.size()));
	for (unsigned int i = used; i < 8192; ++i) assert(static_cast<uint8_t *>(params)[i] == 0xa5);
	constexpr uint32_t statsBytes = sizeof(v4l2_isp_buffer) + sizeof(camss_stats_bhist);
	auto *envelope = static_cast<v4l2_isp_buffer *>(stats);
	auto *histogram = reinterpret_cast<camss_stats_bhist *>(static_cast<uint8_t *>(stats) + sizeof(*envelope));
	std::memset(stats, 0, 8192);
	envelope->version = V4L2_ISP_VERSION_V1; envelope->data_size = sizeof(*histogram);
	histogram->header.type = CAMSS_STATS_AEC_BHIST; histogram->header.size = sizeof(*histogram);
	histogram->bins[512] = 499392;
	auto process = [&](uint64_t epoch, uint32_t sof, uint32_t id, uint32_t bytes, int status, bool known) {
		unsigned int before = observation.calls;
		ipa->processStats(epoch, sof, id, bytes, ipa::camss::SensorContext{true, 500, 512, 42});
		assert(observation.calls == before + 1 && observation.statistics.status == status);
		if (!status) assert(observation.statistics.parametersKnown == known);
  if (!status) {
   assert(observation.statistics.sensorControlsKnown);
   assert(observation.metadata.get(controls::ExposureTimeMode).value_or(-1) == controls::ExposureTimeModeManual);
   assert(observation.metadata.get(controls::AnalogueGainMode).value_or(-1) == controls::AnalogueGainModeManual);
   assert(observation.metadata.get(controls::ExposureTime).value_or(0) == 4974);
   assert(observation.metadata.get(controls::AnalogueGain).value_or(0) == 2.0f);
  } else {
   assert(!observation.metadata.contains(controls::ExposureTime.id()) && !observation.metadata.contains(controls::AnalogueGain.id()));
  }

		auto colour = observation.metadata.get(controls::ColourGains);
		if (!status && known) assert(colour && (*colour)[0] == 2 && (*colour)[1] == 3);
		else assert(!colour);
	};
	ipa->parametersApplied(1, 20);
	process(1, 19, 100, statsBytes, 0, false);
	process(1, 20, 100, statsBytes, 0, true);
	assert(observation.statistics.population == 499392 && observation.statistics.weightedSum == uint64_t(512) * 499392);
	process(1, 20, 100, statsBytes, -EALREADY, false);
	process(0, 21, 100, statsBytes, -ESTALE, false);
	process(1, 21, 1, statsBytes, -ENOENT, false);
	process(1, 21, 100, statsBytes - 1, -EINVAL, false);
	envelope->version = 99; process(1, 21, 100, statsBytes, -EPROTO, false); envelope->version = V4L2_ISP_VERSION_V1;
	histogram->header.flags = 1; process(1, 21, 100, statsBytes, -EPROTO, false); histogram->header.flags = 0;
	--histogram->bins[512]; process(1, 21, 100, statsBytes, -ENODATA, false); ++histogram->bins[512];
	process(1, 21, 100, statsBytes, 0, true);
	process(1, 18, 100, statsBytes, -ERANGE, false);
 ipa->processStats(1, 22, 100, statsBytes, ipa::camss::SensorContext{});
 assert(!observation.statistics.status && !observation.statistics.sensorControlsKnown);
 assert(!observation.metadata.contains(controls::ExposureTime.id()) && !observation.metadata.contains(controls::AnalogueGain.id()));
 ipa->processStats(1, 23, 100, statsBytes, ipa::camss::SensorContext{true, 500, 2000, 42});
 assert(!observation.statistics.status && !observation.statistics.sensorControlsKnown);
 assert(!observation.metadata.contains(controls::ExposureTime.id()));

	ipa->stop(); process(1, 22, 100, statsBytes, -ESTALE, false);
	ipa->unmapBuffers({ 1, 100 });
	assert(ipa->mapBuffers({p}, {s}) == 0 && start(2, controls) == 0);
	ipa->parametersApplied(2, UINT32_MAX - 1);
	process(2, UINT32_MAX - 1, 100, statsBytes, 0, true);
	process(2, UINT32_MAX, 100, statsBytes, 0, true);
	process(2, 0, 100, statsBytes, 0, true);
	ipa->stop(); ipa->unmapBuffers({1,100});
	ipa.reset(); dlclose(handle);
	munmap(params, 8192); munmap(stats, 8192);
	std::cout << "IPA_CONTRACT_PASS callbacks=" << observation.calls << " packet=56 stale/duplicate/invalid/stop/reopen/wrap=pass" << std::endl;
	return 0;
}
