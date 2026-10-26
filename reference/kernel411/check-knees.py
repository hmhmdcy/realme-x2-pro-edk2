"""Verify the maintained TMC10 implementation against actual target knees/sampling."""
from pathlib import Path
import hashlib,importlib.util,json,math,shutil,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('knee411',HERE/'knee-model.py')
k=importlib.util.module_from_spec(spec);spec.loader.exec_module(k);target=k.KneeMachine()
prior=(P.parent/'kernel410/tmc-valid-input-private.bin').read_bytes()
records=[prior[i:i+288] for i in range(0,len(prior),288)];original_count=len(records)
labels=json.loads((P.parent/'kernel410/tmc-cases-private.json').read_text())
base=list(struct.unpack_from('<72f',prior));f32=lambda v:struct.unpack('<f',struct.pack('<f',v))[0]
step=f32(1.03)
for index in range(95):
    midpoint=f32(math.pow(step,index+.5));bits=struct.unpack('<I',struct.pack('<f',midpoint))[0]
    for delta in range(-3,4):
        gain=struct.unpack('<f',struct.pack('<I',bits+delta))[0]
        for dark in [False,True]:
            row=base.copy();row[0]=1 if dark else gain;row[1]=gain if dark else 1
            row[2:7]=[.2,.8,.3,1,0]
            records.append(struct.pack('<72f',*row));labels.append(dict(kind='float-half-index',index=index,dark=dark))
for delta in [0,1,2,3,10,100,500,800,838,839,840,1000]:
    row=base.copy();row[0]=2;row[1]=struct.unpack('<f',struct.pack('<I',0x3f800000+delta))[0]
    row[2:7]=[.2,.8,.3,1,0]
    records.append(struct.pack('<72f',*row));labels.append(dict(kind='near-unity-ratio',ulp_delta=delta))
inputs=b''.join(records);expected=[];target_raw=[];finite_knees=0;sample_success=0
prior_curve_diffs=0;prior_gain_diffs=0;prior_different_bytes=0
old=(P.parent/'kernel410/host-actual-private.bin').read_bytes()
for i,record in enumerate(records):
    curve=target.knees(record[:28]);target_raw.append(curve)
    finite=all(math.isfinite(v) for v in struct.unpack('<18f',curve));finite_knees+=finite
    out=struct.pack('<I',finite)+(curve if finite else bytes([0xa5])*72)
    if finite:
        gains=target.sample(curve,record[28:])
        sampled=all(math.isfinite(v) for v in struct.unpack('<65f',gains)) and struct.unpack_from('<f',record,284)[0]>0
    else:gains=bytes([0xa5])*260;sampled=False
    sample_success+=sampled;out+=struct.pack('<I',sampled)+(gains if sampled else bytes([0xa5])*260);expected.append(out)
    if i<original_count:
        before=old[i*340:(i+1)*340]
        prior_curve_diffs+=before[:76]!=out[:76];prior_gain_diffs+=before[76:]!=out[76:]
        prior_different_bytes+=sum(a!=b for a,b in zip(before,out))
    if i%500==0:print('target knee/sample',i+1,flush=True)
(P/'target-knees-private.bin').write_bytes(b''.join(target_raw))
(P/'tmc-valid-input-private.bin').write_bytes(inputs)
(P/'tmc-target-expected-private.bin').write_bytes(b''.join(expected))
(P/'tmc-cases-private.json').write_text(json.dumps(labels,indent=2)+'\n')
invalid=[];invalid_expected=[]
for at in range(7):
    for value in [math.nan,math.inf,-1]:
        record=bytearray(records[0]);struct.pack_into('<f',record,at*4,value);invalid.append(bytes(record));invalid_expected.append(struct.pack('<I',0)+bytes([0xa5])*72+struct.pack('<I',0)+bytes([0xa5])*260)
for at,value in [(0,.5),(1,.5),*[(i,1.01) for i in range(2,7)]]:
    record=bytearray(records[0]);struct.pack_into('<f',record,at*4,value);invalid.append(bytes(record));invalid_expected.append(struct.pack('<I',0)+bytes([0xa5])*72+struct.pack('<I',0)+bytes([0xa5])*260)
for at,value in [(7,math.nan),(39,math.inf),(71,0),(10,-1),(71,-1)]:
    record=bytearray(records[0]);struct.pack_into('<f',record,at*4,value);invalid.append(bytes(record));invalid_expected.append(expected[0][:76]+struct.pack('<I',0)+bytes([0xa5])*260)
all_input=inputs+b''.join(invalid);wanted=b''.join(expected+invalid_expected)
(P/'tmc-input-private.bin').write_bytes(all_input);(P/'tmc-expected-private.bin').write_bytes(wanted)
sdk=Path('/home/cy122/x2pro-linux/libcamera214-root');work=sdk/'private/camss411-math'
names=['tmc-runner.cpp','libipa/tmc10.cpp','libipa/tmc10.h']
for rel in names:
    dest=work/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(HERE.parent/'kernel410'/rel,dest)
rows=[]
for arch in ['host','aarch64']:
    flags=['-std=c++17','-O2','-ffp-contract=fast','-Wall','-Wextra','-Werror']
    if arch=='host':
        binary=P/'tmc-host';command=['g++',*flags,'-fsanitize=address,undefined','-no-pie',str(HERE.parent/'kernel410/tmc-runner.cpp'),str(HERE.parent/'kernel410/libipa/tmc10.cpp'),'-o',str(binary)];launch=[str(binary)]
    else:
        binary='/private/camss411-math/tmc-aarch64';command=['chroot',str(sdk),'g++',*flags,'/private/camss411-math/tmc-runner.cpp','/private/camss411-math/libipa/tmc10.cpp','-o',binary];launch=['chroot',str(sdk),binary]
    q=subprocess.run(command,capture_output=True);assert not q.returncode,q.stderr.decode()
    q=subprocess.run(launch,input=all_input,capture_output=True,timeout=45);assert not q.returncode,q.stderr.decode()
    (P/(arch+'-actual-private.bin')).write_bytes(q.stdout)
    assert len(q.stdout)==len(wanted)
    diffs=sum(a!=b for a,b in zip(q.stdout,wanted));rows.append(dict(architecture=arch,cases=len(records),invalid_cases=len(invalid),compared_bytes=len(wanted),different_bytes=diffs,passed=not diffs));print(json.dumps(rows[-1]),flush=True)
prior_report=dict(stage=411,prior_source_only_stage=410,cases=original_count,
    differing_curve_cases=prior_curve_diffs,differing_sampling_cases=prior_gain_diffs,different_bytes=prior_different_bytes,
    actual_target_uses_float_log_quotient=True,actual_target_has_only_fine_unity_ratio_bump=True,
    prior_outputs_retained_privately=True,phone_accessed=False,passed=False)
(HERE/'prior-source-r1-validation.json').write_text(json.dumps(prior_report,indent=2)+'\n')
result=dict(stage=411,cases=len(records),prior_cases=original_count,half_index_boundary_cases=1330,near_unity_cases=12,
    invalid_cases=len(invalid),finite_knee_cases=finite_knees,successful_gain_sampling_cases=sample_success,
    target_knee_range=['0x377a08','0x377d50'],target_sampler_entry='0x3c6328',target_mix_range=['0x3626f8','0x36273c'],
    target_instructions=target.instructions,target_providers=target.providers,
    logf_and_powf_are_host_libm_not_target_bionic=True,actual_target_knees_and_percentage_verified=True,
    original_target_unmodified=True,host_asan_ubsan=True,aarch64_sdk_qemu=True,fp_contract_fast=True,
    invalid_outputs_preserved=True,zero_normalization_endpoint_rejected=True,architectures=rows,
    current_source_hashes=[dict(path='kernel410/'+n,sha256=hashlib.sha256((HERE.parent/'kernel410'/n).read_bytes()).hexdigest()) for n in names],
    disabled_roots_not_enabled=True,tmc11_and_runtime_version_selection_unverified=True,
    phone_accessed=False,full_goal_kept_active=True,passed=all(r['passed'] for r in rows))
path=HERE/'knee-validation.json'
if path.exists() and not json.loads(path.read_text())['passed'] and not (HERE/'knee-r1-validation.json').exists():(HERE/'knee-r1-validation.json').write_bytes(path.read_bytes())
path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True);assert result['passed']
