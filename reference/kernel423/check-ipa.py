"""Run matching signed IPA3 and its real methods inside the ARM64 SDK."""
from pathlib import Path
import json,shutil,subprocess
import storage,host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;T='/work/libcamera/src/libcamera-v0.7.2'
attempt=1
while (P/('ipa-contract-r'+str(attempt)+'.log')).exists():attempt+=1
assert json.loads((HERE/'build-validation.json').read_text())['passed']
assert json.loads((HERE/'profiles-validation.json').read_text())['passed']
work=storage.SDK/'private/camss423-contract';work.mkdir(exist_ok=True)
shutil.copyfile(HERE/'ipa-contract.cpp',work/'contract.cpp')
for mode in ['factory','gamma-roundtrip','colour-roundtrip','bypass']:
    shutil.copyfile(P/(mode+'-s5kgw1-private.yaml'),work/(mode+'.yaml'))
with storage.sdk_candidate():
    env=['env','LD_LIBRARY_PATH='+T+'/output/src/libcamera:'+T+'/output/src/libcamera/base']
    q=subprocess.run(['chroot',str(storage.SDK),*env,T+'/output/src/apps/ipa-verify/ipa_verify',T+'/output/src/ipa/camss-vfe/ipa_camss_vfe.so'],capture_output=True)
    (P/'signature-check.log').write_bytes(q.stdout+q.stderr);assert not q.returncode and b'IPA module signature is valid' in q.stdout
    q=subprocess.run(['chroot',str(storage.SDK),'g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-I'+T+'/include','-I'+T+'/output/include','/private/camss423-contract/contract.cpp',
        '-L'+T+'/output/src/libcamera','-L'+T+'/output/src/libcamera/base','-Wl,-rpath-link,'+T+'/output/src/libcamera/base','-lcamera','-lcamera-base','-ldl','-pthread','-o','/private/camss423-contract/contract'],capture_output=True)
    (P/'contract-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-4000:]
    rows=[]
    for mode in ['bypass','colour-roundtrip','gamma-roundtrip','factory']:
        q=subprocess.run(['chroot',str(storage.SDK),*env,'/private/camss423-contract/contract',T+'/output/src/ipa/camss-vfe/ipa_camss_vfe.so','/private/camss423-contract/'+mode+'.yaml',mode,'/private/camss423-contract/'+mode+'.bin'],capture_output=True,timeout=40)
        (P/(mode+'-contract.log')).write_bytes(q.stdout+q.stderr)
        with (P/('ipa-contract-r'+str(attempt)+'.log')).open('ab') as log:log.write(mode.encode()+b'\n'+q.stdout+q.stderr)
        print(mode,q.returncode,(q.stdout+q.stderr).decode()[-1600:],flush=True)
        rows.append(dict(mode=mode,exit_code=q.returncode,passed=not q.returncode))
        if not q.returncode and mode!='bypass':shutil.copyfile(work/(mode+'.bin'),P/(mode+'-contract-private.bin'))
        if q.returncode:break
r=dict(stage=423,private_ipa_version=3,signature_verified=True,aarch64_real_ipa_methods=True,simulation_not_hardware=True,architectures=['aarch64-musl-qemu'],modes=rows,passed=len(rows)==4 and all(r['passed'] for r in rows))
(HERE/'ipa-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));assert r['passed']
