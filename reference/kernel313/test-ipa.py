"""Exercise the actual built AArch64 IPA with a delayed parameter model."""
from pathlib import Path
import json,shutil,subprocess,yaml
import host
HERE=Path(__file__).resolve().parent
SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
stage=SDK/'private/camss313-contract';stage.mkdir(exist_ok=True)
for name in ['ipa-contract.cpp','imx319.yaml']:shutil.copyfile(HERE/name,stage/name)
shutil.copyfile(HERE.parent/'kernel311/imx319-awb.yaml',stage/'imx319-awb.yaml')
profile=yaml.safe_load((HERE/'imx319.yaml').read_text())
profile['autofocus']=yaml.safe_load((HERE/'s5kgw1.yaml').read_text())['autofocus'];profile['autofocus']['lens']='test-lens'
(stage/'imx319-af.yaml').write_text(yaml.safe_dump(profile,sort_keys=False))
tree='/work/libcamera299-inline'
command=['chroot',str(SDK),'/usr/bin/g++','-std=c++20','-O0','-Wall','-Wextra','-Werror',
 '-DLIBCAMERA_BASE_PRIVATE','-I'+tree+'/include','-I'+tree+'/output/include',
 '/private/camss313-contract/ipa-contract.cpp','-L'+tree+'/output/src/libcamera',
 '-L'+tree+'/output/src/libcamera/base','-Wl,-rpath-link,'+tree+'/output/src/libcamera/base',
 '-lcamera','-lcamera-base','-ldl','-o','/private/camss313-contract/contract']
q=subprocess.run(command,capture_output=True,timeout=180)
(host.PRIVATE/'contract-compile.log').write_bytes(q.stdout+q.stderr)
if q.returncode:print(q.stderr.decode());raise SystemExit(q.returncode)
runs=[]
for profile,extra in [('imx319-awb.yaml',[]),('imx319.yaml',['catalog']),('imx319-af.yaml',['af'])]:
 q=subprocess.run(['chroot',str(SDK),'/usr/bin/env',
  'LD_LIBRARY_PATH='+tree+'/output/src/libcamera:'+tree+'/output/src/libcamera/base',
  '/private/camss313-contract/contract',tree+'/output/src/ipa/camss-vfe/ipa_camss_vfe.so',
  '/private/camss313-contract/'+profile,*extra],capture_output=True,timeout=50)
 (host.PRIVATE/(profile+'-contract.log')).write_bytes(q.stdout+q.stderr)
 runs.append({'profile':profile,'exit_code':q.returncode,'passed':q.returncode==0 and b'AWB_CONTRACT_PASS' in q.stdout})
report={'stage':313,'runs':runs,'actual_ipa_dso':True,'synthetic_statistics':True,
        'independent_parameter_delay':3,'catalog_wrong_timing_rejected':runs[-1]['passed'],'passed':all(r['passed'] for r in runs)}
(HERE/'ipa-contract-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print((q.stdout+q.stderr).decode()[-3500:])
print(json.dumps(report))
raise SystemExit(0 if report['passed'] else 1)
