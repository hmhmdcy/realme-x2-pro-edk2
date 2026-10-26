"""Add standard sensor conversion and frame context to the preserved300 IPA."""
from pathlib import Path
import shutil
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'kernel300'
for name in ['ipa','pipeline']:
 (HERE/name).mkdir(exist_ok=True)
 for p in (OLD/name).glob('*'):shutil.copyfile(p,HERE/name/p.name)
s=(OLD/'camss.mojom').read_text()
s=s.replace('struct Statistics {','''struct SensorControlConfiguration {
	bool enabled;
	uint32 exposureDelay;
	uint32 gainDelay;
};
struct SensorContext {
	bool valid;
	uint32 exposureLines;
	uint32 gainCode;
	uint32 source;
};
struct Statistics {''').replace('\tbool parametersKnown;','\tbool parametersKnown;\n\tbool sensorControlsKnown;')
s=s.replace('init(libcamera.IPASettings settings) => (int32 ret);','''init(libcamera.IPASettings settings, libcamera.IPACameraSensorInfo sensorInfo,
	     libcamera.ControlInfoMap sensorControls) => (int32 ret, libcamera.ControlInfoMap ipaControls);''')
s=s.replace('configure(libcamera.IPACameraSensorInfo sensorInfo, libcamera.Size input) => (int32 ret);','''configure(libcamera.IPACameraSensorInfo sensorInfo, libcamera.Size input,
		  libcamera.ControlInfoMap sensorControls, string profilePath)
		=> (int32 ret, libcamera.ControlInfoMap ipaControls, SensorControlConfiguration sensorConfiguration);''')
s=s.replace('start(uint64 epoch, libcamera.ControlList controls) => (int32 ret);','''start(uint64 epoch, libcamera.ControlList controls) => (int32 ret, libcamera.ControlList sensorControls);
	convertControls(uint64 epoch, libcamera.ControlList controls) => (int32 ret, libcamera.ControlList sensorControls);''')
s=s.replace('uint32 bufferId, uint32 bytesused);','uint32 bufferId, uint32 bytesused, SensorContext sensorContext);')
(HERE/'camss.mojom').write_text(s)
s=(OLD/'ipa/camss.cpp').read_text()
s=s.replace('#include <array>','#include <array>\n#include <algorithm>\n#include <cmath>\n#include <limits>\n#include <linux/videodev2.h>')
s=s.replace('#include "parameter_encoder.h"','#include "parameter_encoder.h"\n#include "../libipa/camera_sensor_helper.h"')
s=s.replace('int init(const IPASettings &settings) override;','int init(const IPASettings &settings, const IPACameraSensorInfo &info, const ControlInfoMap &sensorControls, ControlInfoMap *ipaControls) override;')
s=s.replace('int configure(const IPACameraSensorInfo &sensorInfo, const Size &input) override;','int configure(const IPACameraSensorInfo &sensorInfo, const Size &input, const ControlInfoMap &sensorControls, const std::string &profilePath, ControlInfoMap *ipaControls, SensorControlConfiguration *sensorConfiguration) override;')
s=s.replace('int start(uint64_t epoch, const ControlList &controls) override;','int start(uint64_t epoch, const ControlList &controls, ControlList *sensorControls) override;\n\tint convertControls(uint64_t epoch, const ControlList &controls, ControlList *sensorControls) override;')
s=s.replace('uint32_t id, uint32_t bytesused) override;','uint32_t id, uint32_t bytesused, const SensorContext &sensorContext) override;')
anchor='\tstruct Buffer {';s=s.replace(anchor,''' int describeSensor(const IPACameraSensorInfo &info, const ControlInfoMap &controls, ControlInfoMap *ipaControls);
 int translate(const ControlList &controls, bool startup, ControlList *sensorControls);
 std::unique_ptr<CameraSensorHelper> helper_;
 ControlInfoMap sensorControls_;
 double lineUs_ = 0;
 int32_t minLines_ = 0, maxLines_ = 0, minGainCode_ = 0, maxGainCode_ = 0;
 int32_t minExposure_ = 0, maxExposure_ = 0;
 double minGain_ = 1, maxGain_ = 1;
'''+anchor)
a=s.index('int IPACamss::init(');b=s.index('int IPACamss::mapBuffers(',a)
s=s[:a]+r'''int IPACamss::describeSensor(const IPACameraSensorInfo &info, const ControlInfoMap &sensorControls, ControlInfoMap *ipaControls)
{
 if (!helper_ || !ipaControls || !info.pixelRate || !info.minLineLength ||
     info.minLineLength != info.maxLineLength) return -EINVAL;
 auto exposure = sensorControls.find(V4L2_CID_EXPOSURE);
 auto gain = sensorControls.find(V4L2_CID_ANALOGUE_GAIN);
 if (exposure == sensorControls.end() || gain == sensorControls.end()) return -ENOTSUP;
 const ControlInfo &e = exposure->second, &g = gain->second;
 minLines_ = e.min().get<int32_t>(); maxLines_ = e.max().get<int32_t>();
 minGainCode_ = g.min().get<int32_t>(); maxGainCode_ = g.max().get<int32_t>();
 lineUs_ = double(info.minLineLength) * 1000000 / info.pixelRate;
 if (minLines_ <= 0 || maxLines_ < minLines_ || minGainCode_ < 0 || maxGainCode_ < minGainCode_ ||
     !std::isfinite(lineUs_) || lineUs_ <= 0 || maxLines_ * lineUs_ > std::numeric_limits<int32_t>::max()) return -ERANGE;
 minExposure_ = std::lround(minLines_ * lineUs_); maxExposure_ = std::lround(maxLines_ * lineUs_);
 minGain_ = helper_->gain(minGainCode_); maxGain_ = helper_->gain(maxGainCode_);
 if (!std::isfinite(minGain_) || !std::isfinite(maxGain_) || minGain_ <= 0 || maxGain_ < minGain_) return -ERANGE;
 sensorControls_ = sensorControls;
 *ipaControls = ControlInfoMap({
  { &controls::ColourGains, ControlInfo(0.0f, 8.0f, 1.0f) },
  { &controls::ExposureTimeMode, ControlInfo(std::vector<ControlValue>{int32_t(controls::ExposureTimeModeManual)}) },
  { &controls::AnalogueGainMode, ControlInfo(std::vector<ControlValue>{int32_t(controls::AnalogueGainModeManual)}) },
  { &controls::ExposureTime, ControlInfo(minExposure_, maxExposure_, int32_t(std::lround(e.def().get<int32_t>() * lineUs_))) },
  { &controls::AnalogueGain, ControlInfo(float(minGain_), float(maxGain_), float(helper_->gain(g.def().get<int32_t>()))) }
 }, controls::controls);
 return 0;
}

int IPACamss::init(const IPASettings &settings, const IPACameraSensorInfo &info,
 const ControlInfoMap &sensorControls, ControlInfoMap *ipaControls)
{
 if (running_) return -EBUSY;
 model_ = settings.sensorModel;
 if (info.model != model_ || !settings.configurationFile.empty()) return -EINVAL;
 helper_ = CameraSensorHelperFactoryBase::create(model_);
 if (!helper_) return -ENOTSUP;
 int ret = describeSensor(info, sensorControls, ipaControls);
 if (ret) return ret;
 configured_ = false;
 LOG(IPACamss, Info) << "IPA init pid=" << getpid() << " model=" << model_;
 return 0;
}

int IPACamss::configure(const IPACameraSensorInfo &info, const Size &input,
 const ControlInfoMap &sensorControls, const std::string &profilePath,
 ControlInfoMap *ipaControls, SensorControlConfiguration *sensorConfiguration)
{
 if (running_) return -EBUSY;
 configured_ = false;
 if (!sensorConfiguration) return -EINVAL;
 *sensorConfiguration = {};
 if (info.model != model_ || info.outputSize != input || info.bitsPerPixel != 10 ||
     input.width < 4 || input.height < 2 || ((input.width | input.height) & 1)) return -EINVAL;
 int ret = describeSensor(info, sensorControls, ipaControls);
 if (ret) return ret;
 profile_ = { 0, 1.0 };
 if (!profilePath.empty()) {
  File file(profilePath);
  if (!file.open(File::OpenModeFlag::ReadOnly)) return file.error();
  auto root = YamlParser::parse(file);
  if (!root || (*root)["version"].get<unsigned int>().value_or(0) != 1 ||
      (*root)["sensor_model"].get<std::string>().value_or("") != model_) return -EINVAL;
  auto subtraction = (*root)["residual_black_subtraction"].get<uint16_t>();
  auto normalization = (*root)["range_normalization"].get<double>();
  if (!subtraction || !normalization) return -EINVAL;
  profile_ = { *subtraction, *normalization };
  const auto &timing = (*root)["sensor_controls"];
  if (!timing.isEmpty()) {
   if (!timing.isDictionary()) return -EINVAL;
   if (timing["width"].get<unsigned int>().value_or(0) != input.width ||
       timing["height"].get<unsigned int>().value_or(0) != input.height ||
       timing["pixel_rate"].get<unsigned int>().value_or(0) != info.pixelRate ||
       timing["line_length"].get<unsigned int>().value_or(0) != info.minLineLength ||
       timing["frame_length"].get<unsigned int>().value_or(0) != info.minFrameLength) return -EINVAL;
   auto exposureDelay = timing["exposure_delay"].get<unsigned int>();
   auto gainDelay = timing["gain_delay"].get<unsigned int>();
   if (!exposureDelay || !gainDelay || *exposureDelay != *gainDelay ||
       !*exposureDelay || *exposureDelay > 4) return -EINVAL;
   *sensorConfiguration = { true, *exposureDelay, *gainDelay };
  }
 }
 input_ = input; configured_ = true;
 LOG(IPACamss, Info) << "Sensor configuration model=" << model_ << " pixel-rate=" << info.pixelRate
  << " line-length=" << info.minLineLength << " frame-length=" << info.minFrameLength
  << " delayed-controls=" << sensorConfiguration->enabled;
 return 0;
}

int IPACamss::translate(const ControlList &controls, bool startup, ControlList *sensorControls)
{
 if (!sensorControls) return -EINVAL;
 ControlList translated(sensorControls_);
 for (const auto &[id, value] : controls) {
  if (id == controls::ColourGains.id() && startup) continue;
  if (id == controls::ExposureTimeMode.id() || id == controls::AnalogueGainMode.id()) {
   if (value.type() != ControlTypeInteger32 || value.isArray()) return -EINVAL;
   const int32_t wanted = id == controls::ExposureTimeMode.id() ? int32_t(controls::ExposureTimeModeManual) : int32_t(controls::AnalogueGainModeManual);
   if (value.get<int32_t>() != wanted) return -ENOTSUP;
   continue;
  }
  if (id == controls::ExposureTime.id()) {
   if (value.type() != ControlTypeInteger32 || value.isArray()) return -EINVAL;
   int32_t time = value.get<int32_t>();
   if (time < minExposure_ || time > maxExposure_) return -ERANGE;
   int32_t lines = std::clamp<int64_t>(std::llround(time / lineUs_), minLines_, maxLines_);
   translated.set(V4L2_CID_EXPOSURE, lines);
  } else if (id == controls::AnalogueGain.id()) {
   if (value.type() != ControlTypeFloat || value.isArray()) return -EINVAL;
   float gain = value.get<float>();
   if (!std::isfinite(gain) || gain < minGain_ || gain > maxGain_) return -ERANGE;
   int32_t code = std::clamp<int64_t>(helper_->gainCode(gain), minGainCode_, maxGainCode_);
   translated.set(V4L2_CID_ANALOGUE_GAIN, code);
  } else return -EINVAL;
 }
 *sensorControls = translated;
 return 0;
}

int IPACamss::convertControls(uint64_t epoch, const ControlList &controls, ControlList *sensorControls)
{
 if (!running_ || epoch != epoch_) return -ESTALE;
 return translate(controls, false, sensorControls);
}

'''+s[b:]
s=s.replace('int IPACamss::start(uint64_t epoch, const ControlList &controls)','int IPACamss::start(uint64_t epoch, const ControlList &controls, ControlList *sensorControls)')
anchor='\tdouble red = 1, blue = 1;';s=s.replace(anchor,'\tint translated = translate(controls, true, sensorControls);\n\tif (translated) return translated;\n'+anchor)
s=s.replace('if (id != controls::ColourGains.id())\n\t\t\treturn -EINVAL;','if (id != controls::ColourGains.id())\n\t\t\tcontinue;')
s=s.replace('uint32_t id, uint32_t bytesused)\n{','uint32_t id, uint32_t bytesused, const SensorContext &sensorContext)\n{')
anchor='\tcomplete();\n}\n\n} /* namespace libcamera::ipa::camss */'
assert s.count(anchor)==1
s=s.replace(anchor,''' if (sensorContext.valid && sensorContext.exposureLines >= uint32_t(minLines_) &&
     sensorContext.exposureLines <= uint32_t(maxLines_) && sensorContext.gainCode >= uint32_t(minGainCode_) &&
     sensorContext.gainCode <= uint32_t(maxGainCode_)) {
  result.sensorControlsKnown = true;
  metadata.set(controls::ExposureTimeMode, controls::ExposureTimeModeManual);
  metadata.set(controls::AnalogueGainMode, controls::AnalogueGainModeManual);
  metadata.set(controls::ExposureTime, int32_t(std::lround(sensorContext.exposureLines * lineUs_)));
  metadata.set(controls::AnalogueGain, float(helper_->gain(sensorContext.gainCode)));
 }
'''+anchor)
(HERE/'ipa/camss.cpp').write_text(s)
print('Prepared302 IPA source and standard generated interface. No SDK/phone mutation yet.')
