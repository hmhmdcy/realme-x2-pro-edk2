/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* CAMSS inline hardware IPA: explicit manual tuning and validated BHIST. */
#include <array>
#include <algorithm>
#include <cmath>
#include <limits>
#include <linux/videodev2.h>
#include <cerrno>
#include <cstring>
#include <map>
#include <optional>
#include <unistd.h>
#include <time.h>
#include "../libipa/contrast_af.h"

#include <linux/qcom-camss-config.h>
#include <libcamera/base/file.h>
#include <libcamera/base/log.h>
#include <libcamera/control_ids.h>
#include <libcamera/ipa/camss_ipa_interface.h>
#include <libcamera/ipa/ipa_module_info.h>
#include "libcamera/internal/mapped_framebuffer.h"
#include "libcamera/internal/yaml_parser.h"
#include "parameter_encoder.h"
#include "../libipa/camera_sensor_helper.h"
#include "hardware_agc.h"
#include "hardware_awb.h"
#include "statistics.h"

namespace libcamera::ipa::camss {

LOG_DEFINE_CATEGORY(IPACamss)

class IPACamss final : public IPACamssInterface
{
public:
	int init(const IPASettings &settings, const IPACameraSensorInfo &info, const ControlInfoMap &sensorControls, const ControlInfoMap &lensControls, const std::string &lensModel, ControlInfoMap *ipaControls) override;
	int configure(const IPACameraSensorInfo &sensorInfo, const Size &input, const ControlInfoMap &sensorControls, const std::string &profilePath, ControlInfoMap *ipaControls, SensorControlConfiguration *sensorConfiguration) override;
	int mapBuffers(const std::vector<IPABuffer> &parameters, const std::vector<IPABuffer> &statistics) override;
	void unmapBuffers(const std::vector<uint32_t> &ids) override;
	int start(uint64_t epoch, const ControlList &controls, ControlList *sensorControls) override;
	int convertControls(uint64_t epoch, const ControlList &controls, ControlList *sensorControls) override;
	int applyIspControls(uint64_t epoch, const ControlList &controls, AutoIspUpdate *update) override;
	int frameMetadata(uint64_t epoch, uint32_t sof, const SensorContext &sensorContext, ControlList *metadata) override;
 int processFocus(uint64_t epoch,uint32_t sof,const ControlList &controls,bool valid,int32_t score,
                  uint64_t captured,const SensorContext &sensorContext,ControlList *metadata,LensMove *move) override;
 void lensPositionApplied(uint64_t epoch,uint32_t serial,int32_t status,uint64_t monotonic) override;
	void stop() override;
	int prepareParameters(uint64_t epoch, uint32_t id, uint32_t revision, uint32_t *bytesused) override;
	void parametersApplied(uint64_t epoch, uint32_t firstSof, uint32_t revision) override;
	void processStats(uint64_t epoch, uint32_t sof, uint32_t id, uint32_t bytesused, const SensorContext &sensorContext) override;
private:
 int describeSensor(const IPACameraSensorInfo &info, const ControlInfoMap &controls, ControlInfoMap *ipaControls);
 int translate(const ControlList &controls, bool startup, ControlList *sensorControls);
 int configureAutofocus(const ValueNode &tuning,ControlInfoMap *ipaControls);
 ipa::ContrastAf af_;
 bool afEnabled_=false;
 std::optional<ControlInfo> focusControl_;
 std::string lensModel_;
 std::optional<int32_t> initialAfTrigger_;
 uint32_t frameLength_=0;
 std::unique_ptr<CameraSensorHelper> helper_;
 std::unique_ptr<HardwareAgc> agc_;
	std::unique_ptr<HardwareAwb> awb_;
	bool awbEnabled_ = false;
	uint32_t ispRevision_ = 0;
	std::optional<AutoIspUpdate> pendingWhiteBalance_;
	struct ParameterContext { uint32_t revision; double red, blue; bool awbEnabled; double sourceRed, sourceBlue; };
	std::map<uint32_t, ParameterContext> preparedParameters_, parameterHistory_;
 bool automatic_ = false;
 uint32_t revision_ = 0;
 std::optional<AutoSensorUpdate> awaiting_;
 bool autoAvailable_ = false;
 ControlInfoMap sensorControls_;
 double lineUs_ = 0;
 int32_t minLines_ = 0, maxLines_ = 0, minGainCode_ = 0, maxGainCode_ = 0;
 int32_t minExposure_ = 0, maxExposure_ = 0;
 double minGain_ = 1, maxGain_ = 1;
	struct Buffer {
		bool parameters;
		std::unique_ptr<MappedFrameBuffer> memory;
	};
	std::map<uint32_t, Buffer> buffers_;
	ResidualBlackProfile profile_{ 0, 1.0 };
	std::string model_;
	Size input_;
	bool configured_ = false, running_ = false, applied_ = false, effective_ = false;
	uint64_t epoch_ = 0;
	uint32_t firstSof_ = 0;
	std::optional<uint32_t> lastStats_;
	double red_ = 1, blue_ = 1;
};

int IPACamss::describeSensor(const IPACameraSensorInfo &info, const ControlInfoMap &sensorControls, ControlInfoMap *ipaControls)
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
  { &controls::AwbEnable, ControlInfo(false, false, false) },
  { &controls::ExposureTimeMode, ControlInfo(std::vector<ControlValue>{int32_t(controls::ExposureTimeModeManual)}) },
  { &controls::AnalogueGainMode, ControlInfo(std::vector<ControlValue>{int32_t(controls::AnalogueGainModeManual)}) },
  { &controls::ExposureTime, ControlInfo(minExposure_, maxExposure_, int32_t(std::lround(e.def().get<int32_t>() * lineUs_))) },
  { &controls::AnalogueGain, ControlInfo(float(minGain_), float(maxGain_), float(helper_->gain(g.def().get<int32_t>()))) }
 }, controls::controls);
 return 0;
}

int IPACamss::init(const IPASettings &settings, const IPACameraSensorInfo &info,
 const ControlInfoMap &sensorControls,const ControlInfoMap &lensControls,const std::string &lensModel,ControlInfoMap *ipaControls)
{
 if (running_) return -EBUSY;
 model_ = settings.sensorModel;
 if (info.model != model_) return -EINVAL;
 /* The proxy resets V4L2 ControlIds at configure(); retain values only. */
 const auto focus=lensControls.find(V4L2_CID_FOCUS_ABSOLUTE);
 focusControl_=focus==lensControls.end()?std::nullopt:std::optional<ControlInfo>(focus->second);
 lensModel_=lensModel;afEnabled_=false;
 helper_ = CameraSensorHelperFactoryBase::create(model_);
 if (!helper_) return -ENOTSUP;
 int ret = describeSensor(info, sensorControls, ipaControls);
 if (ret) return ret;
 configured_ = false;
 agc_.reset(); awb_.reset(); autoAvailable_ = false;
 if (!settings.configurationFile.empty()) {
  File file(settings.configurationFile);
  if (!file.open(File::OpenModeFlag::ReadOnly)) return file.error();
  auto root=YamlParser::parse(file);
  if (!root || (*root)["sensor_model"].get<std::string>("")!=model_) return -EINVAL;
  ret=configureAutofocus((*root)["autofocus"],ipaControls);
  if (ret) return ret;
 }
 LOG(IPACamss, Info) << "IPA init pid=" << getpid() << " model=" << model_;
 return 0;
}

int IPACamss::configureAutofocus(const ValueNode &tuning,ControlInfoMap *ipaControls)
{
 afEnabled_=false;af_.cancel();
 LOG(IPACamss,Debug)<<"AF configuration lens="<<lensModel_<<" tuning="<<tuning["lens"].get<std::string>("")<<" focus-control="<<focusControl_.has_value();
 if (!tuning || lensModel_.empty() || tuning["lens"].get<std::string>("")!=lensModel_) return 0;
 if (!focusControl_) return 0;
 ipa::ContrastAf::Config config{
  tuning["minimumCode"].get<int32_t>(-1),tuning["maximumCode"].get<int32_t>(-1),
  tuning["coarseStep"].get<int32_t>(0),tuning["fineStep"].get<int32_t>(0),tuning["samples"].get<unsigned int>(3),
  uint64_t(tuning["settleMs"].get<unsigned int>(100))*1000000,
  uint64_t(tuning["timeoutMs"].get<unsigned int>(120000))*1000000,
  tuning["minimumPeak"].get<int32_t>(100),tuning["peakRatio"].get<double>(1.15),tuning["verifyRatio"].get<double>(.75)};
 if (config.minimum<focusControl_->min().get<int32_t>() || config.maximum>focusControl_->max().get<int32_t>() || !af_.configure(config)) return -EINVAL;
 afEnabled_=true;
 ControlInfoMap::Map map;
 for (const auto &[id,value]:*ipaControls) map.emplace(id,value);
 map[&controls::AfMode]=ControlInfo(int32_t(controls::AfModeAuto),int32_t(controls::AfModeAuto),int32_t(controls::AfModeAuto));
 map[&controls::AfTrigger]=ControlInfo(int32_t(controls::AfTriggerStart),int32_t(controls::AfTriggerCancel),int32_t(controls::AfTriggerCancel));
 map[&controls::AfState]=ControlInfo(int32_t(controls::AfStateIdle),int32_t(controls::AfStateFailed),int32_t(controls::AfStateIdle));
 *ipaControls=ControlInfoMap(std::move(map),controls::controls);
 LOG(IPACamss,Debug)<<"AF enabled controls="<<ipaControls->size();
 return 0;
}

int IPACamss::configure(const IPACameraSensorInfo &info, const Size &input,
 const ControlInfoMap &sensorControls, const std::string &profilePath,
 ControlInfoMap *ipaControls, SensorControlConfiguration *sensorConfiguration)
{
 if (running_) return -EBUSY;
 configured_ = false;
 agc_.reset(); awb_.reset(); autoAvailable_ = false;
 if (!sensorConfiguration) return -EINVAL;
 *sensorConfiguration = {};
 if (info.model != model_ || info.outputSize != input || info.bitsPerPixel != 10 ||
     input.width < 4 || input.height < 2 || ((input.width | input.height) & 1)) return -EINVAL;
 int ret = describeSensor(info, sensorControls, ipaControls);
 if (ret) return ret;
 profile_ = { 0, 1.0 };
 afEnabled_=false;af_.cancel();frameLength_=info.minFrameLength;
 if (!profilePath.empty()) {
  File file(profilePath);
  if (!file.open(File::OpenModeFlag::ReadOnly)) return file.error();
  auto root = YamlParser::parse(file);
  if (!root || (*root)["sensor_model"].get<std::string>().value_or("") != model_) return -EINVAL;
  const unsigned int version=(*root)["version"].get<unsigned int>().value_or(0);
  const ValueNode *selected=root.get();
  if (version==2) {
   const auto &modes=(*root)["modes"];
   if (!modes.isList()) return -EINVAL;
   selected=nullptr;
   for (const auto &mode:modes.asList()) {
    const auto &match=mode["match"];
    if (!mode.isDictionary() || !match.isDictionary()) return -EINVAL;
    if (match["width"].get<unsigned int>().value_or(0)!=input.width ||
        match["height"].get<unsigned int>().value_or(0)!=input.height ||
        match["pixel_rate"].get<unsigned int>().value_or(0)!=info.pixelRate ||
        match["line_length"].get<unsigned int>().value_or(0)!=info.minLineLength ||
        match["frame_length"].get<unsigned int>().value_or(0)!=info.minFrameLength) continue;
    if (selected) return -EINVAL;
    selected=&mode;
   }
   if (!selected) return -ENOTSUP;
  } else if (version!=1) return -EINVAL;
  const ValueNode &tuning=*selected;
  ret=configureAutofocus(tuning["autofocus"].isEmpty()?(*root)["autofocus"]:tuning["autofocus"],ipaControls);
  if (ret) return ret;
  auto subtraction = tuning["residual_black_subtraction"].get<uint16_t>();
  auto normalization = tuning["range_normalization"].get<double>();
  if (!subtraction || !normalization) return -EINVAL;
  profile_ = { *subtraction, *normalization };
  const auto &awb = tuning["awb"];
  if (!awb.isEmpty()) {
   auto candidate = std::make_unique<HardwareAwb>();
   if (!awb.isDictionary() || candidate->initialise(awb)) return -EINVAL;
   awb_ = std::move(candidate);
   ControlInfoMap::Map map;
   for (const auto &[id, value] : *ipaControls) map.emplace(id, value);
   map[&controls::AwbEnable] = ControlInfo(false, true, true);
   *ipaControls = ControlInfoMap(std::move(map), controls::controls);
  }
  const auto &timing = tuning["sensor_controls"];
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
  const auto &agc = tuning["agc"];
  if (!agc.isEmpty()) {
   if (!sensorConfiguration->enabled || !agc.isDictionary()) return -EINVAL;
   auto candidate = std::make_unique<HardwareAgc>();
   ret = candidate->initialise(agc, lineUs_, minLines_, maxLines_, minGain_, maxGain_, helper_.get());
   if (ret) return ret;
   agc_ = std::move(candidate);
   autoAvailable_ = true;
   ControlInfoMap::Map map;
   for (const auto &[id, value] : *ipaControls) map.emplace(id, value);
   map[&controls::ExposureTimeMode] = ControlInfo(std::vector<ControlValue>{
    int32_t(controls::ExposureTimeModeAuto), int32_t(controls::ExposureTimeModeManual)}, int32_t(controls::ExposureTimeModeAuto));
   map[&controls::AnalogueGainMode] = ControlInfo(std::vector<ControlValue>{
    int32_t(controls::AnalogueGainModeAuto), int32_t(controls::AnalogueGainModeManual)}, int32_t(controls::AnalogueGainModeAuto));
   *ipaControls = ControlInfoMap(std::move(map), controls::controls);
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
  if (id==libcamera::controls::AfMode.id() || id==libcamera::controls::AfTrigger.id()) {
   if (!afEnabled_) return -ENOTSUP;
   if (value.type()!=ControlTypeInteger32 || value.isArray()) return -EINVAL;
   if (id==libcamera::controls::AfMode.id() && value.get<int32_t>()!=libcamera::controls::AfModeAuto) return -ENOTSUP;
   if (id==libcamera::controls::AfTrigger.id() && value.get<int32_t>()!=libcamera::controls::AfTriggerStart && value.get<int32_t>()!=libcamera::controls::AfTriggerCancel) return -ENOTSUP;
   continue;
  }
  if (id == controls::ColourGains.id()) {
   if (value.type() != ControlTypeFloat || !value.isArray() || value.numElements() != 2) return -EINVAL;
   for (float gain : value.get<Span<const float>>())
    if (!std::isfinite(gain) || gain < 0 || gain > 8) return -ERANGE;
   continue;
  }
  if (id == controls::AwbEnable.id()) {
   if (value.type() != ControlTypeBool || value.isArray()) return -EINVAL;
   if (value.get<bool>() && !awb_) return -ENOTSUP;
   continue;
  }
  if (id == controls::ExposureTimeMode.id() || id == controls::AnalogueGainMode.id()) {
   if (value.type() != ControlTypeInteger32 || value.isArray()) return -EINVAL;
   const int32_t wanted = id == controls::ExposureTimeMode.id() ? int32_t(controls::ExposureTimeModeManual) : int32_t(controls::AnalogueGainModeManual);
   if (!startup && value.get<int32_t>() != wanted) return -ENOTSUP;
   const int32_t autoMode = id == controls::ExposureTimeMode.id() ? int32_t(controls::ExposureTimeModeAuto) : int32_t(controls::AnalogueGainModeAuto);
   if (startup && value.get<int32_t>() != wanted && value.get<int32_t>() != autoMode) return -ENOTSUP;
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
 ControlList sensorOnly(libcamera::controls::controls);
 for (const auto &[id, value] : controls)
  if (id != libcamera::controls::ColourGains.id() && id != libcamera::controls::AwbEnable.id() && id!=libcamera::controls::AfMode.id() && id!=libcamera::controls::AfTrigger.id()) sensorOnly.set(id,value);
 ControlList ignored(sensorControls_);
 int ret = translate(controls, true, &ignored);
 if (ret) return ret;
 if (automatic_ && !sensorOnly.empty()) return -ENOTSUP;
 return translate(sensorOnly, false, sensorControls);
}

int IPACamss::applyIspControls(uint64_t epoch, const ControlList &controls, AutoIspUpdate *update)
{
 if (!update) return -EINVAL;
 *update = {};
 if (!running_ || epoch != epoch_) return -ESTALE;
 if (pendingWhiteBalance_ || !preparedParameters_.empty() || parameterHistory_.empty()) return -EAGAIN;
 ControlList ignored(sensorControls_);
 int ret = translate(controls, true, &ignored);
 if (ret) return ret;
 const auto &current = parameterHistory_.rbegin()->second;
 const bool enabled = controls.get(libcamera::controls::AwbEnable).value_or(awbEnabled_);
 double red = current.sourceRed, blue = current.sourceBlue;
 if (!enabled) {
  auto gains = controls.get(libcamera::controls::ColourGains);
  if (gains) { red=(*gains)[0];blue=(*gains)[1]; }
 }
 if (enabled == current.awbEnabled && red == current.sourceRed && blue == current.sourceBlue) return 0;
 if (ispRevision_ >= UINT32_MAX-1) return -EOVERFLOW;
 af_.cancelScan();
 awbEnabled_ = enabled;
 if (awb_) awb_->reset();
 pendingWhiteBalance_ = AutoIspUpdate{ true, ++ispRevision_, red, blue };
 *update = *pendingWhiteBalance_;
 return 0;
}

int IPACamss::frameMetadata(uint64_t epoch, uint32_t sof, const SensorContext &sensorContext, ControlList *metadata)
{
 if (!metadata) return -EINVAL;
 *metadata=ControlList(controls::controls);
 if (!running_ || epoch!=epoch_) return -ESTALE;
 auto context=parameterHistory_.upper_bound(sof);
 if (context==parameterHistory_.begin()) return -ENODATA;
 --context;
 if (!sensorContext.valid || sensorContext.exposureLines<uint32_t(minLines_) ||
     sensorContext.exposureLines>uint32_t(maxLines_) || sensorContext.gainCode<uint32_t(minGainCode_) ||
     sensorContext.gainCode>uint32_t(maxGainCode_)) return -ENODATA;
 const std::array<float,2> gains{float(context->second.red),float(context->second.blue)};
 metadata->set(controls::ColourGains,Span<const float,2>(gains));
 metadata->set(controls::AwbEnable,context->second.awbEnabled);
 metadata->set(controls::AwbLocked,false);
 metadata->set(controls::ExposureTimeMode,int32_t(automatic_?controls::ExposureTimeModeAuto:controls::ExposureTimeModeManual));
 metadata->set(controls::AnalogueGainMode,int32_t(automatic_?controls::AnalogueGainModeAuto:controls::AnalogueGainModeManual));
 metadata->set(controls::ExposureTime,int32_t(std::lround(sensorContext.exposureLines*lineUs_)));
 metadata->set(controls::AnalogueGain,float(helper_->gain(sensorContext.gainCode)));
 return 0;
}

int IPACamss::processFocus(uint64_t epoch,uint32_t sof,const ControlList &controls,bool valid,int32_t score,
                         uint64_t captured,const SensorContext &sensorContext,ControlList *metadata,LensMove *move)
{
 if (!metadata || !move) return -EINVAL;
 *metadata=ControlList(libcamera::controls::controls);*move={};
 if (!running_ || epoch!=epoch_) return -ESTALE;
 if (!afEnabled_) return -ENOTSUP;
 timespec clock{};uint64_t now=clock_gettime(CLOCK_MONOTONIC,&clock)?0:uint64_t(clock.tv_sec)*1000000000+clock.tv_nsec;
 auto trigger=controls.get(libcamera::controls::AfTrigger);
 if (initialAfTrigger_) { if (!trigger) trigger=initialAfTrigger_;initialAfTrigger_.reset(); }
 if (trigger && *trigger==libcamera::controls::AfTriggerCancel) af_.cancelScan();
 else if (trigger && *trigger==libcamera::controls::AfTriggerStart) af_.trigger(now);
 const uint64_t guard=std::ceil((uint64_t(frameLength_)+sensorContext.exposureLines)*lineUs_*1000);
 af_.process(valid && sensorContext.valid,score,captured,guard,now);
 if (auto command=af_.takeMove(now)) *move={true,command->serial,command->position};
 if (valid) metadata->set(libcamera::controls::FocusFoM,score);
 metadata->set(libcamera::controls::AfMode,libcamera::controls::AfModeAuto);
 metadata->set(libcamera::controls::AfState,int32_t(af_.state()));
 LOG(IPACamss,Info)<<"AF frame sof="<<sof<<" captured="<<captured<<" guard="<<guard<<" now="<<now<<" valid="<<valid<<" score="<<score<<" state="<<int(af_.state());
 return 0;
}

void IPACamss::lensPositionApplied(uint64_t epoch,uint32_t serial,int32_t status,uint64_t monotonic)
{
 if (running_ && epoch==epoch_) af_.applied(serial,status,monotonic);
}

int IPACamss::mapBuffers(const std::vector<IPABuffer> &parameters, const std::vector<IPABuffer> &statistics)
{
	if (running_)
		return -EBUSY;
	std::map<uint32_t, Buffer> pending;
	for (bool output : { true, false }) {
		for (const IPABuffer &buffer : output ? parameters : statistics) {
			if (!buffer.id || buffer.planes.size() != 1 ||
			    pending.count(buffer.id) || buffers_.count(buffer.id))
				return -EINVAL;
			FrameBuffer frame(buffer.planes);
			auto mapped = std::make_unique<MappedFrameBuffer>(&frame, output
				? MappedFrameBuffer::MapFlag::ReadWrite : MappedFrameBuffer::MapFlag::Read);
			if (!mapped->isValid())
				return mapped->error();
			const size_t required = sizeof(v4l2_isp_buffer) + (output
				? sizeof(camss_params_wb_gain) + sizeof(camss_params_aec_bhist) : sizeof(camss_stats_bhist));
			if (mapped->planes()[0].size() < required)
				return -ENOSPC;
			pending.emplace(buffer.id, Buffer{ output, std::move(mapped) });
		}
	}
	buffers_.merge(pending);
	return 0;
}

void IPACamss::unmapBuffers(const std::vector<uint32_t> &ids)
{
	/* Pipeline first stops the IPA and all V4L2 queues. */
	if (running_)
		return;
	for (uint32_t id : ids)
		buffers_.erase(id);
}

int IPACamss::start(uint64_t epoch, const ControlList &controls, ControlList *sensorControls)
{
	if (running_)
		return -EBUSY;
	if (!configured_ || !epoch || epoch <= epoch_)
		return -EINVAL;
 if (!sensorControls) return -EINVAL;
 ControlList initial(sensorControls_);
 int translated = translate(controls, true, &initial);
 if (translated) return translated;
 const int32_t exposureMode = controls.get(controls::ExposureTimeMode).value_or(autoAvailable_ ? controls::ExposureTimeModeAuto : controls::ExposureTimeModeManual);
 const int32_t gainMode = controls.get(controls::AnalogueGainMode).value_or(autoAvailable_ ? controls::AnalogueGainModeAuto : controls::AnalogueGainModeManual);
 const bool automatic = exposureMode == controls::ExposureTimeModeAuto && gainMode == controls::AnalogueGainModeAuto;
 const bool manual = exposureMode == controls::ExposureTimeModeManual && gainMode == controls::AnalogueGainModeManual;
 if ((!automatic && !manual) || (automatic && !autoAvailable_)) return -ENOTSUP;
	const bool awbEnabled = controls.get(controls::AwbEnable).value_or(bool(awb_));
	if (awbEnabled && !awb_) return -ENOTSUP;
	double red = 1, blue = 1;
	for (const auto &[id, value] : controls) {
		if (id != controls::ColourGains.id())
			continue;
		if (value.type() != ControlTypeFloat || !value.isArray() || value.numElements() != 2)
			return -EINVAL;
		auto gains = value.get<Span<const float>>();
		if (gains.size() != 2)
			return -EINVAL;
		red = gains[0]; blue = gains[1];
	}
	alignas(8) std::array<uint8_t, sizeof(v4l2_isp_buffer) + sizeof(camss_params_wb_gain) + sizeof(camss_params_aec_bhist)> packet;
	size_t used;
	int ret = encodeParameters(packet, profile_, red, blue, input_, Rectangle(input_), &used);
	if (ret)
		return ret;
 *sensorControls = initial;
 af_.cancel();initialAfTrigger_=controls.get(libcamera::controls::AfTrigger);
 automatic_ = automatic;
 revision_ = 0;
 awaiting_.reset();
 if (agc_) agc_->resetFrameCount();
 epoch_ = epoch;
	red_ = red; blue_ = blue;
	awbEnabled_ = awbEnabled;
	ispRevision_ = 0;
	pendingWhiteBalance_.reset();
	preparedParameters_.clear(); parameterHistory_.clear();
	if (awb_) awb_->reset();
	applied_ = effective_ = false;
	lastStats_.reset();
	running_ = true;
	return 0;
}

void IPACamss::stop()
{
	running_ = false;af_.cancel();initialAfTrigger_.reset();
 automatic_ = false; awaiting_.reset();
	awbEnabled_ = false; pendingWhiteBalance_.reset();
	preparedParameters_.clear(); parameterHistory_.clear();
	applied_ = effective_ = false;
	lastStats_.reset();
}

int IPACamss::prepareParameters(uint64_t epoch, uint32_t id, uint32_t revision, uint32_t *bytesused)
{
	if (!bytesused)
		return -EINVAL;
	*bytesused = 0;
	if (!running_ || epoch != epoch_)
		return -ESTALE;
	auto it = buffers_.find(id);
	if (it == buffers_.end() || !it->second.parameters)
		return -ENOENT;
	if (preparedParameters_.count(revision)) return -EALREADY;
	double red = red_, blue = blue_;
	if (revision) {
		if (!pendingWhiteBalance_ || pendingWhiteBalance_->revision != revision) return -ESTALE;
		red = pendingWhiteBalance_->red; blue = pendingWhiteBalance_->blue;
	} else if (!parameterHistory_.empty()) return -ESTALE;
	double effectiveRed, effectiveBlue;
	int ret = effectiveColourGains(profile_, red, blue, &effectiveRed, &effectiveBlue);
	if (ret) return ret;
	size_t used;
	ret = encodeParameters(it->second.memory->planes()[0], profile_, red, blue, input_, Rectangle(input_), &used);
	if (!ret) {
		preparedParameters_[revision] = { revision, effectiveRed, effectiveBlue, awbEnabled_, red, blue };
		*bytesused = used;
	}
	return ret;
}

void IPACamss::parametersApplied(uint64_t epoch, uint32_t firstSof, uint32_t revision)
{
	if (!running_ || epoch != epoch_) return;
	auto it = preparedParameters_.find(revision);
	if (it == preparedParameters_.end() ||
	    (!parameterHistory_.empty() &&
	     (firstSof <= parameterHistory_.rbegin()->first || revision <= parameterHistory_.rbegin()->second.revision))) {
		LOG(IPACamss, Error) << "Invalid ISP parameter acknowledgement revision=" << revision;
		return;
	}
	parameterHistory_[firstSof] = it->second;
	preparedParameters_.erase(it);
	if (pendingWhiteBalance_ && pendingWhiteBalance_->revision == revision) pendingWhiteBalance_.reset();
	while (parameterHistory_.size() > 64) parameterHistory_.erase(parameterHistory_.begin());
	LOG(IPACamss, Info) << "ISP applied epoch=" << epoch << " revision=" << revision << " first-sof=" << firstSof << " awb=" << parameterHistory_.at(firstSof).awbEnabled;
}

void IPACamss::processStats(uint64_t epoch, uint32_t sof, uint32_t id, uint32_t bytesused, const SensorContext &sensorContext)
{
	Statistics result{};
	ControlList metadata(controls::controls);
	result.status = -ESTALE;
	auto complete = [&]() {
		LOG(IPACamss, Debug) << "IPA stats pid=" << getpid() << " epoch=" << epoch << " sof=" << sof << " status=" << result.status;
		statsProcessed.emit(epoch, sof, id, result, metadata);
	};
	if (!running_ || epoch != epoch_) { complete(); return; }
	auto it = buffers_.find(id);
	if (it == buffers_.end() || it->second.parameters) { result.status = -ENOENT; complete(); return; }
	const auto &memory = it->second.memory->planes()[0];
	if (bytesused > memory.size()) { result.status = -EINVAL; complete(); return; }
	if (lastStats_ && sof <= *lastStats_) {
		result.status = sof == *lastStats_ ? -EALREADY : -ERANGE; complete(); return;
	}
	ParsedStatistics parsed;
	result.status = parseStatistics({ memory.data(), bytesused }, input_.width, input_.height, &parsed);
	if (result.status) { complete(); return; }
	lastStats_ = sof;
	result.population = parsed.population;
	result.weightedSum = parsed.weightedSum;
	result.rgbPresent = !parsed.grid.regions.empty();
	auto context = parameterHistory_.upper_bound(sof);
	if (context != parameterHistory_.begin()) {
		--context;
		result.parametersKnown = true;
		result.ispRevision = context->second.revision;
		const std::array<float, 2> gains{ float(context->second.red), float(context->second.blue) };
		metadata.set(controls::ColourGains, Span<const float, 2>(gains));
	}
	effective_ = result.parametersKnown;
	metadata.set(controls::AwbEnable, result.parametersKnown && context->second.awbEnabled);
	metadata.set(controls::AwbLocked, false);
	if (af_.state()!=ipa::ContrastAf::State::Scanning && awbEnabled_ && effective_ && context->second.awbEnabled && result.rgbPresent && context == std::prev(parameterHistory_.end()) &&
	    !pendingWhiteBalance_ && preparedParameters_.empty()) {
		auto awb = awb_->calculate(parsed.grid, context->second.red, context->second.blue);
		result.awbRegions = awb.regions;
		result.rgbMeans = { awb.means.r(), awb.means.g(), awb.means.b() };
		metadata.set(controls::AwbLocked, awb.locked);
		if (awb.valid && ispRevision_ < UINT32_MAX - 1) {
			double red, blue;
			if (!effectiveColourGains(profile_, awb.red, awb.blue, &red, &blue) &&
			    (red != context->second.red || blue != context->second.blue)) {
				pendingWhiteBalance_ = AutoIspUpdate{ true, ++ispRevision_, awb.red, awb.blue };
				result.ispUpdate = *pendingWhiteBalance_;
			}
		}
	}
	LOG(IPACamss, Info) << "RGB epoch=" << epoch << " sof=" << sof << " present=" << result.rgbPresent
		<< " regions=" << result.awbRegions << " revision=" << result.ispRevision
		<< " parameters-known=" << result.parametersKnown;
 if (sensorContext.valid && sensorContext.exposureLines >= uint32_t(minLines_) &&
     sensorContext.exposureLines <= uint32_t(maxLines_) && sensorContext.gainCode >= uint32_t(minGainCode_) &&
     sensorContext.gainCode <= uint32_t(maxGainCode_)) {
  result.sensorControlsKnown = true;
  metadata.set(controls::ExposureTimeMode, int32_t(automatic_ ? controls::ExposureTimeModeAuto : controls::ExposureTimeModeManual));
  metadata.set(controls::AnalogueGainMode, int32_t(automatic_ ? controls::AnalogueGainModeAuto : controls::AnalogueGainModeManual));
  metadata.set(controls::ExposureTime, int32_t(std::lround(sensorContext.exposureLines * lineUs_)));
  metadata.set(controls::AnalogueGain, float(helper_->gain(sensorContext.gainCode)));
 }
 if (af_.state()!=ipa::ContrastAf::State::Scanning && automatic_ && effective_ && result.sensorControlsKnown &&
     (!awaiting_ || (sensorContext.source == awaiting_->revision &&
      sensorContext.exposureLines == awaiting_->exposureLines && sensorContext.gainCode == awaiting_->gainCode))) {
  awaiting_.reset();
  uint32_t lines, code;
  if (!agc_->calculate(parsed.histogram, sensorContext.exposureLines, sensorContext.gainCode, &lines, &code) &&
      (lines != sensorContext.exposureLines || code != sensorContext.gainCode) && revision_ < UINT32_MAX - 1) {
   result.automaticUpdate = { true, ++revision_, lines, code };
   awaiting_ = result.automaticUpdate;
  }
 }
 complete();
}

} /* namespace libcamera::ipa::camss */

namespace libcamera {
extern "C" {
const IPAModuleInfo ipaModuleInfo = {
	IPA_MODULE_API_VERSION, 0, "camss-vfe", "camss-vfe",
};
IPAInterface *ipaCreate() { return new ipa::camss::IPACamss(); }
}
} /* namespace libcamera */
