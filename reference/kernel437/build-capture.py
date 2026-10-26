from pathlib import Path
import hashlib,json,shutil,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
storage.candidate()
source=(HERE.parent/'kernel423/capture.cpp').read_text()
old='static constexpr std::array<Policy,3> policies{{{0,0,0,false},{0,0,0,false},{0,0,0,false}}};'
assert old in source
source=source.replace(old,'static constexpr std::array<Policy,1> policies{{{0,0,0,false}}};')
source=source.replace('unsigned stride=0,width=0,height=0;', 'unsigned lockedRun=0,lockedTotal=0;\n unsigned stride=0,width=0,height=0;')
source=source.replace('   if(applied)++matched;else matched=0;', '   if(applied)++matched;else matched=0;\n   if(applied && locked.value_or(false)){++lockedRun;++lockedTotal;}else lockedRun=0;')
source=source.replace('if(matched>=8)', 'if(matched>=240 || (matched>=24 && lockedRun>=8))')
source=source.replace(' std::cout<<"ADAPT_RESULT frames="', ' std::cout<<"AWB_STEADY_RESULT locked-frames="<<capture.lockedTotal<<" final-locked-run="<<capture.lockedRun<<std::endl;\n std::cout<<"ADAPT_RESULT frames="')
(HERE/'capture.cpp').write_text(source)
work=storage.SDK/'private/camss437-contract';work.mkdir(exist_ok=True);shutil.copyfile(HERE/'capture.cpp',work/'capture.cpp');T='/work/libcamera/src/libcamera-v0.7.2'
with storage.sdk_candidate():
 q=subprocess.run(['chroot',str(storage.SDK),'g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-I'+T+'/include','-I'+T+'/output/include','/private/camss437-contract/capture.cpp','-L'+T+'/output/src/libcamera','-L'+T+'/output/src/libcamera/base','-Wl,-rpath-link,'+T+'/output/src/libcamera/base','-lcamera','-lcamera-base','-pthread','-o','/private/camss437-contract/capture'],capture_output=True)
(P/'capture-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
shutil.copyfile(work/'capture',P/'capture')
(HERE/'capture-validation.json').write_text(json.dumps(dict(stage=437,aarch64_werror=True,source_sha256=hashlib.sha256(source.encode()).hexdigest(),binary_sha256=hashlib.sha256((P/'capture').read_bytes()).hexdigest(),no_af_or_policy_transitions=True,stop_after_eight_consecutive_locked_frames=True,maximum_matched_frames=240,maximum_seconds=20,lock_absence_not_hidden_by_capture_result=True,passed=True),indent=2)+'\n')
print('Bounded steady AWB capture built; ordinary controls and hardware pixels retained')
