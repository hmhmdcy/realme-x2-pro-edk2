"""Wire immutable focus statistics, acknowledged lens moves and generic AF search."""
from pathlib import Path
import difflib,hashlib,json
R=Path(__file__).resolve().parent
S=Path('/home/cy122/x2pro-linux/libcamera214-root/work/libcamera277-r23-built/src/libcamera-v0.7.2')
names=['include/libcamera/internal/framebuffer.h','src/libcamera/v4l2_videodevice.cpp',
 'include/libcamera/internal/software_isp/swstats_cpu.h','src/libcamera/software_isp/swstats_cpu.cpp',
 'include/libcamera/internal/software_isp/software_isp.h','src/libcamera/software_isp/software_isp.cpp',
 'src/libcamera/pipeline/simple/simple.cpp','include/libcamera/ipa/soft.mojom',
 'src/ipa/simple/ipa_context.h','src/ipa/simple/soft_simple.cpp']
before={n:(S/n).read_text() for n in names};after=dict(before)
def change(n,a,b):
 assert after[n].count(a)==1,(n,a);after[n]=after[n].replace(a,b)
def span(n,a,b,new):
 start=after[n].index(a);end=after[n].index(b,start);after[n]=after[n][:start]+new+after[n][end:]
change(names[0],'\tbool isContiguous() const { return isContiguous_; }','''\tbool isContiguous() const { return isContiguous_; }
\tbool timestampMonotonic() const { return timestampMonotonic_; }
\tvoid setTimestampMonotonic(bool monotonic) { timestampMonotonic_ = monotonic; }''')
change(names[0],'\tbool isContiguous_;','\tbool isContiguous_;\n\tbool timestampMonotonic_ = false;')
change(names[1],'''\tmetadata.timestamp = buf.timestamp.tv_sec * 1000000000ULL
\t\t\t   + buf.timestamp.tv_usec * 1000ULL;''','''\tmetadata.timestamp = buf.timestamp.tv_sec * 1000000000ULL
\t\t\t   + buf.timestamp.tv_usec * 1000ULL;
\tbuffer->_d()->setTimestampMonotonic((buf.flags & V4L2_BUF_FLAG_TIMESTAMP_MASK) ==
\t\t\t\t\t V4L2_BUF_FLAG_TIMESTAMP_MONOTONIC);''')
change(names[2],'Signal<uint32_t, uint32_t> statsReady;','Signal<uint32_t, uint32_t, bool, int32_t> statsReady;')
change(names[3],'\tstatsReady.emit(frame, bufferId);','''\t/* Copy the focus measurement while this producer still owns its frame. */
\tstd::optional<int32_t> focus = valid ? sharedStats_->focus.figureOfMerit() : std::nullopt;
\tstatsReady.emit(frame, bufferId, focus.has_value(), focus.value_or(0));''')
change(names[4],'''\t\t\t  const ControlList &sensorControls, uint32_t source);''','''\t\t\t  const ControlList &sensorControls, uint32_t source,
\t\t\t  bool focusValid, int32_t focus, uint64_t capturedMonotonic);''')
change(names[4],'\tvoid stop();','\tvoid stop();\n\tvoid lensPositionApplied(uint32_t serial, int32_t status, uint64_t monotonic);')
change(names[4],'Signal<uint32_t, uint32_t> ispStatsReady;','Signal<uint32_t, uint32_t, bool, int32_t> ispStatsReady;')
change(names[4],'\tSignal<const ControlList &, uint32_t> setSensorControls;','\tSignal<const ControlList &, uint32_t> setSensorControls;\n\tSignal<uint32_t, int32_t> setLensControls;')
change(names[4],'\tvoid statsReady(uint32_t frame, uint32_t bufferId);','\tvoid statsReady(uint32_t frame, uint32_t bufferId, bool focusValid, int32_t focus);')
change(names[4],'class Debayer;','class Debayer;\nclass CameraLens;')
change(names[4],'\t\t    ControlInfoMap *ipaControls);','\t\t    ControlInfoMap *ipaControls, CameraLens *lens = nullptr);')
change(names[5],'#include "libcamera/internal/software_isp/software_isp.h"','#include "libcamera/internal/software_isp/software_isp.h"\n#include "libcamera/internal/camera_lens.h"')
change(names[5],'\t\t\t ControlInfoMap *ipaControls)','\t\t\t ControlInfoMap *ipaControls, CameraLens *lens)')
change(names[5],'''\t\t\t sensor->controls(),
\t\t\t ipaControls,''','''\t\t\t sensor->controls(),
\t\t\t lens ? lens->controls() : ControlInfoMap{},
\t\t\t lens ? lens->model() : std::string{},
\t\t\t ipaControls,''')
change(names[5],'\tipa_->setSensorControls.connect(this, &SoftwareIsp::setSensorCtrls);','''\tipa_->setSensorControls.connect(this, &SoftwareIsp::setSensorCtrls);
\tipa_->setLensControls.connect(this, [this](uint32_t serial, int32_t position) {
\t\tsetLensControls.emit(serial, position);
\t});''')
change(names[5],'''\t\t\t       const ControlList &sensorControls, uint32_t source)
{
\tASSERT(ipa_);
\tipa_->processStats(frame, bufferId, sensorControls, source);
}''','''\t\t\t       const ControlList &sensorControls, uint32_t source,
\t\t\t       bool focusValid, int32_t focus, uint64_t capturedMonotonic)
{
\tASSERT(ipa_);
\tipa_->processStats(frame, bufferId, sensorControls, source,
\t\t\t   focusValid, focus, capturedMonotonic);
}''')
change(names[5],'''void SoftwareIsp::statsReady(uint32_t frame, uint32_t bufferId)
{
\tispStatsReady.emit(frame, bufferId);
}''','''void SoftwareIsp::statsReady(uint32_t frame, uint32_t bufferId,
\t\t\t     bool focusValid, int32_t focus)
{
\tispStatsReady.emit(frame, bufferId, focusValid, focus);
}

void SoftwareIsp::lensPositionApplied(uint32_t serial, int32_t status, uint64_t monotonic)
{
\tipa_->lensPositionApplied(serial, status, monotonic);
}''')
change(names[6],'#include <algorithm>','#include <algorithm>\n#include <time.h>')
change(names[6],'\tuint32_t sensorControlSource = 0;','\tuint32_t sensorControlSource = 0;\n\tuint64_t capturedMonotonic = 0;')
change(names[6],'\tstd::unique_ptr<SoftwareIsp> swIsp_;','\tstd::unique_ptr<SoftwareIsp> swIsp_;\n\tbool lensActive_ = false;')
change(names[6],'\tvoid ispStatsReady(uint32_t frame, uint32_t bufferId);','\tvoid ispStatsReady(uint32_t frame, uint32_t bufferId, bool focusValid, int32_t focus);')
change(names[6],'\tvoid setSensorControls(const ControlList &sensorControls, uint32_t source);','\tvoid setSensorControls(const ControlList &sensorControls, uint32_t source);\n\tvoid setLensControls(uint32_t serial, int32_t position);')
change(names[6],'std::make_unique<SoftwareIsp>(pipe, sensor_.get(), &controlInfo_)','std::make_unique<SoftwareIsp>(pipe, sensor_.get(), &controlInfo_, sensor_->focusLens())')
anchor='\t\tswIsp_->setSensorControls.connect(this, &SimpleCameraData::setSensorControls);'
change(names[6],anchor,anchor+'\n\t\tswIsp_->setLensControls.connect(this, &SimpleCameraData::setLensControls);')
change(names[6],'\t\t\tinfo->sensorControls = delayedCtrls_->get(sequence, &info->sensorControlSource);','''\t\t\tinfo->sensorControls = delayedCtrls_->get(sequence, &info->sensorControlSource);
\t\t\tinfo->capturedMonotonic = buffer->_d()->timestampMonotonic()
\t\t\t\t? buffer->metadata().timestamp : 0;''')
change(names[6],'void SimpleCameraData::ispStatsReady(uint32_t frame, uint32_t bufferId)','void SimpleCameraData::ispStatsReady(uint32_t frame, uint32_t bufferId,\n\t\t\t\t   bool focusValid, int32_t focus)')
change(names[6],'\tswIsp_->processStats(frame, bufferId, *info->sensorControls, info->sensorControlSource);','\tswIsp_->processStats(frame, bufferId, *info->sensorControls, info->sensorControlSource,\n\t\t\t     focusValid, focus, info->capturedMonotonic);')
anchor='void SimpleCameraData::setSensorControls(const ControlList &sensorControls, uint32_t source)'
addition='''void SimpleCameraData::setLensControls(uint32_t serial, int32_t position)
{
\tCameraLens *lens = sensor_->focusLens();
\tint ret = lensActive_ && lens ? lens->setFocusPosition(position) : -EPIPE;
\tstruct timespec now{};
\tuint64_t timestamp = clock_gettime(CLOCK_MONOTONIC, &now) == 0
\t\t? uint64_t(now.tv_sec) * 1000000000ULL + now.tv_nsec : 0;
\tLOG(SimplePipeline, Debug) << "Focus command " << serial << " position "
\t\t\t\t   << position << " result " << ret << " at " << timestamp;
\tswIsp_->lensPositionApplied(serial, ret, timestamp);
}

'''
change(names[6],anchor,addition+anchor)
anchor='''\t\tret = lens->open();
\t\tif (ret) {
\t\t\tstop(camera);
\t\t\treturn ret;
\t\t}
\t}'''
change(names[6],anchor,anchor[:-2]+'\t\tdata->lensActive_ = true;\n\t}')
anchor='''void SimplePipelineHandler::stopDevice(Camera *camera)
{
\tSimpleCameraData *data = cameraData(camera);'''
change(names[6],anchor,anchor+'\n\tdata->lensActive_ = false;')
change(names[7],'''\t     libcamera.ControlInfoMap sensorControls)
''','''\t     libcamera.ControlInfoMap sensorControls,
\t     libcamera.ControlInfoMap lensControls,
\t     string lensModel)
''')
change(names[7],'\tstop();','\tstop();\n\t[async] lensPositionApplied(uint32 serial, int32 status, uint64 monotonic);')
change(names[7],'\t\t\t     uint32 source);','\t\t\t     uint32 source,\n\t\t\t     bool focusValid, int32 focus, uint64 capturedMonotonic);')
change(names[7],'\tsetIspParams();','\tsetIspParams();\n\tsetLensControls(uint32 serial, int32 position);')
change(names[8],'struct IPAFrameContext : public FrameContext {','struct IPAFrameContext : public FrameContext {\n\tstd::optional<int32_t> afTrigger;\n\tbool afCancel = false;')
change(names[9],'#include <cmath>','#include <cmath>\n#include <time.h>')
change(names[9],'#include "libipa/camera_sensor_helper.h"','#include "libipa/camera_sensor_helper.h"\n#include "libipa/contrast_af.h"')
change(names[9],'''\t\t const ControlInfoMap &sensorControls,
\t\t ControlInfoMap *ipaControls,''','''\t\t const ControlInfoMap &sensorControls,
\t\t const ControlInfoMap &lensControls, const std::string &lensModel,
\t\t ControlInfoMap *ipaControls,''')
change(names[9],'\tvoid stop() override;','\tvoid stop() override;\n\tvoid lensPositionApplied(uint32_t serial, int32_t status, uint64_t monotonic) override;')
change(names[9],'\t\t\t  const ControlList &sensorControls, uint32_t source) override;','\t\t\t  const ControlList &sensorControls, uint32_t source,\n\t\t\t  bool focusValid, int32_t focus, uint64_t capturedMonotonic) override;')
change(names[9],'\tvoid updateControls(ControlInfoMap *ipaControls);','''\tvoid updateControls(ControlInfoMap *ipaControls);
\tint configureAutofocus(const ValueNode &tuning, const ControlInfoMap &lensControls,
\t\t\t       const std::string &lensModel);
\tipa::ContrastAf af_;
\tipa::ContrastAf::Config afConfig_{};
\tbool afEnabled_ = false, afRunning_ = false, initialAfPending_ = false;
\tstd::optional<int32_t> initialAfTrigger_;''')
change(names[9],'''\t\t\tconst ControlInfoMap &sensorControls,
\t\t\tControlInfoMap *ipaControls,''','''\t\t\tconst ControlInfoMap &sensorControls,
\t\t\tconst ControlInfoMap &lensControls, const std::string &lensModel,
\t\t\tControlInfoMap *ipaControls,''')
anchor='\t/* \\todo Use the IPA configuration file for real. */'
change(names[9],anchor,'''\tint afRet = configureAutofocus((*data)["autofocus"], lensControls, lensModel);
\tif (afRet)
\t\treturn afRet;

'''+anchor)
anchor='int IPASoftSimple::configure(const IPAConfigInfo &configInfo, ControlInfoMap *ipaControls)'
addition='''int IPASoftSimple::configureAutofocus(const ValueNode &tuning,
\t\t\t\t    const ControlInfoMap &lensControls,
\t\t\t\t    const std::string &lensModel)
{
\tafEnabled_ = false;
\tif (!tuning || lensModel.empty() || tuning["lens"].get<std::string>("") != lensModel)
\t\treturn 0;
\tauto control = lensControls.find(V4L2_CID_FOCUS_ABSOLUTE);
\tif (control == lensControls.end())
\t\treturn 0;
\tafConfig_ = {
\t\ttuning["minimumCode"].get<int32_t>(-1),
\t\ttuning["maximumCode"].get<int32_t>(-1),
\t\ttuning["coarseStep"].get<int32_t>(0),
\t\ttuning["fineStep"].get<int32_t>(0),
\t\ttuning["samples"].get<unsigned int>(3),
\t\tuint64_t(tuning["settleMs"].get<unsigned int>(100)) * 1000000,
\t\tuint64_t(tuning["timeoutMs"].get<unsigned int>(120000)) * 1000000,
\t\ttuning["minimumPeak"].get<int32_t>(100),
\t\ttuning["peakRatio"].get<double>(1.15),
\t\ttuning["verifyRatio"].get<double>(0.75),
\t};
\tif (afConfig_.minimum < control->second.min().get<int32_t>() ||
\t    afConfig_.maximum > control->second.max().get<int32_t>() || !af_.configure(afConfig_)) {
\t\tLOG(IPASoft, Error) << "Invalid autofocus tuning or lens control limits";
\t\treturn -EINVAL;
\t}
\tafEnabled_ = true;
\treturn 0;
}

'''
change(names[9],anchor,addition+anchor)
anchor='\tControlInfoMap::Map map = context_.ctrlMap;'
change(names[9],anchor,'''\tif (afEnabled_) {
\t\t/* Auto-only until a calibrated manual distance map is supplied. */
\t\tcontext_.ctrlMap[&controls::AfMode] = ControlInfo(int32_t(controls::AfModeAuto), int32_t(controls::AfModeAuto), int32_t(controls::AfModeAuto));
\t\tcontext_.ctrlMap[&controls::AfTrigger] = ControlInfo(int32_t(controls::AfTriggerStart), int32_t(controls::AfTriggerCancel), int32_t(controls::AfTriggerCancel));
\t\tcontext_.ctrlMap[&controls::AfState] = ControlInfo(int32_t(controls::AfStateIdle), int32_t(controls::AfStateFailed), int32_t(controls::AfStateIdle));
\t}
'''+anchor)
anchor='''\t/* A restart without configure() must also restore the default Auto modes. */'''
change(names[9],anchor,'''\taf_.configure(afConfig_);
\tafRunning_ = afEnabled_;
\tinitialAfPending_ = afEnabled_;
\tinitialAfTrigger_ = controls.get(controls::AfTrigger);
\tif (auto mode = controls.get(controls::AfMode); mode && *mode != controls::AfModeAuto)
\t\tinitialAfTrigger_ = controls::AfTriggerCancel;
'''+anchor)
change(names[9],'''void IPASoftSimple::stop()
{
\tcontext_.frameContexts.clear();
}''','''void IPASoftSimple::stop()
{
\tafRunning_ = false;
\taf_.cancel();
\tcontext_.frameContexts.clear();
}

void IPASoftSimple::lensPositionApplied(uint32_t serial, int32_t status, uint64_t monotonic)
{
\tif (afRunning_)
\t\taf_.applied(serial, status, monotonic);
}''')
anchor='\tIPAFrameContext &frameContext = context_.frameContexts.alloc(frame);'
change(names[9],anchor,anchor+'''
\tframeContext.afTrigger = controls.get(controls::AfTrigger);
\tif (auto mode = controls.get(controls::AfMode); mode && *mode != controls::AfModeAuto)
\t\tframeContext.afCancel = true;
''')
change(names[9],'''\t\t\t\t const ControlList &sensorControls, uint32_t source)
''','''\t\t\t\t const ControlList &sensorControls, uint32_t source,
\t\t\t\t bool focusValid, int32_t focus, uint64_t capturedMonotonic)
''')
old='''\t/* Never report a cached focus score as belonging to another frame. */
\tif (stats_->valid && stats_->frame == frame) {
\t\tif (auto focus = stats_->focus.figureOfMerit())
\t\t\tmetadata.set(controls::FocusFoM, *focus);
\t}'''
new='''\t/* Focus is a value copied with this frame, not a mutable shared snapshot. */
\tif (focusValid)
\t\tmetadata.set(controls::FocusFoM, focus);
\tif (afEnabled_ && afRunning_) {
\t\tstruct timespec clock{};
\t\tuint64_t now = clock_gettime(CLOCK_MONOTONIC, &clock) == 0
\t\t\t? uint64_t(clock.tv_sec) * 1000000000ULL + clock.tv_nsec : 0;
\t\tauto trigger = frameContext.afTrigger;
\t\tif (initialAfPending_) {
\t\t\tif (!trigger)
\t\t\t\ttrigger = initialAfTrigger_;
\t\t\tinitialAfPending_ = false;
\t\t}
\t\tif (frameContext.afCancel)
\t\t\taf_.cancel();
\t\telse if (trigger && *trigger == controls::AfTriggerCancel)
\t\t\taf_.cancelScan();
\t\telse if (trigger && *trigger == controls::AfTriggerStart)
\t\t\taf_.trigger(now);
\t\t/* WM-done timestamps can trail exposure: exclude exposure plus readout. */
\t\tlong double lines = uint64_t(context_.sensorInfo.minFrameLength) +
\t\t\t\t    std::max(frameContext.sensor.exposure, 0);
\t\tuint64_t guard = std::ceil(lines * context_.sensorInfo.minLineLength *
\t\t\t\t\t  1000000000.0L / context_.sensorInfo.pixelRate);
\t\taf_.process(focusValid, focus, capturedMonotonic, guard, now);
\t\tif (auto move = af_.takeMove(now))
\t\t\tsetLensControls.emit(move->serial, move->position);
\t\tmetadata.set(controls::AfMode, controls::AfModeAuto);
\t\tmetadata.set(controls::AfState, static_cast<int32_t>(af_.state()));
\t}'''
change(names[9],old,new)
after['src/ipa/libipa/contrast_af.h']=(R/'contrast_af.h').read_text()
patch=''.join(''.join(difflib.unified_diff(before.get(n,'').splitlines(True),s.splitlines(True),fromfile='a/'+n if n in before else '/dev/null',tofile='b/'+n)) for n,s in after.items())
header='''Subject: [PATCH] simple: add acknowledged contrast AF with frame-owned focus metrics

Carry the scalar focus metric with its frame through the worker and IPA boundary.
Track the capture timestamp clock explicitly. Route standard lens controls with
serial acknowledgements and exclude exposures preceding mechanical settling.
Provide bounded coarse/fine/verification contrast AF through standard Auto mode,
trigger/cancel and state metadata, enabled only by matching sensor/lens tuning.
Keep device ranges and search parameters in data, not controller code.

This does not provide a calibrated manual LensPosition map, continuous AF or a
hardware ISP. Other software ISP algorithms retain their existing stats path.
---
'''
(R/'0028-simple-contrast-autofocus.patch').write_text(header+patch)
d=dict(stage=278,patch_count=28,source_before_files={n:hashlib.sha256(s.encode()).hexdigest() for n,s in before.items()},
 source_files={n:hashlib.sha256(s.encode()).hexdigest() for n,s in after.items()},new_source_files=['src/ipa/libipa/contrast_af.h'],
 immutable_focus_metric_transport=True,explicit_monotonic_timestamp_flag=True,serial_acknowledged_lens_moves=True,
 no_machine_or_address_constants_in_controller=True,auto_trigger_cancel_supported=True,manual_distance_and_continuous_not_implemented=True,
 not_built_or_deployed=True)
(R/'af-source-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(dict(stage=278,source_files=len(after),patch_count=28)))
