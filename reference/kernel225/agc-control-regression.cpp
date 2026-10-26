/* Behavioral regression for the real software IPA algorithm, without a camera. */
#include <cmath>
#include <iostream>
#include <stdexcept>

#include <linux/v4l2-controls.h>
#include <libcamera/control_ids.h>
#include <libcamera/controls.h>

#include "src/ipa/simple/algorithms/agc.h"

using namespace libcamera;
using namespace libcamera::ipa::soft;
using namespace std::literals::chrono_literals;

static unsigned int checks;
static void require(bool value, const char *message)
{
	++checks;
	if (!value)
		throw std::runtime_error(message);
}

int main()
{
	try {
		Control<int32_t> exposureId(V4L2_CID_EXPOSURE, "Exposure", "v4l2", ControlId::Direction::In);
		ControlIdMap sensorIds{ { V4L2_CID_EXPOSURE, &exposureId } };
		ControlInfoMap sensorMap({ { &exposureId, ControlInfo(1, 1000, 400) } }, sensorIds);
		IPAConfigInfo config;
		config.sensorControls = sensorMap;
		IPAContext context(16);
		context.configuration.agc.exposureMin = 1;
		context.configuration.agc.exposureMax = 1000;
		context.configuration.agc.againMin = context.configuration.agc.again10 = 1;
		context.configuration.agc.againMax = 8;
		context.configuration.agc.againMinStep = 0.01;
		context.configuration.agc.lineDuration = 10us;
		algorithms::Agc agc;
		require(agc.configure(context, config) == 0, "configuration");
		uint32_t sequence = 0;
		auto queued = [&](const ControlList &controls) {
			IPAFrameContext frame{};
			agc.queueRequest(context, sequence++, frame, controls);
			return frame;
		};
		auto prepared = [&](const ControlList &controls) {
			auto frame = queued(controls);
			agc.prepare(context, 0, frame, nullptr);
			return frame;
		};
		auto process = [&](IPAFrameContext &frame, uint32_t source, int32_t exposure,
				   double gain, bool valid = true) {
			frame.sensor.source = source;
			frame.sensor.exposure = exposure;
			frame.sensor.gain = gain;
			SwIspStats stats{};
			stats.valid = valid;
			stats.yHistogram[0] = 100;
			ControlList metadata(controls::controls);
			agc.process(context, 0, frame, &stats, metadata);
			require(metadata.get(controls::ExposureTime).value_or(-1) == exposure * 10,
				"metadata must describe captured exposure");
			require(std::abs(metadata.get(controls::AnalogueGain).value_or(-1) - gain) < 1e-5,
				"metadata must describe captured gain");
			require(metadata.get(controls::ExposureTimeMode).value_or(-1) ==
				((source & 1) ? controls::ExposureTimeModeManual : controls::ExposureTimeModeAuto),
				"exposure source must come from capture cookie");
			require(metadata.get(controls::AnalogueGainMode).value_or(-1) ==
				((source & 2) ? controls::AnalogueGainModeManual : controls::AnalogueGainModeAuto),
				"gain source must come from capture cookie");
		};
		ControlList empty(controls::controls);
		auto automatic = prepared(empty);
		require(automatic.agc.source() == 0, "both controls default to Auto");
		require(automatic.agc.exposure == 400 && automatic.agc.gain == 1, "best effort defaults");

		ControlList ignored(controls::controls);
		ignored.set(controls::ExposureTime, 9000);
		ignored.set(controls::AnalogueGain, 7.0f);
		automatic = prepared(ignored);
		require(!automatic.agc.requestedExposure && !automatic.agc.requestedGain, "Auto values not retained");
		require(automatic.agc.exposure == 400 && automatic.agc.gain == 1, "Auto values ignored");

		context.activeState.agc.exposure = 600;
		context.activeState.agc.again = 2;
		automatic = prepared(empty);
		process(automatic, 0, 350, 1.5, false);
		require(automatic.sensor.exposure == 600 && automatic.sensor.gain == 2,
			"invalid statistics must hold the latest computed targets");
		ControlList manualMode(controls::controls);
		manualMode.set(controls::ExposureTimeMode, controls::ExposureTimeModeManual);
		manualMode.set(controls::AnalogueGainMode, controls::AnalogueGainModeManual);
		auto manual = prepared(manualMode);
		require(manual.agc.exposure == 600 && manual.agc.gain == 2, "Auto-to-Manual freezes latest targets");
		process(manual, 0, 350, 1.5);
		require(manual.sensor.exposure == 600 && manual.sensor.gain == 2, "old Auto capture must not undo Manual");
		manual = prepared(empty);
		process(manual, 3, 600, 2);
		require(manual.sensor.exposure == 600 && manual.sensor.gain == 2, "Manual persists under dark stats");

		ControlList values(controls::controls);
		values.set(controls::ExposureTime, 1234);
		values.set(controls::AnalogueGain, 3.5f);
		manual = prepared(values);
		require(manual.agc.exposure == 123 && manual.agc.gain == 3.5, "manual units and line quantisation");
		manual = prepared(empty);
		require(manual.agc.exposure == 123 && manual.agc.gain == 3.5, "manual values persist");

		ControlList mixed(controls::controls);
		mixed.set(controls::ExposureTime, 2000);
		mixed.set(controls::AnalogueGainMode, controls::AnalogueGainModeAuto);
		auto frame = prepared(mixed);
		require(frame.agc.source() == 1 && frame.agc.gain == 3.5, "gain resumes from last Manual target");
		process(frame, 1, 200, 3.5);
		require(frame.sensor.exposure == 200 && frame.sensor.gain > 3.5, "gain-only automatic correction");

		mixed = ControlList(controls::controls);
		mixed.set(controls::ExposureTimeMode, controls::ExposureTimeModeAuto);
		mixed.set(controls::AnalogueGainMode, controls::AnalogueGainModeManual);
		mixed.set(controls::AnalogueGain, 3.0f);
		frame = prepared(mixed);
		require(frame.agc.source() == 2 && frame.agc.exposure == 200, "exposure resumes from last Manual target");
		process(frame, 2, 200, 3);
		require(frame.sensor.exposure > 200 && frame.sensor.gain == 3, "exposure-only automatic correction");

		ControlList autoMode(controls::controls);
		autoMode.set(controls::ExposureTimeMode, controls::ExposureTimeModeAuto);
		autoMode.set(controls::AnalogueGainMode, controls::AnalogueGainModeAuto);
		autoMode.set(controls::ExposureTime, 9900);
		autoMode.set(controls::AnalogueGain, 7.9f);
		frame = prepared(autoMode);
		require(frame.agc.source() == 0 && !frame.agc.requestedExposure && !frame.agc.requestedGain,
			"same-request Auto ignores manual values");
		require(frame.agc.gain == 3, "Auto is seeded from previous Manual gain");
		process(frame, 3, 200, 3);
		require(frame.sensor.gain == 3, "source transition waits for matching stats");

		/* Queue a whole batch before preparing any frame. */
		values = manualMode;
		values.set(controls::ExposureTime, 8000);
		values.set(controls::AnalogueGain, 4.0f);
		auto batch0 = queued(values);
		auto batch1 = queued(empty);
		auto batch2 = queued(autoMode);
		auto batch3 = queued(manualMode);
		agc.prepare(context, 0, batch0, nullptr);
		agc.prepare(context, 0, batch1, nullptr);
		require(batch0.agc.exposure == 800 && batch1.agc.exposure == 800, "queued Manual values are independent");
		agc.prepare(context, 0, batch2, nullptr);
		context.activeState.agc.exposure = 650;
		context.activeState.agc.again = 2.2;
		agc.prepare(context, 0, batch3, nullptr);
		require(batch3.agc.exposure == 650 && std::abs(batch3.agc.gain - 2.2) < 1e-6,
			"queued freeze uses last computed targets, not ignored Auto values");

		values = ControlList(controls::controls);
		values.set(controls::ExposureTime, -100);
		values.set(controls::AnalogueGain, 0.0f);
		frame = prepared(values);
		require(frame.agc.exposure == 1 && frame.agc.gain == 1, "lower sensor bounds");
		values.set(controls::ExposureTime, 2147483647);
		values.set(controls::AnalogueGain, 900.0f);
		frame = prepared(values);
		require(frame.agc.exposure == 1000 && frame.agc.gain == 8, "upper sensor bounds");
		require(agc.configure(context, config) == 0, "restart configuration");
		frame = prepared(empty);
		require(frame.agc.source() == 0 && frame.agc.exposure == 400 && frame.agc.gain == 1,
			"restart resets modes and retained manual requests");
		std::cout << "{\"behavioral_assertions\":" << checks << ",\"passed\":true}" << std::endl;
		return 0;
	} catch (const std::exception &error) {
		std::cerr << error.what() << std::endl;
		return 1;
	}
}
