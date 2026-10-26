"""Extend the real-DSO contract with sensor conversion, mode gating and context."""
from pathlib import Path
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'kernel300'
s=(OLD/'ipa-contract.cpp').read_text().replace('#include <array>','#include <array>\n#include <linux/videodev2.h>')
a=s.index('\tassert(ipa->init(');b=s.index('\tSharedFD paramFd',a)
s=s[:a]+''' const ControlId exposureId(V4L2_CID_EXPOSURE, "Exposure", "V4L2", ControlTypeInteger32, ControlId::Direction::In | ControlId::Direction::Out);
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
'''+s[b:]
# Existing calls only; preserve the new wrapper body.
s=s.replace('ipa->start(1, controls)','start(1, controls)').replace('ipa->start(2, controls)','start(2, controls)')
anchor='\tassert(start(1, controls) == 0);';assert s.count(anchor)==1
s=s.replace(anchor,anchor+'''
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
''')
s=s.replace('ipa->processStats(epoch, sof, id, bytes);','ipa->processStats(epoch, sof, id, bytes, ipa::camss::SensorContext{true, 500, 512, 42});')
anchor='\t\tif (!status) assert(observation.statistics.parametersKnown == known);';assert s.count(anchor)==1
s=s.replace(anchor,anchor+'''
  if (!status) {
   assert(observation.statistics.sensorControlsKnown);
   assert(observation.metadata.get(controls::ExposureTimeMode).value_or(-1) == controls::ExposureTimeModeManual);
   assert(observation.metadata.get(controls::AnalogueGainMode).value_or(-1) == controls::AnalogueGainModeManual);
   assert(observation.metadata.get(controls::ExposureTime).value_or(0) == 4974);
   assert(observation.metadata.get(controls::AnalogueGain).value_or(0) == 2.0f);
  } else {
   assert(!observation.metadata.contains(controls::ExposureTime.id()) && !observation.metadata.contains(controls::AnalogueGain.id()));
  }
''')
anchor='\tprocess(1, 18, 100, statsBytes, -ERANGE, false);';assert s.count(anchor)==1
s=s.replace(anchor,anchor+'''
 ipa->processStats(1, 22, 100, statsBytes, ipa::camss::SensorContext{});
 assert(!observation.statistics.status && !observation.statistics.sensorControlsKnown);
 assert(!observation.metadata.contains(controls::ExposureTime.id()) && !observation.metadata.contains(controls::AnalogueGain.id()));
 ipa->processStats(1, 23, 100, statsBytes, ipa::camss::SensorContext{true, 500, 2000, 42});
 assert(!observation.statistics.status && !observation.statistics.sensorControlsKnown);
 assert(!observation.metadata.contains(controls::ExposureTime.id()));
''')
(HERE/'ipa-contract.cpp').write_text(s)
s=(OLD/'test-ipa-contract.py').read_text().replace('camss300-contract','camss302-contract').replace("HERE.parent/'kernel299/manual-sunny-imx319-bls.yaml'","HERE/'imx319-manual.yaml'").replace('stage=300','stage=302')
s=s.replace('out=dict(stage=302,','out=dict(stage=302,sensor_helper_conversion_5000us_to503lines_and_gain4_to768_verified=True,mode_clock_mismatch_rejected=True,invalid_conversion_atomic=True,exposure_gain_metadata_quantized_and_missing_for_unknown_or_out_of_range_context=True,')
(HERE/'test-ipa-contract.py').write_text(s)
print('Prepared real302 DSO contract, independent numeric conversions and old wire/error cases.')
