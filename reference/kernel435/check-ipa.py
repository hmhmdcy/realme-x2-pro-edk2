"""Execute the actual ARM64 IPA5 and profile object, including legacy paths."""
from pathlib import Path
import hashlib,importlib.util,json,shutil,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;tree=storage.candidate()/'src/libcamera-v0.7.2';T='/work/libcamera/src/libcamera-v0.7.2';W='/private/camss435-contract';work=storage.SDK/W.lstrip('/');work.mkdir(exist_ok=True)
assert json.loads((HERE/'build-validation.json').read_text())['passed']
attempt=1
while (P/('contract-r'+str(attempt)+'-private.json')).exists():attempt+=1
record=P/('contract-r'+str(attempt)+'-private.json');record.write_text(json.dumps(dict(terminal=False,passed=False))+'\n')
original=(HERE.parent/'kernel431/ipa-contract.cpp').read_text();(work/'legacy.cpp').write_text(original)
prefix=original.split(' uint32_t bytes=0;')[0].replace('constexpr uint32_t used=','constexpr uint32_t baseUsed=').replace('used-sizeof(*envelope)','baseUsed-sizeof(*envelope)')
(work/'gtm.cpp').write_text(prefix+(HERE/'gtm-contract-body.cpp').read_text())
shutil.copyfile(HERE/'profile-contract.cpp',work/'profile.cpp')
for name,path in [('factory',P/'factory-s5kgw1-private.yaml'),('legacy',P.parent/'kernel431/factory-s5kgw1-private.yaml'),('bypass',P.parent/'kernel423/bypass-s5kgw1-private.yaml')]:shutil.copyfile(path,work/(name+'.yaml'))
rows=[]
with storage.sdk_candidate():
 env=['env','LD_LIBRARY_PATH='+T+'/output/src/libcamera:'+T+'/output/src/libcamera/base']
 for name,source in [('legacy','legacy.cpp'),('gtm','gtm.cpp'),('profile','profile.cpp')]:
  command=['chroot',str(storage.SDK),'g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-DLIBCAMERA_BASE_PRIVATE','-I'+T+'/include','-I'+T+'/output/include','-I'+T+'/src/ipa/camss-vfe',W+'/'+source]
  if name=='profile':command += [T+'/output/src/ipa/camss-vfe/ipa_camss_vfe.so.p/ipe_tone_profile.cpp.o',T+'/output/src/ipa/camss-vfe/ipa_camss_vfe.so.p/gamma_profile.cpp.o',T+'/output/src/ipa/libipa/libipa.a']
  command += ['-L'+T+'/output/src/libcamera','-L'+T+'/output/src/libcamera/base','-Wl,-rpath-link,'+T+'/output/src/libcamera/base','-lcamera','-lcamera-base','-ldl','-pthread','-o',W+'/'+name]
  q=subprocess.run(command,capture_output=True);(P/(name+'-contract-r'+str(attempt)+'-build-private.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,(name,q.stderr.decode()[-2500:])
 for name,arguments in [('legacy-factory',[W+'/legacy',T+'/output/src/ipa/camss-vfe/ipa_camss_vfe.so',W+'/legacy.yaml','factory',W+'/legacy.bin']),('legacy-bypass',[W+'/legacy',T+'/output/src/ipa/camss-vfe/ipa_camss_vfe.so',W+'/bypass.yaml','bypass',W+'/bypass.bin']),('profile',[W+'/profile',W+'/factory.yaml',W+'/profile']),('gtm',[W+'/gtm',T+'/output/src/ipa/camss-vfe/ipa_camss_vfe.so',W+'/factory.yaml','factory',W+'/gtm.bin'])]:
  q=subprocess.run(['chroot',str(storage.SDK),*env,*arguments],capture_output=True,timeout=45);(P/(name+'-contract-r'+str(attempt)+'-run-private.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,(name,q.returncode,(q.stdout+q.stderr).decode()[-3500:]);rows.append(dict(test=name,passed=True));print(json.dumps(rows[-1]),flush=True)
 for i in range(3):
  for kind in ['adrc','lut']:shutil.copyfile(work/('profile-'+str(i)+'-'+kind+'.bin'),P/('profile-'+str(i)+'-'+kind+'-private.bin'))
r=dict(stage=435,private_ipa_version=5,actual_ipa_sha256=hashlib.sha256((P/'ipa_camss_vfe.so').read_bytes()).hexdigest(),actual_arm64_ipa_module_and_profile_object=True,contracts=rows,compiler_werror=True,submission_not_physical_ack=True,bootstrap_no_numeric_commit=True,original_gtm_share_nonzero=True,native_histogram_hold_and_refresh=True,immutable_applied_tmc_used_for_ltm=True,ipe_failure_keeps_applied_ife=True,incompatible_gtm_hold_rejected=True,matching_gtm_hold_kept=True,requested_controls_waiting_for_gtm_can_recover=True,waiting_controls_suppress_new_auto_isp_proposal=True,legacy_profiles_compatible=True,statistics_synthetic_not_hardware=True,phone_accessed=False,passed=True)
(HERE/'ipa-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
record.write_text(json.dumps(dict(terminal=True,**r),indent=2)+'\n')
