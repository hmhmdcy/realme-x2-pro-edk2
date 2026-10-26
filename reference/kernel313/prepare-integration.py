"""Connect the existing acknowledged contrast AF controller to the CAMSS IPA."""
from pathlib import Path
import shutil,yaml
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'kernel312'
for name in ['camss.mojom','build-candidate.py','ipa-contract.cpp','test-ipa.py','pack-runtime.py','native-capture.py','launch-capture.py','poll-capture.py']:
    shutil.copyfile(OLD/name,HERE/name)
for directory in ['ipa','pipeline']:
    (HERE/directory).mkdir(exist_ok=True)
    for p in (OLD/directory).iterdir():
        if p.is_file():shutil.copyfile(p,HERE/directory/p.name)
def edit(name,before,after):
    p=HERE/name;s=p.read_text()
    if s.count(before)!=1:raise RuntimeError((name,before[:90],s.count(before)))
    p.write_text(s.replace(before,after))
edit('camss.mojom','struct Statistics {','''struct LensMove {
 bool valid;
 uint32 serial;
 int32 position;
};
struct Statistics {''')
edit('camss.mojom','libcamera.ControlInfoMap sensorControls) => (int32 ret, libcamera.ControlInfoMap ipaControls);',
     'libcamera.ControlInfoMap sensorControls, libcamera.ControlInfoMap lensControls, string lensModel) => (int32 ret, libcamera.ControlInfoMap ipaControls);')
edit('camss.mojom','\tstop();',''' processFocus(uint64 epoch, uint32 sof, libcamera.ControlList controls, bool valid, int32 score,
              uint64 capturedMonotonic, SensorContext sensorContext)
              => (int32 ret, libcamera.ControlList metadata, LensMove move);
 [async] lensPositionApplied(uint64 epoch, uint32 serial, int32 status, uint64 monotonic);
\tstop();''')
edit('ipa/camss.cpp','#include <unistd.h>','#include <unistd.h>\n#include <time.h>\n#include "../libipa/contrast_af.h"')
edit('ipa/camss.cpp','const ControlInfoMap &sensorControls, ControlInfoMap *ipaControls) override;',
     'const ControlInfoMap &sensorControls, const ControlInfoMap &lensControls, const std::string &lensModel, ControlInfoMap *ipaControls) override;')
edit('ipa/camss.cpp','\tvoid stop() override;',''' int processFocus(uint64_t epoch,uint32_t sof,const ControlList &controls,bool valid,int32_t score,
                  uint64_t captured,const SensorContext &sensorContext,ControlList *metadata,LensMove *move) override;
 void lensPositionApplied(uint64_t epoch,uint32_t serial,int32_t status,uint64_t monotonic) override;
\tvoid stop() override;''')
edit('ipa/camss.cpp',' std::unique_ptr<CameraSensorHelper> helper_;',''' int configureAutofocus(const ValueNode &tuning,ControlInfoMap *ipaControls);
 ipa::ContrastAf af_;
 bool afEnabled_=false;
 ControlInfoMap lensControls_;
 std::string lensModel_;
 std::optional<int32_t> initialAfTrigger_;
 uint32_t frameLength_=0;
 std::unique_ptr<CameraSensorHelper> helper_;''')
edit('ipa/camss.cpp','const ControlInfoMap &sensorControls, ControlInfoMap *ipaControls)\n{\n if (running_) return -EBUSY;',
     'const ControlInfoMap &sensorControls,const ControlInfoMap &lensControls,const std::string &lensModel,ControlInfoMap *ipaControls)\n{\n if (running_) return -EBUSY;')
edit('ipa/camss.cpp','if (info.model != model_ || !settings.configurationFile.empty()) return -EINVAL;',
     'if (info.model != model_) return -EINVAL;\n lensControls_=lensControls;lensModel_=lensModel;afEnabled_=false;')
edit('ipa/camss.cpp',' LOG(IPACamss, Info) << "IPA init pid="',''' if (!settings.configurationFile.empty()) {
  File file(settings.configurationFile);
  if (!file.open(File::OpenModeFlag::ReadOnly)) return file.error();
  auto root=YamlParser::parse(file);
  if (!root || (*root)["sensor_model"].get<std::string>("")!=model_) return -EINVAL;
  ret=configureAutofocus((*root)["autofocus"],ipaControls);
  if (ret) return ret;
 }
 LOG(IPACamss, Info) << "IPA init pid="''')
edit('ipa/camss.cpp','int IPACamss::configure(const IPACameraSensorInfo &info, const Size &input,','''int IPACamss::configureAutofocus(const ValueNode &tuning,ControlInfoMap *ipaControls)
{
 afEnabled_=false;af_.cancel();
 if (!tuning || lensModel_.empty() || tuning["lens"].get<std::string>("")!=lensModel_) return 0;
 auto control=lensControls_.find(V4L2_CID_FOCUS_ABSOLUTE);
 if (control==lensControls_.end()) return 0;
 ipa::ContrastAf::Config config{
  tuning["minimumCode"].get<int32_t>(-1),tuning["maximumCode"].get<int32_t>(-1),
  tuning["coarseStep"].get<int32_t>(0),tuning["fineStep"].get<int32_t>(0),tuning["samples"].get<unsigned int>(3),
  uint64_t(tuning["settleMs"].get<unsigned int>(100))*1000000,
  uint64_t(tuning["timeoutMs"].get<unsigned int>(120000))*1000000,
  tuning["minimumPeak"].get<int32_t>(100),tuning["peakRatio"].get<double>(1.15),tuning["verifyRatio"].get<double>(.75)};
 if (config.minimum<control->second.min().get<int32_t>() || config.maximum>control->second.max().get<int32_t>() || !af_.configure(config)) return -EINVAL;
 afEnabled_=true;
 ControlInfoMap::Map map;
 for (const auto &[id,value]:*ipaControls) map.emplace(id,value);
 map[&controls::AfMode]=ControlInfo(int32_t(controls::AfModeAuto),int32_t(controls::AfModeAuto),int32_t(controls::AfModeAuto));
 map[&controls::AfTrigger]=ControlInfo(int32_t(controls::AfTriggerStart),int32_t(controls::AfTriggerCancel),int32_t(controls::AfTriggerCancel));
 map[&controls::AfState]=ControlInfo(int32_t(controls::AfStateIdle),int32_t(controls::AfStateFailed),int32_t(controls::AfStateIdle));
 *ipaControls=ControlInfoMap(std::move(map),controls::controls);
 return 0;
}

int IPACamss::configure(const IPACameraSensorInfo &info, const Size &input,''')
edit('ipa/camss.cpp',' profile_ = { 0, 1.0 };',' profile_ = { 0, 1.0 };\n afEnabled_=false;af_.cancel();frameLength_=info.minFrameLength;')
edit('ipa/camss.cpp','  const ValueNode &tuning=*selected;','''  const ValueNode &tuning=*selected;
  ret=configureAutofocus(tuning["autofocus"].isEmpty()?(*root)["autofocus"]:tuning["autofocus"],ipaControls);
  if (ret) return ret;''')
edit('ipa/camss.cpp',' for (const auto &[id, value] : controls) {',''' for (const auto &[id, value] : controls) {
  if (id==libcamera::controls::AfMode.id() || id==libcamera::controls::AfTrigger.id()) {
   if (!afEnabled_) return -ENOTSUP;
   if (value.type()!=ControlTypeInteger32 || value.isArray()) return -EINVAL;
   if (id==libcamera::controls::AfMode.id() && value.get<int32_t>()!=libcamera::controls::AfModeAuto) return -ENOTSUP;
   if (id==libcamera::controls::AfTrigger.id() && value.get<int32_t>()!=libcamera::controls::AfTriggerStart && value.get<int32_t>()!=libcamera::controls::AfTriggerCancel) return -ENOTSUP;
   continue;
  }''')
edit('ipa/camss.cpp','if (id != libcamera::controls::ColourGains.id() && id != libcamera::controls::AwbEnable.id()) sensorOnly.set(id,value);',
     'if (id != libcamera::controls::ColourGains.id() && id != libcamera::controls::AwbEnable.id() && id!=libcamera::controls::AfMode.id() && id!=libcamera::controls::AfTrigger.id()) sensorOnly.set(id,value);')
edit('ipa/camss.cpp',' awbEnabled_ = enabled;',' af_.cancelScan();\n awbEnabled_ = enabled;')
edit('ipa/camss.cpp',' automatic_ = automatic;',' af_.cancel();initialAfTrigger_=controls.get(libcamera::controls::AfTrigger);\n automatic_ = automatic;')
edit('ipa/camss.cpp','\trunning_ = false;','\trunning_ = false;af_.cancel();initialAfTrigger_.reset();')
edit('ipa/camss.cpp','if (awbEnabled_ && effective_ && context->second.awbEnabled',
     'if (af_.state()!=ipa::ContrastAf::State::Scanning && awbEnabled_ && effective_ && context->second.awbEnabled')
edit('ipa/camss.cpp','if (automatic_ && effective_ && result.sensorControlsKnown &&',
     'if (af_.state()!=ipa::ContrastAf::State::Scanning && automatic_ && effective_ && result.sensorControlsKnown &&')
edit('ipa/camss.cpp','int IPACamss::mapBuffers(','''int IPACamss::processFocus(uint64_t epoch,uint32_t sof,const ControlList &controls,bool valid,int32_t score,
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

int IPACamss::mapBuffers(''')
# Source script labels only. Existing known module / SDK paths stay unchanged.
for name in ['build-candidate.py','test-ipa.py','pack-runtime.py','native-capture.py','launch-capture.py','poll-capture.py']:
    p=HERE/name;p.write_text(p.read_text().replace('312','313'))
for model in ['s5kgw1','imx471','imx319','s5k3m5']:
    profile=yaml.safe_load((OLD/(model+'.yaml')).read_text())
    if model=='s5kgw1':profile['autofocus']=yaml.safe_load((HERE.parents[1]/'linux-port/packages/samurai-camera-config/s5kgw1.yaml').read_text())['autofocus']
    (HERE/(model+'.yaml')).write_text('# Experimental IQ references; AF codes are not distance calibration.\n'+yaml.safe_dump(profile,sort_keys=False))
print('Prepared common IPA AF using the existing ContrastAf controller.')
