from pathlib import Path
import json,shutil,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;TREE='/work/libcamera/src/libcamera-v0.7.2'
assert not json.loads((HERE/'build-validation.json').read_text())['exit_code']
relative=Path('/private/camss349-contract');stage=storage.SDK/str(relative).lstrip('/');stage.mkdir(exist_ok=True)
shutil.copyfile(HERE/'gamma-contract.cpp',stage/'contract.cpp')
for path in (P/'profiles').glob('*.yaml'):shutil.copyfile(path,stage/path.name)
for name in ['factory-gamma-private.bin','rgb-gamma-private.bin']:shutil.copyfile(P/name,stage/name)
cases=json.loads((P/'cases-private.json').read_text());rows=[]
with storage.sdk_candidate():
 flags=['-std=c++20','-O2','-Wall','-Wextra','-Werror','-I'+TREE+'/include','-I'+TREE+'/output/include']
 links=['-L'+TREE+'/output/src/libcamera','-L'+TREE+'/output/src/libcamera/base','-Wl,-rpath-link,'+TREE+'/output/src/libcamera/base','-lcamera','-lcamera-base','-ldl']
 q=subprocess.run(['chroot',str(storage.SDK),'g++',*flags,str(relative/'contract.cpp'),*links,'-o',str(relative/'contract')],capture_output=True)
 (P/'contract-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
 base=['chroot',str(storage.SDK),'env','LD_LIBRARY_PATH='+TREE+'/output/src/libcamera:'+TREE+'/output/src/libcamera/base',str(relative/'contract'),TREE+'/output/src/ipa/camss-vfe/ipa_camss_vfe.so']
 for case in cases:
  m=case['match'];args=[str(relative/case['profile']),case['model'],*[str(m[k]) for k in ['width','height','pixel_rate','line_length','frame_length']],
   str(case['result']),str(int(case['gamma'])),str(relative/(case['expected'] or 'unused')),str(relative/case['fallback'])]
  q=subprocess.run([*base,*args],capture_output=True,timeout=45)
  serial=1
  while (P/(case['name']+'-contract-r'+str(serial)+'.log')).exists():serial+=1
  (P/(case['name']+'-contract-r'+str(serial)+'.log')).write_bytes(q.stdout+q.stderr)
  if q.returncode:print(q.stderr.decode()[-4500:]);raise RuntimeError(case['name'])
  marker=b'GAMMA_CONFIG_REJECT_PASS' if case['result'] else b'GAMMA_CONTRACT_PASS';assert marker in q.stdout
  rows.append(dict(case=case['name'],expected_configuration_error=case['result'],factory_or_rgb_packet_verified=case['gamma'],passed=True));print(case['name']+' passed',flush=True)
report=dict(stage=349,actual_aarch64_ipa=True,cases=rows,full_native_gamma_block_exact=True,rgb_asymmetric_channels_verified=True,
 gamma_not_reuploaded_on_wb_revision=True,restart_reuploads_gamma=True,reconfigure_legacy_clears_gamma=True,
 no_metadata_before_ack=True,short_parameter_mapping_rejected=True,invalid_configuration_rejected=True,
 default_profiles_changed=False,installed=False,passed=True)
(HERE/'ipa-contract-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(stage=349,cases=len(rows),passed=True)))
