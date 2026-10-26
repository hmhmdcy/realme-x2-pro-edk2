"""Retain the bounded 442 application queue and exercise a real AF trigger."""
from pathlib import Path
import hashlib,json,shutil,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;storage.mount.mounted_build()
source=(HERE.parent/'kernel442/capture.cpp').read_text()
def replace(a,b):
 global source
 assert source.count(a)==1,(a,source.count(a));source=source.replace(a,b)
replace('std::array<Policy,1> policies{{{0,0,0,false}}}', 'std::array<Policy,3> policies{{{0,0,0,false},{0,0,0,false},{0,0,0,false}}}')
replace('list.set(controls::AwbEnable,optical);if(!optical)list.set(controls::ColourGains,{1.f,1.f});', '''list.set(controls::AwbEnable,optical);if(!optical)list.set(controls::ColourGains,{1.f,1.f});
 list.set(controls::AfMode,controls::AfModeAuto);if(phase==1)list.set(controls::AfTrigger,controls::AfTriggerStart);''')
replace('unsigned lockedRun=0,lockedTotal=0;', 'unsigned lockedRun=0,lockedTotal=0;bool sawScanning=false;int afTerminal=-1;')
replace('auto matrix=metadata.get(controls::ColourCorrectionMatrix);','''auto matrix=metadata.get(controls::ColourCorrectionMatrix);
  auto afState=metadata.get(controls::AfState);auto focus=metadata.get(controls::FocusFoM);
  if(!draining && phase==1 && afState){if(*afState==controls::AfStateScanning)sawScanning=true;if(sawScanning && (*afState==controls::AfStateFocused || *afState==controls::AfStateFailed))afTerminal=*afState;}''')
replace('<<" kelvin="<<kelvin.value_or(0)', '<<" af-state="<<afState.value_or(-1)<<" focus-fom="<<focus.value_or(-1)<<" kelvin="<<kelvin.value_or(0)')
replace('if(!draining && (matched>=240 || (matched>=24 && lockedRun>=8)))', 'if(!draining && (phase==1 ? (matched>=8 && afTerminal>=0) : (matched>=24 && lockedRun>=8)))')
replace('if(next)setPolicy(request->controls(),phase);','if(next){setPolicy(request->controls(),phase);std::cout<<"AF_POLICY_REQUEST phase="<<phase<<" previous-request="<<request->sequence()<<std::endl;}')
replace('static_cast<const ControlId*>(&controls::AwbEnable)', 'static_cast<const ControlId*>(&controls::AwbEnable),static_cast<const ControlId*>(&controls::AfMode),static_cast<const ControlId*>(&controls::AfTrigger)')
replace('std::chrono::seconds(20)', 'std::chrono::seconds(125)')
replace('std::cout<<"AWB_STEADY_RESULT', 'std::cout<<"AF_TRIGGER_RESULT scanning="<<capture.sawScanning<<" terminal="<<capture.afTerminal<<" focused="<<(capture.afTerminal==controls::AfStateFocused)<<std::endl;\n std::cout<<"AWB_STEADY_RESULT')
(HERE/'af-capture.cpp').write_text(source)
W='/private/camss446-af';work=storage.SDK/W.lstrip('/');work.mkdir(exist_ok=True);shutil.copyfile(HERE/'af-capture.cpp',work/'capture.cpp')
T='/work/libcamera/src/libcamera-v0.7.2'
with storage.sdk_candidate():
 q=subprocess.run(['chroot',str(storage.SDK),'g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-I'+T+'/include','-I'+T+'/output/include',W+'/capture.cpp','-L'+T+'/output/src/libcamera','-L'+T+'/output/src/libcamera/base','-Wl,-rpath-link,'+T+'/output/src/libcamera/base','-lcamera','-lcamera-base','-pthread','-o',W+'/af-capture'],capture_output=True)
(P/'af-probe-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-2500:]
shutil.copyfile(work/'af-capture',P/'af-capture')
r=dict(stage=446,aarch64_werror=True,queued442_app_dispatch_reused=True,scanning_required_before_terminal=True,one_trigger_then_observation=True,deadline_seconds=125,every_frame_saved=True,clients=[dict(name='af-capture',sha256=hashlib.sha256((P/'af-capture').read_bytes()).hexdigest(),source_sha256=hashlib.sha256(source.encode()).hexdigest())],passed=True)
(HERE/'af-client-build-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
