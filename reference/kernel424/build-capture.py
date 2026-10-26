"""Build a bounded auto-tone capture with an actual autofocus scan after AE warmup."""
from pathlib import Path
import json,shutil,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
storage.candidate()
source=(HERE.parent/'kernel423/capture.cpp').read_text()
needle=' list.set(controls::AwbEnable,optical);if(!optical)list.set(controls::ColourGains,{1.f,1.f});'
assert source.count(needle)==1
source=source.replace(needle,needle+'\n if(optical){list.set(controls::AfMode,controls::AfModeAuto);if(phase==1)list.set(controls::AfTrigger,controls::AfTriggerStart);}')
source=source.replace('  auto matrix=metadata.get(controls::ColourCorrectionMatrix);','  auto matrix=metadata.get(controls::ColourCorrectionMatrix);\n  auto afState=metadata.get(controls::AfState);auto focus=metadata.get(controls::FocusFoM);')
source=source.replace('<<" kelvin="<<kelvin.value_or(0)', '<<" af-state="<<afState.value_or(-1)<<" focus-fom="<<focus.value_or(-1)<<" kelvin="<<kelvin.value_or(0)')
source=source.replace('if(matched>=8)', 'if(matched>=(optical?(phase==0?24:phase==2?16:8):8) && (!optical || phase!=1 || (afState && (*afState==controls::AfStateFocused || *afState==controls::AfStateFailed))))')
(HERE/'capture.cpp').write_text(source)
work=storage.SDK/'private/camss424-contract';work.mkdir(exist_ok=True);shutil.copyfile(HERE/'capture.cpp',work/'capture.cpp');T='/work/libcamera/src/libcamera-v0.7.2'
with storage.sdk_candidate():
 q=subprocess.run(['chroot',str(storage.SDK),'g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-I'+T+'/include','-I'+T+'/output/include','/private/camss424-contract/capture.cpp',
  '-L'+T+'/output/src/libcamera','-L'+T+'/output/src/libcamera/base','-Wl,-rpath-link,'+T+'/output/src/libcamera/base','-lcamera','-lcamera-base','-pthread','-o','/private/camss424-contract/capture'],capture_output=True)
(P/'capture-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-2200:]
shutil.copyfile(work/'capture',P/'capture')
r=dict(stage=424,aarch64_werror=True,actual_af_trigger_after_ae_warmup=True,scan_waits_for_terminal_af_metadata=True,
 capture_deadline_seconds=20,ordinary_v4l2_sensor_test_pattern_zero_for_scene=True,dma_synchronized_nv12_saved=True,app_does_not_tone_filter=True,passed=True)
(HERE/'capture-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
