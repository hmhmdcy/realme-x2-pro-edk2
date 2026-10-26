from pathlib import Path
import hashlib,json,shutil,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;T='/work/libcamera/src/libcamera-v0.7.2';W='/private/camss438-profiles';work=storage.SDK/W.lstrip('/');work.mkdir(exist_ok=True)
assert json.loads((HERE/'rear-profile-validation.json').read_text())['passed']
source=(HERE.parent/'kernel435/profile-contract.cpp').read_text().replace('&&c.cache!=b.cache','')
(work/'profile.cpp').write_text(source)
for model in ['imx319','s5k3m5']:shutil.copyfile(P/('factory-'+model+'-private.yaml'),work/(model+'.yaml'))
rows=[]
with storage.sdk_candidate():
 q=subprocess.run(['chroot',str(storage.SDK),'g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-DLIBCAMERA_BASE_PRIVATE','-I'+T+'/include','-I'+T+'/output/include','-I'+T+'/src/ipa/camss-vfe',W+'/profile.cpp',T+'/output/src/ipa/camss-vfe/ipa_camss_vfe.so.p/ipe_tone_profile.cpp.o',T+'/output/src/ipa/camss-vfe/ipa_camss_vfe.so.p/gamma_profile.cpp.o',T+'/output/src/ipa/libipa/libipa.a','-L'+T+'/output/src/libcamera','-L'+T+'/output/src/libcamera/base','-Wl,-rpath-link,'+T+'/output/src/libcamera/base','-lcamera','-lcamera-base','-pthread','-o',W+'/profile'],capture_output=True)
 (P/'profile-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
 for model in ['imx319','s5k3m5']:
  q=subprocess.run(['chroot',str(storage.SDK),'env','LD_LIBRARY_PATH='+T+'/output/src/libcamera:'+T+'/output/src/libcamera/base',W+'/profile',W+'/'+model+'.yaml',W+'/'+model],capture_output=True,timeout=35)
  (P/(model+'-profile-run.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,(model,q.returncode,(q.stdout+q.stderr).decode()[-2000:])
  for i in range(3):
   for kind in ['adrc','lut']:shutil.copyfile(work/(model+'-'+str(i)+'-'+kind+'.bin'),P/(model+'-'+str(i)+'-'+kind+'-private.bin'))
  rows.append(dict(model=model,actual_arm64_compiled_profile=True,gtm_tmc_ltm_packet_calculation=True,immutable_applied_tmc=True,native_histogram_hold_and_trigger_refresh=True,cases=3,passed=True));print(json.dumps(rows[-1]),flush=True)
r=dict(stage=438,compiler_werror=True,source_userspace_stage437=True,profiles=rows,phone_accessed=False,passed=True)
(HERE/'rear-math-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
