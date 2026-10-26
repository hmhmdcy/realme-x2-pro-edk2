from pathlib import Path
import json,shutil,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');TREE='/work/libcamera335-ccm-built/src/libcamera-v0.7.2'
s=(HERE.parent/'kernel332/cct-smoke.cpp').read_text()
s=s.replace(' if(argc!=8)return 2;',' if(argc!=7)return 2;')
s=s.replace(' int expected=0;std::ifstream expectedFile(argv[7]);if(!(expectedFile>>expected)||expected<1500||expected>12000)return 2;','')
s=s.replace('capture.targets=std::vector<int>{expected,-1}','capture.targets=std::vector<int>{-1}')
s=s.replace('  auto temperature=request->metadata().get(controls::ColourTemperature);','')
s=s.replace('  const bool applied=target>0 ? temperature==target && awb==false : temperature.has_value() && awb==true && locked==true;', '  const bool applied=awb==true && locked==true;')
s=s.replace('"CCT_FRAME sequence="','"AWB_FRAME sequence="').replace('<<" metadata="<<temperature.value_or(0)','')
s=s.replace('camera->controls().find(&controls::ColourTemperature)!=camera->controls().end()','camera->controls().find(&controls::AwbEnable)!=camera->controls().end() && camera->controls().at(&controls::AwbEnable).max().get<bool>()')
s=s.replace('"CCT_CONTROL supported="','"AWB_CONTROL supported="').replace('"CCT_RESULT frames="','"AWB_RESULT frames="')
s=s.replace(' initial.set(controls::AwbEnable,false);',' initial.set(controls::AwbEnable,true);')
s=s.replace('"-"+std::to_string(capture.targets[i])+"-private.nv12"','"-awb-private.nv12"')
(HERE/'awb-grid-smoke.cpp').write_text(s);stage=SDK/'private/camss338-runtime';stage.mkdir(exist_ok=True);shutil.copyfile(HERE/'awb-grid-smoke.cpp',stage/'awb-grid-smoke.cpp')
q=subprocess.run(['chroot',str(SDK),'g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-I'+TREE+'/include','-I'+TREE+'/output/include','/private/camss338-runtime/awb-grid-smoke.cpp',
 '-L'+TREE+'/output/src/libcamera','-L'+TREE+'/output/src/libcamera/base','-Wl,-rpath-link,'+TREE+'/output/src/libcamera/base','-lcamera','-lcamera-base','-pthread','-o','/private/camss338-runtime/awb-grid-smoke'],capture_output=True)
(P/'awb-probe-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
(HERE/'awb-probe-build-validation.json').write_text(json.dumps(dict(stage=338,uses_installed_core_and_ipa=True,internal_test_pattern=True,automatic_awb_locked_and_stable_image_end_condition=True,passed=True),indent=2)+'\n')
print('Built focused installed-IPA AWB convergence capture for the changed grid.')
