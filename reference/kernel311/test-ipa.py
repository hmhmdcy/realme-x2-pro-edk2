"""Exercise the actual built AArch64 IPA with a delayed parameter model."""
from pathlib import Path
import json,shutil,subprocess
import host
HERE=Path(__file__).resolve().parent
SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
stage=SDK/'private/camss311-contract';stage.mkdir(exist_ok=True)
for name in ['ipa-contract.cpp','imx319-awb.yaml']:shutil.copyfile(HERE/name,stage/name)
tree='/work/libcamera299-inline'
command=['chroot',str(SDK),'/usr/bin/g++','-std=c++20','-O0','-Wall','-Wextra','-Werror',
 '-DLIBCAMERA_BASE_PRIVATE','-I'+tree+'/include','-I'+tree+'/output/include',
 '/private/camss311-contract/ipa-contract.cpp','-L'+tree+'/output/src/libcamera',
 '-L'+tree+'/output/src/libcamera/base','-Wl,-rpath-link,'+tree+'/output/src/libcamera/base',
 '-lcamera','-lcamera-base','-ldl','-o','/private/camss311-contract/contract']
q=subprocess.run(command,capture_output=True,timeout=180)
(host.PRIVATE/'contract-compile.log').write_bytes(q.stdout+q.stderr)
if q.returncode:print(q.stderr.decode());raise SystemExit(q.returncode)
q=subprocess.run(['chroot',str(SDK),'/usr/bin/env',
 'LD_LIBRARY_PATH='+tree+'/output/src/libcamera:'+tree+'/output/src/libcamera/base',
 '/private/camss311-contract/contract',tree+'/output/src/ipa/camss-vfe/ipa_camss_vfe.so',
 '/private/camss311-contract/imx319-awb.yaml'],capture_output=True,timeout=50)
(host.PRIVATE/'contract.log').write_bytes(q.stdout+q.stderr)
report={'stage':311,'exit_code':q.returncode,'actual_ipa_dso':True,'synthetic_statistics':True,
        'independent_parameter_delay':3,'passed':q.returncode==0 and b'AWB_CONTRACT_PASS' in q.stdout}
(HERE/'ipa-contract-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print((q.stdout+q.stderr).decode()[-3500:])
print(json.dumps(report))
raise SystemExit(q.returncode)
