"""Prepare main-only profiles and the public-control capture/consumer binaries."""
from pathlib import Path
import json,shutil,subprocess,sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');TREE='/work/libcamera321-lsc-built/src/libcamera-v0.7.2'
stage=SDK/'private/camss325-runtime';stage.mkdir(exist_ok=True)
s=(HERE.parent/'kernel324/lsc-smoke.cpp').read_text().replace('if(argc!=6)return 2;','if(argc!=7)return 2;\n int selectedPattern=0;if(std::sscanf(argv[6],"%d",&selectedPattern)!=1 || selectedPattern<=0)return 2;')
s=s.replace('pattern.value=3;','pattern.value=selectedPattern;')
s=s.replace('FrameBufferAllocator allocator(camera);','''v4l2_queryctrl patternInfo{};patternInfo.id=V4L2_CID_TEST_PATTERN;
 if(ioctl(sensor,VIDIOC_QUERYCTRL,&patternInfo))return 6;
 v4l2_querymenu patternName{};patternName.id=V4L2_CID_TEST_PATTERN;patternName.index=selectedPattern;
 if(ioctl(sensor,VIDIOC_QUERYMENU,&patternName))return 6;
 std::cout<<"LSC_PATTERN index="<<selectedPattern<<" maximum="<<patternInfo.maximum<<" name="<<patternName.name<<std::endl;
 FrameBufferAllocator allocator(camera);''')
# Exercise the normal active-PM write path as well as the cached startup value.
s=s.replace('if(camera->start(&initial))return 8;','''if(camera->start(&initial))return 8;
 v4l2_control activePattern{V4L2_CID_TEST_PATTERN,0};
 if(ioctl(sensor,VIDIOC_S_CTRL,&activePattern)){camera->stop();return 8;}
 activePattern.value=selectedPattern;
 if(ioctl(sensor,VIDIOC_S_CTRL,&activePattern)){camera->stop();return 8;}
 std::cout<<"LSC_PATTERN_ACTIVE toggled=1"<<std::endl;''')
same=(stage/'lsc-smoke.cpp').exists() and (stage/'lsc-smoke.cpp').read_text()==s
(HERE/'lsc-smoke.cpp').write_text(s);(stage/'lsc-smoke.cpp').write_text(s)
if '--repack' in sys.argv:assert same and (stage/'lsc-smoke').exists()
else:
 q=subprocess.run(['chroot',str(SDK),'g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-I'+TREE+'/include','-I'+TREE+'/output/include','/private/camss325-runtime/lsc-smoke.cpp',
  '-L'+TREE+'/output/src/libcamera','-L'+TREE+'/output/src/libcamera/base','-Wl,-rpath-link,'+TREE+'/output/src/libcamera/base','-lcamera','-lcamera-base','-pthread','-o','/private/camss325-runtime/lsc-smoke'],capture_output=True)
 (P/'probe-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
profiles=P/'profiles';profiles.mkdir(exist_ok=True)
for name in ['s5kgw1-off','qtech_s5kgw1','sunny_s5kgw1']:
 shutil.copyfile(P.parent/'kernel324/profiles'/(name+'.yaml'),profiles/(name+'.yaml'))
cases={k:dict(**v,test_pattern=2) for k,v in json.loads((HERE.parent/'kernel324/cases.json').read_text()).items() if v['model']=='s5kgw1'}
(HERE/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
(HERE/'probe-build-validation.json').write_text(json.dumps(dict(stage=325,aarch64_tool_built=True,werror=True,uses_installed_ipa=True,explicit_pattern_index=True,active_control_toggle=True,main_cases=len(cases),passed=True),indent=2)+'\n')
print('Prepared public TEST_PATTERN and mode-selectable main LSC probe; IPA unchanged.')
