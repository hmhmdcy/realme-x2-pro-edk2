"""Build a candidate patch from the exact retained r11 tree, without deployment."""
from pathlib import Path
import difflib,hashlib,json,shutil

here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel225')
sdk=Path('/home/cy122/x2pro-linux/libcamera214-root');base=sdk/'work/libcamera224-r11-built/src/libcamera-v0.7.2'
originals={};changed={}
def read(name):
 if name not in originals:originals[name]=(base/name).read_text()
 return changed.get(name,originals[name])
def replace(name,old,new,count=1):
 text=read(name);assert text.count(old)==count,(name,old,text.count(old));changed[name]=text.replace(old,new)

n='include/libcamera/internal/delayed_controls.h'
replace(n,'#include <stdint.h>','#include <optional>\n#include <stdint.h>')
replace(n,'void reset();','void reset(uint32_t cookie = 0);')
replace(n,'bool push(const ControlList &controls);','bool push(const ControlList &controls, std::optional<uint32_t> cookie = std::nullopt);')
replace(n,'ControlList get(uint32_t sequence);','ControlList get(uint32_t sequence, uint32_t *cookie = nullptr);')
replace(n,'\tuint32_t queueCount_;','\t/* Opaque source tags follow the same delayed target slots as controls. */\n\tstd::array<uint32_t, listSize> cookies_;\n\n\tuint32_t queueCount_;')
n='src/libcamera/delayed_controls.cpp'
replace(n,'void DelayedControls::reset()','void DelayedControls::reset(uint32_t cookie)')
replace(n,'\tqueueCount_ = 1;','\tcookies_.fill(cookie);\n\tqueueCount_ = 1;')
replace(n,'bool DelayedControls::push(const ControlList &controls)','bool DelayedControls::push(const ControlList &controls, std::optional<uint32_t> cookie)')
replace(n,'\tqueueCount_++;','\tcookies_[queueCount_ % listSize] =\n\t\tcookie.value_or(cookies_[(queueCount_ - 1) % listSize]);\n\tqueueCount_++;')
replace(n,'ControlList DelayedControls::get(uint32_t sequence)','ControlList DelayedControls::get(uint32_t sequence, uint32_t *cookie)')
replace(n,'\tunsigned int index = std::max<int>(0, sequence - maxDelay_);','\tunsigned int index = std::max<int>(0, sequence - maxDelay_);\n\tif (cookie)\n\t\t*cookie = cookies_[index % listSize];\n\tLOG(DelayedControls, Debug) << "Reading source cookie "\n\t\t<< cookies_[index % listSize] << " at index " << index;')
replace(n,' * \u005cparam[in] controls List of controls to add to the device queue',' * \u005cparam[in] controls List of controls to add to the device queue\n * \u005cparam[in] cookie Optional opaque source tag; an omitted tag retains the previous one')

n='src/ipa/simple/ipa_context.h'
replace(n,'''	struct {
		int32_t exposure;
		double again;
		bool valid;
	} agc;''','''	struct {
		int32_t exposure;
		double again;
		int32_t manualExposure;
		double manualGain;
		bool queueAutoExposure;
		bool queueAutoGain;
		bool preparedAutoExposure;
		bool preparedAutoGain;
		std::optional<int32_t> requestedExposure;
		std::optional<double> requestedGain;
	} agc;''')
replace(n,'''		int32_t exposure;
		double gain;
	} sensor;''','''		int32_t exposure;
		double gain;
		uint32_t source;
	} sensor;

	struct {
		bool autoExposure;
		bool autoGain;
		std::optional<int32_t> requestedExposure;
		std::optional<double> requestedGain;
		int32_t exposure;
		double gain;
		uint32_t source() const
		{
			return (autoExposure ? 0 : 1) | (autoGain ? 0 : 2);
		}
	} agc;''')

n='src/ipa/simple/algorithms/agc.h'
replace(n,'\tvoid process(IPAContext &context, const uint32_t frame,','''	int init(IPAContext &context, const ValueNode &tuningData) override;
	int configure(IPAContext &context, const IPAConfigInfo &configInfo) override;
	void queueRequest(IPAContext &context, const uint32_t frame,
			  IPAFrameContext &frameContext, const ControlList &controls) override;
	void prepare(IPAContext &context, const uint32_t frame,
		     IPAFrameContext &frameContext, DebayerParams *params) override;

	void process(IPAContext &context, const uint32_t frame,''')
n='src/ipa/simple/algorithms/agc.cpp'
replace(n,'#include "control_ids.h"','#include "control_ids.h"\n\n#include <linux/v4l2-controls.h>')
marker='void Agc::updateExposure(IPAContext &context, IPAFrameContext &frameContext, double exposureMSV)'
new=r'''int Agc::init(IPAContext &context, [[maybe_unused]] const ValueNode &tuningData)
{
	context.ctrlMap[&controls::AeEnable] = ControlInfo(false, true, true);
	context.ctrlMap[&controls::ExposureTimeMode] =
		ControlInfo(static_cast<int32_t>(controls::ExposureTimeModeAuto),
			    static_cast<int32_t>(controls::ExposureTimeModeManual),
			    static_cast<int32_t>(controls::ExposureTimeModeAuto));
	context.ctrlMap[&controls::AnalogueGainMode] =
		ControlInfo(static_cast<int32_t>(controls::AnalogueGainModeAuto),
			    static_cast<int32_t>(controls::AnalogueGainModeManual),
			    static_cast<int32_t>(controls::AnalogueGainModeAuto));
	return 0;
}

int Agc::configure(IPAContext &context, const IPAConfigInfo &configInfo)
{
	auto &state = context.activeState.agc;
	state.exposure = std::clamp(configInfo.sensorControls.at(V4L2_CID_EXPOSURE).def().get<int32_t>(),
				    context.configuration.agc.exposureMin,
				    context.configuration.agc.exposureMax);
	state.again = context.configuration.agc.againMin;
	state.manualExposure = state.exposure;
	state.manualGain = state.again;
	state.queueAutoExposure = state.queueAutoGain = true;
	state.preparedAutoExposure = state.preparedAutoGain = true;
	state.requestedExposure.reset();
	state.requestedGain.reset();
	return 0;
}

void Agc::queueRequest(IPAContext &context, [[maybe_unused]] const uint32_t frame,
		       IPAFrameContext &frameContext, const ControlList &controls)
{
	auto &state = context.activeState.agc;
	const auto exposureMode = controls.get(controls::ExposureTimeMode);
	const auto gainMode = controls.get(controls::AnalogueGainMode);
	/* Camera patches AeEnable before this call, including explicit-mode precedence. */
	if (exposureMode) {
		bool automatic = *exposureMode == controls::ExposureTimeModeAuto;
		if (automatic != state.queueAutoExposure)
			state.requestedExposure.reset();
		state.queueAutoExposure = automatic;
	}
	if (gainMode) {
		bool automatic = *gainMode == controls::AnalogueGainModeAuto;
		if (automatic != state.queueAutoGain)
			state.requestedGain.reset();
		state.queueAutoGain = automatic;
	}

	/* Values supplied in Auto are ignored, including for future transitions. */
	if (const auto value = controls.get(controls::ExposureTime);
	    value && !state.queueAutoExposure) {
		double lineUs = context.configuration.agc.lineDuration.get<std::micro>();
		double lines = std::clamp(*value / lineUs,
					 static_cast<double>(context.configuration.agc.exposureMin),
					 static_cast<double>(context.configuration.agc.exposureMax));
		state.requestedExposure = static_cast<int32_t>(std::llround(lines));
	}
	if (const auto value = controls.get(controls::AnalogueGain);
	    value && !state.queueAutoGain && std::isfinite(*value))
		state.requestedGain = std::clamp(static_cast<double>(*value),
					       context.configuration.agc.againMin,
					       context.configuration.agc.againMax);

	frameContext.agc.autoExposure = state.queueAutoExposure;
	frameContext.agc.autoGain = state.queueAutoGain;
	frameContext.agc.requestedExposure = state.requestedExposure;
	frameContext.agc.requestedGain = state.requestedGain;
}

void Agc::prepare(IPAContext &context, [[maybe_unused]] const uint32_t frame,
		  IPAFrameContext &frameContext, [[maybe_unused]] DebayerParams *params)
{
	auto &state = context.activeState.agc;
	auto &target = frameContext.agc;
	if (!target.autoExposure) {
		if (target.requestedExposure)
			state.manualExposure = *target.requestedExposure;
		else if (state.preparedAutoExposure)
			state.manualExposure = state.exposure;
	} else if (!state.preparedAutoExposure) {
		state.exposure = state.manualExposure;
	}
	if (!target.autoGain) {
		if (target.requestedGain)
			state.manualGain = *target.requestedGain;
		else if (state.preparedAutoGain)
			state.manualGain = state.again;
	} else if (!state.preparedAutoGain) {
		state.again = state.manualGain;
	}
	state.preparedAutoExposure = target.autoExposure;
	state.preparedAutoGain = target.autoGain;
	target.exposure = target.autoExposure ? state.exposure : state.manualExposure;
	target.gain = target.autoGain ? state.again : state.manualGain;
}

'''+marker
replace(n,marker,new)
replace(n,'if (exposure < context.configuration.agc.exposureMax)', 'if (frameContext.agc.autoExposure && exposure < context.configuration.agc.exposureMax)')
replace(n,'} else {\n\t\t\tdouble next = again * factor;', '} else if (frameContext.agc.autoGain) {\n\t\t\tdouble next = again * factor;')
replace(n,'if (again > context.configuration.agc.again10)', 'if (frameContext.agc.autoGain && again > context.configuration.agc.again10)')
replace(n,'} else {\n\t\t\tint32_t next = static_cast<int32_t>(exposure * factor);', '} else if (frameContext.agc.autoExposure) {\n\t\t\tint32_t next = static_cast<int32_t>(exposure * factor);')
replace(n,'\tcontext.activeState.agc.exposure = exposure;\n\tcontext.activeState.agc.again = again;','')
a=read(n).index('\tif (!context.activeState.agc.valid) {');b=read(n).index('\n\t/*\n\t * Calculate Mean Sample',a)
text=read(n);changed[n]=text[:a]+r'''	metadata.set(controls::ExposureTimeMode,
		     (frameContext.sensor.source & 1) ? controls::ExposureTimeModeManual
						    : controls::ExposureTimeModeAuto);
	metadata.set(controls::AnalogueGainMode,
		     (frameContext.sensor.source & 2) ? controls::AnalogueGainModeManual
						    : controls::AnalogueGainModeAuto);

	/* Targets belong to this request; metadata above belongs to the captured SOF. */
	bool sourcesMatch = frameContext.sensor.source == frameContext.agc.source();
	if (!frameContext.agc.autoExposure || !sourcesMatch)
		frameContext.sensor.exposure = frameContext.agc.exposure;
	if (!frameContext.agc.autoGain || !sourcesMatch)
		frameContext.sensor.gain = frameContext.agc.gain;
	if (!stats->valid || !sourcesMatch ||
	    (!frameContext.agc.autoExposure && !frameContext.agc.autoGain))
		return;
'''+text[b:]
replace(n,'\tupdateExposure(context, frameContext, exposureMSV);','''	updateExposure(context, frameContext, exposureMSV);
	if (frameContext.agc.autoExposure)
		context.activeState.agc.exposure = frameContext.sensor.exposure;
	if (frameContext.agc.autoGain)
		context.activeState.agc.again = frameContext.sensor.gain;''')

n='include/libcamera/ipa/soft.mojom'
replace(n,'\tstart() => (int32 ret);','\tstart(libcamera.ControlList controls)\n\t\t=> (int32 ret, libcamera.ControlList sensorControls, uint32 source);')
replace(n,'\t\t=> (int32 ret);','\t\t=> (int32 ret, libcamera.ControlInfoMap ipaControls);')
replace(n,'\t\t\t     libcamera.ControlList sensorControls);','\t\t\t     libcamera.ControlList sensorControls,\n\t\t\t     uint32 source);')
replace(n,'setSensorControls(libcamera.ControlList sensorControls);','setSensorControls(libcamera.ControlList sensorControls, uint32 source);')

n='src/ipa/simple/soft_simple.cpp'
replace(n,'int configure(const IPAConfigInfo &configInfo) override;','int configure(const IPAConfigInfo &configInfo, ControlInfoMap *ipaControls) override;')
replace(n,'int start() override;','int start(const ControlList &controls, ControlList *sensorControls, uint32_t *source) override;')
replace(n,'\t\t\t  const ControlList &sensorControls) override;','\t\t\t  const ControlList &sensorControls, uint32_t source) override;')
replace(n,'\tvoid updateExposure(double exposureMSV);','\tvoid updateControls(ControlInfoMap *ipaControls);\n\tControlList sensorControls(const IPAFrameContext &frameContext) const;\n\tIPAConfigInfo configInfo_;')
old='\tControlInfoMap::Map ctrlMap = context_.ctrlMap;\n\t*ipaControls = ControlInfoMap(std::move(ctrlMap), controls::controls);\n'
replace(n,old,'')
marker='int IPASoftSimple::configure(const IPAConfigInfo &configInfo)'
replace(n,marker,'int IPASoftSimple::configure(const IPAConfigInfo &configInfo, ControlInfoMap *ipaControls)')
replace(n,'\tcontext_.sensorInfo = configInfo.sensorInfo;','\tconfigInfo_ = configInfo;\n\tcontext_.sensorInfo = configInfo.sensorInfo;')
old='\treturn 0;\n}\n\nint IPASoftSimple::configure('
new='\tconfigInfo_ = { sensorInfo, sensorControls };\n\tsensorInfoMap_ = sensorControls;\n\tupdateControls(ipaControls);\n\treturn 0;\n}\n\nint IPASoftSimple::configure('
replace(n,old,new)
old='\treturn 0;\n}\n\nint IPASoftSimple::start()\n{\n\treturn 0;\n}'
new=r'''	updateControls(ipaControls);
	return 0;
}

void IPASoftSimple::updateControls(ControlInfoMap *ipaControls)
{
	const ControlInfo &exposure = sensorInfoMap_.at(V4L2_CID_EXPOSURE);
	const ControlInfo &gain = sensorInfoMap_.at(V4L2_CID_ANALOGUE_GAIN);
	double lineUs = context_.sensorInfo.minLineLength * 1000000.0 / context_.sensorInfo.pixelRate;
	context_.ctrlMap[&controls::ExposureTime] =
		ControlInfo(static_cast<int32_t>(std::ceil(exposure.min().get<int32_t>() * lineUs)),
			    static_cast<int32_t>(std::floor(exposure.max().get<int32_t>() * lineUs)),
			    static_cast<int32_t>(exposure.def().get<int32_t>() * lineUs));
	context_.ctrlMap[&controls::AnalogueGain] =
		ControlInfo(static_cast<float>(camHelper_ ? camHelper_->gain(gain.min().get<int32_t>()) : gain.min().get<int32_t>()),
			    static_cast<float>(camHelper_ ? camHelper_->gain(gain.max().get<int32_t>()) : gain.max().get<int32_t>()),
			    static_cast<float>(camHelper_ ? camHelper_->gain(gain.def().get<int32_t>()) : gain.def().get<int32_t>()));
	ControlInfoMap::Map map = context_.ctrlMap;
	*ipaControls = ControlInfoMap(std::move(map), controls::controls);
}

ControlList IPASoftSimple::sensorControls(const IPAFrameContext &frameContext) const
{
	ControlList controls(sensorInfoMap_);
	controls.set(V4L2_CID_EXPOSURE, frameContext.sensor.exposure);
	double gain = frameContext.sensor.gain;
	controls.set(V4L2_CID_ANALOGUE_GAIN,
		     static_cast<int32_t>(camHelper_ ? camHelper_->gainCode(gain) : gain));
	return controls;
}

int IPASoftSimple::start(const ControlList &controls, ControlList *sensorControls, uint32_t *source)
{
	/* A restart without configure() must also restore the default Auto modes. */
	context_.activeState = {};
	context_.frameContexts.clear();
	for (const auto &algo : algorithms()) {
		int ret = algo->configure(context_, configInfo_);
		if (ret)
			return ret;
	}
	IPAFrameContext initial{};
	context_.activeState.combinedMatrix = Matrix<float, 3, 3>::identity();
	for (const auto &algo : algorithms())
		algo->queueRequest(context_, 0, initial, controls);
	for (const auto &algo : algorithms())
		algo->prepare(context_, 0, initial, params_);
	initial.sensor.exposure = initial.agc.exposure;
	initial.sensor.gain = initial.agc.gain;
	*sensorControls = this->sensorControls(initial);
	*source = initial.agc.source();
	return 0;
}'''
replace(n,old,new)
replace(n,'\t\t\t\t const ControlList &sensorControls)\n{','\t\t\t\t const ControlList &sensorControls, uint32_t source)\n{')
marker='\tIPAFrameContext &frameContext = context_.frameContexts.get(frame);\n\n\tframeContext.sensor.exposure ='
replace(n,marker,'''	if (!sensorControls.contains(V4L2_CID_EXPOSURE) ||
	    !sensorControls.contains(V4L2_CID_ANALOGUE_GAIN)) {
		LOG(IPASoft, Error) << "Control(s) missing";
		return;
	}
	IPAFrameContext &frameContext = context_.frameContexts.get(frame);
	frameContext.sensor.source = source;

	frameContext.sensor.exposure =''')
a=read(n).index('\t/* Sanity check */',read(n).index('void IPASoftSimple::processStats'));b=read(n).index('\n}\n',a)
text=read(n);changed[n]=text[:a]+'\tsetSensorControls.emit(this->sensorControls(frameContext), frameContext.agc.source());'+text[b:]

n='include/libcamera/internal/software_isp/software_isp.h'
replace(n,'\t\t\t  const ControlList &sensorControls);','\t\t\t  const ControlList &sensorControls, uint32_t source);')
replace(n,'int start();','int start(const ControlList &controls, ControlList *sensorControls, uint32_t *source);')
replace(n,'const ipa::soft::IPAConfigInfo &configInfo);','const ipa::soft::IPAConfigInfo &configInfo, ControlInfoMap *ipaControls);')
replace(n,'Signal<const ControlList &> setSensorControls;','Signal<const ControlList &, uint32_t> setSensorControls;')
replace(n,'void setSensorCtrls(const ControlList &sensorControls);','void setSensorCtrls(const ControlList &sensorControls, uint32_t source);')
n='src/libcamera/software_isp/software_isp.cpp'
replace(n,'const ControlList &sensorControls)\n{\n\tASSERT(ipa_);','const ControlList &sensorControls, uint32_t source)\n{\n\tASSERT(ipa_);')
replace(n,'ipa_->processStats(frame, bufferId, sensorControls);','ipa_->processStats(frame, bufferId, sensorControls, source);')
replace(n,'const ipa::soft::IPAConfigInfo &configInfo)\n{','const ipa::soft::IPAConfigInfo &configInfo, ControlInfoMap *ipaControls)\n{')
replace(n,'int ret = ipa_->configure(configInfo);','int ret = ipa_->configure(configInfo, ipaControls);')
replace(n,'int SoftwareIsp::start()','int SoftwareIsp::start(const ControlList &controls, ControlList *sensorControls, uint32_t *source)')
replace(n,'int ret = ipa_->start();','int ret = ipa_->start(controls, sensorControls, source);')
replace(n,'void SoftwareIsp::setSensorCtrls(const ControlList &sensorControls)\n{\n\tsetSensorControls.emit(sensorControls);','void SoftwareIsp::setSensorCtrls(const ControlList &sensorControls, uint32_t source)\n{\n\tsetSensorControls.emit(sensorControls, source);')

n='src/libcamera/pipeline/simple/simple.cpp'
replace(n,'\tstd::optional<ControlList> sensorControls;','\tstd::optional<ControlList> sensorControls;\n\tuint32_t sensorControlSource = 0;')
replace(n,'void setSensorControls(const ControlList &sensorControls);','void setSensorControls(const ControlList &sensorControls, uint32_t source);')
replace(n,'info->sensorControls = delayedCtrls_->get(sequence);','info->sensorControls = delayedCtrls_->get(sequence, &info->sensorControlSource);')
replace(n,'swIsp_->processStats(frame, bufferId, *info->sensorControls);','swIsp_->processStats(frame, bufferId, *info->sensorControls, info->sensorControlSource);')
replace(n,'void SimpleCameraData::setSensorControls(const ControlList &sensorControls)\n{\n\tdelayedCtrls_->push(sensorControls);','void SimpleCameraData::setSensorControls(const ControlList &sensorControls, uint32_t source)\n{\n\tdelayedCtrls_->push(sensorControls, source);')
replace(n,'data->swIsp_->configure(inputCfg, outputCfgs, configInfo);','data->swIsp_->configure(inputCfg, outputCfgs, configInfo, &data->controlInfo_);')
replace(n,'int SimplePipelineHandler::start(Camera *camera, [[maybe_unused]] const ControlList *controls)','int SimplePipelineHandler::start(Camera *camera, const ControlList *controls)')
replace(n,'\tdata->delayedCtrls_->reset();',r'''	uint32_t initialSource = 0;
	if (data->useConversion_ && data->swIsp_) {
		ControlList sensorControls;
		ControlList emptyControls(libcamera::controls::controls);
		ret = data->swIsp_->start(controls ? *controls : emptyControls,
					&sensorControls, &initialSource);
		if (!ret)
			ret = data->sensor_->setControls(&sensorControls);
		if (ret) {
			stop(camera);
			return ret < 0 ? ret : -EINVAL;
		}
	}
	/* Seed both values and their source before the first SOF can arrive. */
	data->delayedCtrls_->reset(initialSource);''')
replace(n,'\t\telse if (data->swIsp_)\n\t\t\tret = data->swIsp_->start();','')

patch='''Subject: [PATCH] simple: support manual exposure and delayed source metadata

Expose independent exposure/gain modes and values, preserve queued request
controls, ignore manual values in Auto, freeze Auto-to-Manual transitions,
seed Auto from the last manual target, and apply start controls before SOF.
Keep opaque mode tags in the same delayed slots as the sensor values and
snapshot them at capture, instead of echoing the current request modes.

---
'''
for name in sorted(changed):
 text=changed[name];p=private/'manual-source'/name;assert not p.exists();p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
 patch+='diff --git a/'+name+' b/'+name+'\n'+''.join(difflib.unified_diff(originals[name].splitlines(True),text.splitlines(True),fromfile='a/'+name,tofile='b/'+name))
(here/'libcamera-manual-exposure-controls.patch').write_text(patch)
recipe=sdk/'work/libcamera225';assert not recipe.exists();recipe.mkdir()
for p in (sdk/'work/libcamera224-r11').iterdir():
 if p.is_file() and not p.is_symlink() and p.name!='source-lock.json':shutil.copyfile(p,recipe/p.name)
name='0018-simple-manual-exposure-controls.patch';(recipe/name).write_text(patch)
text=(recipe/'APKBUILD').read_text();assert text.count('pkgrel=11\n')==1;text=text.replace('pkgrel=11\n','pkgrel=12\n')
marker='\t0017-simple-capture-cancel-status.patch\n';assert text.count(marker)==1;text=text.replace(marker,marker+'\t'+name+'\n')
marker=next(l for l in text.splitlines(True) if l.rstrip().endswith('  0017-simple-capture-cancel-status.patch'))
text=text.replace(marker,marker+hashlib.sha512(patch.encode()).hexdigest()+'  '+name+'\n');(recipe/'APKBUILD').write_text(text)
config=sdk/'work/samurai-camera-config225';assert not config.exists();config.mkdir()
for name in ['APKBUILD','configuration.yaml','70-samurai-camera-heaps.rules','samurai-camera-heaps.conf','README.md']:shutil.copyfile(sdk/'work/samurai-camera-config224-r11'/name,config/name)
text=(config/'APKBUILD').read_text().replace('pkgrel=6\n','pkgrel=7\n').replace('99990.7.2-r11','99990.7.2-r12');(config/'APKBUILD').write_text(text)
proof=dict(stage=225,candidate_framework='99990.7.2-r12',candidate_config_stack='0.1.0-r7',
 patch_sha256=hashlib.sha256(patch.encode()).hexdigest(),
 original_sources_sha256={n:hashlib.sha256(t.encode()).hexdigest() for n,t in originals.items()},
 source_files={n:hashlib.sha256(t.encode()).hexdigest() for n,t in changed.items()},
 prior17_patches_and_full_features_preserved=True,independent_modes_start_controls_and_source_cookie_candidate=True,
 kernel_driver_delay_values_unchanged_and_optical_delay_unverified=True,not_built_or_deployed=True)
(here/'candidate-source-validation.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(dict(stage=225,files=len(changed),patch_sha256=proof['patch_sha256'],candidate='r12/r7',not_deployed=True)))
