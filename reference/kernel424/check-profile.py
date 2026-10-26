"""Test the actual compiled profile and reproduce the former wrong-domain calculation."""
from pathlib import Path
import json,re,shutil,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;T='/work/libcamera/src/libcamera-v0.7.2';W='/private/camss424-contract'
assert json.loads((HERE/'build-validation.json').read_text())['passed']
storage.candidate()
work=storage.SDK/W.lstrip('/');work.mkdir(exist_ok=True);shutil.copyfile(HERE/'profile-contract.cpp',work/'profile.cpp')
shutil.copyfile(P.parent/'kernel423/factory-s5kgw1-private.yaml',work/'factory.yaml')
wrong=(HERE/'ipe_tone_profile.cpp').read_text().replace('in.curves.exposureIndex = frame.luxIndex;','in.curves.exposureIndex = frame.exposureIndex;').replace('history.ltmLuxIndex : frame.luxIndex','history.ltmLuxIndex : frame.exposureIndex').replace('state.ltmLuxIndex = frame.luxIndex','state.ltmLuxIndex = frame.exposureIndex')
(work/'wrong.cpp').write_text(wrong)
rows=[]
with storage.sdk_candidate():
 env=['env','LD_LIBRARY_PATH='+T+'/output/src/libcamera:'+T+'/output/src/libcamera/base']
 for kind in ['actual','wrong-domain-counterexample']:
  obj=T+'/output/src/ipa/camss-vfe/ipa_camss_vfe.so.p/ipe_tone_profile.cpp.o' if kind=='actual' else W+'/wrong.cpp'
  args=['chroot',str(storage.SDK),'g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-DLIBCAMERA_BASE_PRIVATE','-I'+T+'/include','-I'+T+'/output/include','-I'+T+'/src/ipa/camss-vfe',W+'/profile.cpp',obj,
   T+'/output/src/ipa/camss-vfe/ipa_camss_vfe.so.p/gamma_profile.cpp.o',T+'/output/src/ipa/libipa/libipa.a',
   '-L'+T+'/output/src/libcamera','-L'+T+'/output/src/libcamera/base','-Wl,-rpath-link,'+T+'/output/src/libcamera/base','-lcamera','-lcamera-base','-pthread','-o',W+'/'+kind]
  q=subprocess.run(args,capture_output=True);(P/(kind+'-profile-build.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-2500:]
  q=subprocess.run(['chroot',str(storage.SDK),*env,W+'/'+kind,W+'/factory.yaml'],capture_output=True,timeout=30)
  (P/(kind+'-profile-run.log')).write_bytes(q.stdout+q.stderr);print(kind,q.returncode,(q.stdout+q.stderr).decode()[-1800:],flush=True)
  changed=int(re.search(rb'PHYSICAL_INDEX_DIFFERENCE bytes=(\d+)',q.stderr)[1])
  if kind=='actual':
   assert not q.returncode and changed==0
   split=re.search(rb'TMC_GTM_SPLIT enabled=(\d+) nonzero-fraction=(\d+)',q.stdout);assert split
   gtm_enabled=bool(int(split[1]));gtm_fraction_nonzero=bool(int(split[2]))
  else:assert q.returncode==-6 and changed>0
  rows.append(dict(kind=kind,exit_code=q.returncode,physical_coordinate_only_different_bytes=changed))
r=dict(stage=424,actual_compiled_ipe_tone_profile_object_tested=True,aarch64_sdk_qemu=True,rows=rows,
 lux_history_controls_attenuation=True,physical_exposure_coordinate_does_not_change_ltm=True,
 next_history_stores_lux=True,first_calculation_previous_equals_current=True,input_and_failure_output_preserved=True,
 old_domain_counterexample_reproduced=True,passed=True)
r.update(actual_factory_example_gtm_enabled=gtm_enabled,actual_factory_example_gtm_fraction_nonzero=gtm_fraction_nonzero,gtm_hardware_application_not_claimed=True)
(HERE/'profile-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
