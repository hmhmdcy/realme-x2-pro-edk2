"""Compare native TMC11 state/version, IPE transport, and LTM selection gates."""
from pathlib import Path
import hashlib,importlib.util,itertools,json,math,random,shutil,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);out=importlib.util.module_from_spec(spec);spec.loader.exec_module(out);return out
policy=module('policy415',HERE/'policy-model.py').PolicyMachine()
metadata=module('metadata415',HERE/'metadata-model.py').MetadataMachine()
rng=random.Random(415);f32=lambda v:struct.unpack('<f',struct.pack('<f',v))[0]
records=[];wanted=[];kinds=[]
def add_policy(words,old,new,kind):
    record=struct.pack('<10I12f',*words,*old,*new);out,n=policy.policy(record)
    records.append(record);wanted.append(struct.pack('<I',1)+out);kinds.append(dict(kind=kind,instructions=n))
for i,(enable,cache,prior,force,locks) in enumerate(itertools.product([0,1,2],[0,1,2],[0,1,2],[0,1,2],[(0,0),(1,0),(0,1),(1,1),(2,2)])):
    words=[63,enable,63 if cache==1 else 62,int(cache!=0),prior,force,*locks,i%2,(i//2)%2]
    old=[1]*6;new=[1]*6
    if i%3:new[i%6]=2
    add_policy(words,old,new,'native-state-cache-force-lock-matrix')
matrix_count=len(records)
factory=0
for variant in ['qtech_s5kgw1','sunny_s5kgw1','sunny_imx471','qtech_s5k3m5sx','sunny_imx319']:
    for root in json.loads((P.parent/'kernel412'/(variant+'-tmc11-trees-private.json')).read_text()):
        for lock in [0,1]:
            add_policy([root['uid'],root['enabled'],root['uid']+1,1,1,0,lock,lock,1,0],
                       [1]*6,[2,1.2,2,50,3,4],'factory-root-enable-and-lock');factory+=1
# Threshold cases around the original double constant1e-9 and signed zero.
eps=f32(1e-9);bits=struct.unpack('<I',struct.pack('<f',eps))[0]
values=[0.,-0.,struct.unpack('<f',struct.pack('<I',1))[0],eps,
        struct.unpack('<f',struct.pack('<I',bits-1))[0],struct.unpack('<f',struct.pack('<I',bits+1))[0],1e30,-1e30]
for axis,value,force,hp in itertools.product(range(6),values,[0,1],[0,1]):
    old=[0.]*6;new=[0.]*6;new[axis]=value
    add_policy([63,1,63,1,1,force,0,0,hp,1],old,new,'trigger-threshold-and-forced-histogram-retention')
valid=len(records);invalid=[]
for offset,fmt,value in [(12,'I',2),(24,'I',256),(28,'I',256),(32,'I',2),(36,'I',2),
                          (40,'f',math.nan),(64,'f',math.inf)]:
    raw=bytearray(records[0]);struct.pack_into('<'+fmt,raw,offset,value);invalid.append(bytes(raw))
inputs=b''.join(records+invalid);gold=b''.join(wanted)+(struct.pack('<I',0)+bytes([0xa5])*56)*len(invalid)
datasets={'policy':(inputs,gold)}
(P/'policy-cases-private.json').write_text(json.dumps(kinds,indent=2)+'\n')
ltm_records=[];ltm_wanted=[];own=0
for words in itertools.product([0,1],[0,1,2],[0,1,2],[0,1,2,0xffffffff],[0,1],[0,1,2,0xffffffff],[0,1]):
    record=struct.pack('<7I',*words);out,n=metadata.ltm(record)
    ltm_records.append(record);ltm_wanted.append(struct.pack('<I',1)+out);own+=struct.unpack_from('<I',out)[0]==0
ltm_count=len(ltm_records);ltm_invalid=[]
for offset in [0,16,24]:
    r=bytearray(ltm_records[0]);struct.pack_into('<I',r,offset,2);ltm_invalid.append(bytes(r))
datasets['consumer']=(b''.join(ltm_records+ltm_invalid),b''.join(ltm_wanted)+(struct.pack('<I',0)+bytes([0xa5])*12)*len(ltm_invalid))
metadata_records=[];metadata_wanted=[];metadata_kinds=[]
for version in [0,1,2,0xffffffff,None]:
    for i in range(12):
        prop=bytearray(rng.randbytes(4236));struct.pack_into('<I',prop,4,version if version is not None else 0)
        cache=bytes([0xa7])*4236 if i%2 else rng.randbytes(4236)
        out,n=metadata.metadata(bytes(prop) if version is not None else None,cache)
        metadata_records.append(struct.pack('<I',version is not None)+bytes(prop)+cache)
        metadata_wanted.append(struct.pack('<I',1)+out);metadata_kinds.append(dict(version=version,instructions=n))
for kind in ['none','uniform','black']:
    prop=(P.parent/'kernel413'/(kind+'-adrc-private.bin')).read_bytes();assert len(prop)==4236
    out,n=metadata.metadata(prop,bytes([0xa7])*4236)
    metadata_records.append(struct.pack('<I',1)+prop+bytes([0xa7])*4236)
    metadata_wanted.append(struct.pack('<I',1)+out);metadata_kinds.append(dict(actual_generation413_kind=kind,instructions=n))
metadata_count=len(metadata_records)
bad=bytearray(metadata_records[0]);struct.pack_into('<I',bad,0,2)
datasets['metadata']=(b''.join(metadata_records)+bytes(bad),b''.join(metadata_wanted)+struct.pack('<I',0)+bytes(bad[-4236:]))
(P/'metadata-cases-private.json').write_text(json.dumps(metadata_kinds,indent=2)+'\n')
sdk=Path('/home/cy122/x2pro-linux/libcamera214-root');work=sdk/'private/camss415-runtime'
files=['kernel415/'+n for n in ['policy-runner.cpp','consumer-runner.cpp','metadata-runner.cpp','libipa/tmc_runtime.cpp','libipa/tmc_runtime.h']]
for name in files:
    dest=work/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(HERE.parent/name,dest)
rows=[]
for name,(data,expected) in datasets.items():
    (P/(name+'-input-private.bin')).write_bytes(data);(P/(name+'-target-private.bin')).write_bytes(expected)
    for arch in ['host','aarch64']:
        flags=['-std=c++17','-O2','-ffp-contract=fast','-Wall','-Wextra','-Werror']
        rels=['kernel415/'+name+'-runner.cpp','kernel415/libipa/tmc_runtime.cpp']
        if arch=='host':
            binary=P/(name+'-host');command=['g++',*flags,'-fsanitize=address,undefined','-no-pie',*[str(HERE.parent/r) for r in rels],'-o',str(binary)];launch=[str(binary)]
        else:
            binary='/private/camss415-runtime/'+name+'-aarch64';command=['chroot',str(sdk),'g++',*flags,*['/private/camss415-runtime/'+r for r in rels],'-o',binary];launch=['chroot',str(sdk),binary]
        q=subprocess.run(command,capture_output=True);assert not q.returncode,q.stderr.decode()
        q=subprocess.run(launch,input=data,capture_output=True,timeout=45);assert not q.returncode,q.stderr.decode()
        (P/(name+'-'+arch+'-actual-private.bin')).write_bytes(q.stdout);assert len(q.stdout)==len(expected)
        diff=sum(a!=b for a,b in zip(q.stdout,expected));rows.append(dict(component=name,architecture=arch,compared_bytes=len(expected),different_bytes=diff,passed=not diff))
        print(json.dumps(rows[-1]),flush=True)
report=dict(stage=415,policy_valid_cases=valid,policy_invalid_cases=len(invalid),policy_matrix_cases=matrix_count,
    factory_root_policy_cases=factory,policy_target_instructions=policy.instructions,policy_target_providers=policy.providers,
    cached_uid_only_refresh_not_source_newer_enable_compare_verified=True,trigger_comparison_float_abs_double_1e_minus9_threshold=True,
    equal_trigger_force_does_not_refresh_histogram_pointer=True,disabled_publishes_existing_adrc_pointer=True,
    lock_suppresses_calculation_after_cache_and_version_update=True,raw_module_enable_copied_to_version=True,
    original_tmc11_prefix=['0x383728','0x383cdc or 0x38565c'],existing_adrc_allocation_only=True,
    ltm_gate_valid_cases=ltm_count,ltm_gate_invalid_cases=len(ltm_invalid),ltm_own_tmc10_gate_cases=own,
    original_ltm_gate=['0x360088','0x35e9dc or 0x363994'],own_tmc10_allocation_and_calculation_not_executed=True,
    ltm_uses_own10_only_root_enable1_use_ltm1_version0=True,otherwise_copies_upstream_ltm_flag_without_global_enable_gate=True,
    metadata_valid_cases=metadata_count,metadata_invalid_cases=1,actual_generation413_metadata_cases=3,
    original_metadata_copy=['0x2dffe0','0x2e01f8'],metadata_consumer_instructions=metadata.instructions,
    metadata_consumer_providers=metadata.providers,metadata_only_memcpy_provider=True,
    version0_copies32_knee_bytes_version1_copies40=True,unknown_version_preserves_knees=True,
    absent_property_clears_only_enable=True,earlier_ispinput112_label_corrected_to_node_cache149a8=True,
    exact_cache_transport_not_hardware_validation=True,architectures=rows,
    current_source_hashes=[dict(path=n,sha256=hashlib.sha256((HERE.parent/n).read_bytes()).hexdigest()) for n in files],
    host_asan_ubsan=True,aarch64_sdk_qemu=True,phone_accessed=False,new_hardware_verification=False,
    runtime_metadata_actually_observed=False,product_request_integration=False,last_device_evidence_stage=406,
    full_goal_kept_active=True,passed=all(r['passed'] for r in rows))
path=HERE/'runtime-validation.json'
if path.exists() and not json.loads(path.read_text())['passed'] and not (HERE/'runtime-r1-validation.json').exists():(HERE/'runtime-r1-validation.json').write_bytes(path.read_bytes())
path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True);assert report['passed']
