"""Check immutable proposed state and rerun native results against saved oracle."""
from pathlib import Path
import hashlib, json, shutil, subprocess
import host
HERE=Path(__file__).resolve().parent
P=host.PRIVATE
report=json.loads((HERE/'temporal-validation.json').read_text())
assert report['passed']
sdk=Path('/home/cy122/x2pro-linux/libcamera214-root')
work=sdk/'private/camss408-math'
relative=['kernel408/api-contract.cpp','kernel408/temporal-runner.cpp',
          'kernel408/libipa/ltm_face_smoothing.cpp','kernel408/libipa/ltm_face_smoothing.h',
          'kernel407/libipa/ltm_curves.cpp','kernel407/libipa/ltm_curves.h']
for name in relative:
    target=work/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(HERE.parent/name,target)
inputs=(P/'temporal-input-private.bin').read_bytes()
wanted=(P/'temporal-expected-private.bin').read_bytes()
assert len(inputs)==876*(report['valid_cases']+report['invalid_cases'])
assert len(wanted)==1192*(report['valid_cases']+report['invalid_cases'])
rows=[]
for arch in ['host','aarch64']:
    for kind in ['api-contract','temporal-runner']:
        rels=['kernel408/'+kind+'.cpp','kernel408/libipa/ltm_face_smoothing.cpp','kernel407/libipa/ltm_curves.cpp']
        options=['-std=c++17','-O2','-ffp-contract=fast','-Wall','-Wextra','-Werror']
        if arch=='host':
            binary=P/(kind+'-final-host')
            command=['g++',*options,'-fsanitize=address,undefined','-no-pie',*[str(HERE.parent/r) for r in rels],'-o',str(binary)]
            launch=[str(binary)]
        else:
            binary='/private/camss408-math/'+kind+'-final-aarch64'
            command=['chroot',str(sdk),'g++',*options,*['/private/camss408-math/'+r for r in rels],'-o',binary]
            launch=['chroot',str(sdk),binary]
        q=subprocess.run(command,capture_output=True);assert not q.returncode,q.stderr.decode()
        q=subprocess.run(launch,input=inputs if kind=='temporal-runner' else b'',capture_output=True,timeout=45)
        assert not q.returncode,q.stderr.decode()
        expected=wanted if kind=='temporal-runner' else b''
        assert q.stdout==expected,(arch,kind,sum(a!=b for a,b in zip(q.stdout,expected)))
        rows.append(dict(architecture=arch,scope=kind,passed=True))
        print(json.dumps(rows[-1]),flush=True)
sources=[dict(path=name,sha256=hashlib.sha256((HERE.parent/name).read_bytes()).hexdigest()) for name in relative]
result=dict(stage=408,rows=rows,sources=sources,
            known_history90_output45_before_after_half_attenuation=True,
            positive_negative_lce_history52_5_output26_25=True,
            both_bypass_controls_preserve_state=True,
            null_and_alias_outputs_rejected=True,input_state_alias_rejected=True,
            invalid_exposure_does_not_bypass_validation_in_prepare=True,
            final_native_all3978_saved_oracle_records_zero_difference=True,
            host_asan_ubsan=True,aarch64_sdk_qemu=True,fp_contract_fast=True,
            phone_accessed=False,passed=True)
(HERE/'api-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
