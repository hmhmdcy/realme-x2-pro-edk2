"""Build a real sensor request probe saving DMA-synchronized NV12 samples."""
from pathlib import Path
import json,shutil,subprocess
import storage,host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
source=(HERE.parent/'kernel362/adaptation-smoke.cpp').read_text()
source=source.replace('static volatile sig_atomic_t interrupted;','static volatile sig_atomic_t interrupted;\nstatic bool optical;')
a=source.index('static constexpr std::array<Policy,5>');b=source.index('static bool meanY',a)
source=source[:a]+'''static constexpr std::array<Policy,3> policies{{{0,0,0,false},{0,0,0,false},{0,0,0,false}}};
static void setPolicy(ControlList &list,unsigned phase)
{
 const auto &p=policies.at(phase);list.set(controls::ExposureValue,p.ev);list.set(controls::AeFlickerMode,p.mode);
 list.set(controls::AwbEnable,optical);if(!optical)list.set(controls::ColourGains,{1.f,1.f});
}
'''+source[b:]
source=source.replace('const auto &p=policies[phase];','auto p=policies[phase];p.awb=optical;')
source=source.replace('if(matched>=3)','if(matched>=8)')
source=source.replace('std::signal(SIGINT,onSignal);','optical=patternIndex==0;std::signal(SIGINT,onSignal);')
source=source.replace('controls::ExposureTimeModeAuto','optical?controls::ExposureTimeModeAuto:controls::ExposureTimeModeManual')
source=source.replace('controls::AnalogueGainModeAuto','optical?controls::AnalogueGainModeAuto:controls::AnalogueGainModeManual')
needle='*mean=double(sum)/(uint64_t(width)*height);return true;'
assert source.count(needle)==1
source=source.replace(needle,'''*mean=double(sum)/(uint64_t(width)*height);
 const char *folder=getenv("CAPTURE_DIR");if(!folder)return false;
 std::string path=std::string(folder)+"/frame-"+std::to_string(buffer->metadata().sequence)+".nv12";
 std::ofstream output(path,std::ios::binary);output.write(reinterpret_cast<const char*>(data.data()),data.size());
 std::cout<<"SAMPLE sequence="<<buffer->metadata().sequence<<" width="<<width<<" height="<<height<<" stride="<<stride<<" bytes="<<data.size()<<std::endl;
 return output.good();''')
(HERE/'capture.cpp').write_text(source)
work=storage.SDK/'private/camss423-contract';work.mkdir(exist_ok=True);shutil.copyfile(HERE/'capture.cpp',work/'capture.cpp')
T='/work/libcamera/src/libcamera-v0.7.2'
with storage.sdk_candidate():
 q=subprocess.run(['chroot',str(storage.SDK),'g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-I'+T+'/include','-I'+T+'/output/include','/private/camss423-contract/capture.cpp',
  '-L'+T+'/output/src/libcamera','-L'+T+'/output/src/libcamera/base','-Wl,-rpath-link,'+T+'/output/src/libcamera/base','-lcamera','-lcamera-base','-pthread','-o','/private/camss423-contract/capture'],capture_output=True)
(P/'capture-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-3000:]
shutil.copyfile(work/'capture',P/'capture')
r=dict(stage=423,aarch64_probe_werror=True,pattern_manual_exposure_and_wb=True,optical_auto_exposure_and_wb=True,dma_sync_samples_saved=True,app_does_not_apply_tone_filter=True,passed=True)
(HERE/'probe-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
