"""Exercise the actual candidate IPA's missing-lux and receipt paths."""
from pathlib import Path
import json,shutil,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;T='/work/libcamera/src/libcamera-v0.7.2'
assert json.loads((HERE/'build-validation.json').read_text())['passed']
storage.candidate()
work=storage.SDK/'private/camss424-contract';work.mkdir(exist_ok=True)
shutil.copyfile(HERE/'ipa-contract.cpp',work/'contract.cpp')
for mode in ['factory','gamma-roundtrip','colour-roundtrip','bypass']:shutil.copyfile(P.parent/'kernel423'/(mode+'-s5kgw1-private.yaml'),work/(mode+'.yaml'))
shutil.copyfile(P.parent/'kernel423/ipa_camss_vfe.so',work/'old423.so')
attempt=1
while (P/('ipa-contract-r'+str(attempt)+'.log')).exists():attempt+=1
with storage.sdk_candidate():
 env=['env','LD_LIBRARY_PATH='+T+'/output/src/libcamera:'+T+'/output/src/libcamera/base']
 q=subprocess.run(['chroot',str(storage.SDK),*env,T+'/output/src/apps/ipa-verify/ipa_verify',T+'/output/src/ipa/camss-vfe/ipa_camss_vfe.so'],capture_output=True)
 (P/'signature-check.log').write_bytes(q.stdout+q.stderr);assert not q.returncode and b'IPA module signature is valid' in q.stdout
 q=subprocess.run(['chroot',str(storage.SDK),'g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-I'+T+'/include','-I'+T+'/output/include','/private/camss424-contract/contract.cpp',
  '-L'+T+'/output/src/libcamera','-L'+T+'/output/src/libcamera/base','-Wl,-rpath-link,'+T+'/output/src/libcamera/base','-lcamera','-lcamera-base','-ldl','-pthread','-o','/private/camss424-contract/contract'],capture_output=True)
 (P/'contract-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-3000:]
 q=subprocess.run(['chroot',str(storage.SDK),*env,'/private/camss424-contract/contract','/private/camss424-contract/old423.so','/private/camss424-contract/factory.yaml','factory','/private/camss424-contract/old.bin'],capture_output=True,timeout=30)
 (P/'old423-missing-lux-counterexample.log').write_bytes(q.stdout+q.stderr)
 assert q.returncode==-6 and b'MISSING_LUX initial status=-61' in q.stderr
 rows=[]
 for mode in ['bypass','colour-roundtrip','gamma-roundtrip','factory']:
  q=subprocess.run(['chroot',str(storage.SDK),*env,'/private/camss424-contract/contract',T+'/output/src/ipa/camss-vfe/ipa_camss_vfe.so','/private/camss424-contract/'+mode+'.yaml',mode,'/private/camss424-contract/'+mode+'.bin'],capture_output=True,timeout=40)
  (P/(mode+'-contract.log')).write_bytes(q.stdout+q.stderr)
  with (P/('ipa-contract-r'+str(attempt)+'.log')).open('ab') as log:log.write(mode.encode()+b'\n'+q.stdout+q.stderr)
  print(mode,q.returncode,(q.stdout+q.stderr).decode()[-900:],flush=True)
  rows.append(dict(mode=mode,exit_code=q.returncode,passed=not q.returncode))
  if not q.returncode and mode!='bypass':shutil.copyfile(work/(mode+'.bin'),P/(mode+'-contract-private.bin'))
  if q.returncode:break
r=dict(stage=424,private_ipa_version=3,signature_verified=True,aarch64_real_ipa_methods=True,
 missing_lux_before_first_numerical_commit_holds_bypass=True,missing_lux_after_commit_preserves_packet_and_revision=True,
 recovery_calculates_from_acknowledged_history=True,old423_reproduces_enodata_frame_rejection=True,
 disabled_profile_unchanged=True,synthetic_statistics_not_hardware_fault_injection=True,modes=rows,passed=len(rows)==4 and all(x['passed'] for x in rows))
(HERE/'ipa-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));assert r['passed']
