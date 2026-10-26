"""Check actual IPE request binding and AEC HDR trigger domains."""
from pathlib import Path
import hashlib,importlib.util,itertools,json,math,random,shutil,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('binding416',HERE/'binding-model.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);target=m.BindingMachine()
rng=random.Random(416);f32=lambda v:struct.unpack('<f',struct.pack('<f',v))[0]
bindings={}
for version,initial in itertools.product([0,1,2,0xffffffff],[0,1,2,0xa7a7a7a7]):
    out,n=target.binding(version,initial);bindings[(version,initial)]=out
    assert struct.unpack('<2I',out)==(1 if version==1 else initial,1)
records=[];wanted=[];nonfinite=0
def add(t0,t1,g0,g1,s0,s1,version,initial):
    global nonfinite
    record=struct.pack('<2Q4f',t0,t1,g0,g1,s0,s1);out,n=target.hdr(record)
    finite=all(math.isfinite(v) for v in struct.unpack('<3f',out));nonfinite+=not finite
    records.append(record+struct.pack('<2I',version,initial))
    wanted.append(struct.pack('<I',finite)+(out if finite else bytes([0xa5])*12)+bindings[(version,initial)][:4])
eps=f32(1e-9);bits=struct.unpack('<I',struct.pack('<f',eps))[0]
denominators=[0.,-0.,struct.unpack('<f',struct.pack('<I',1))[0],
              struct.unpack('<f',struct.pack('<I',bits-1))[0],eps,
              struct.unpack('<f',struct.pack('<I',bits+1))[0],1.,-1.,1e-30,1e30]
times=[(0,0),(0,100000),(100000,0),(100000,200000),((1<<24)+1,(1<<24)+3),
       ((1<<32)-1,(1<<32)+1),((1<<63)-1,(1<<64)-1),((1<<64)-1,1)]
keys=list(bindings)
for i,((t0,t1),g0,s0) in enumerate(itertools.product(times,denominators,denominators)):
    add(t0,t1,g0,2.125,s0,3.75,*keys[i%len(keys)])
for i in range(200):
    add(rng.getrandbits(64),rng.getrandbits(64),rng.uniform(.01,128),rng.uniform(.01,128),
        rng.uniform(.01,65536),rng.uniform(.01,65536),*keys[i%len(keys)])
for i,(g0,g1,s0,s1) in enumerate([(1e-8,3e38,1,1),(1,1,1e-8,3e38)]):
    add(1,2,g0,g1,s0,s1,*keys[i])
count=len(records);invalid=[]
for offset,value in [(16,math.nan),(20,math.inf),(24,-math.inf),(28,math.nan)]:
    r=bytearray(records[0]);struct.pack_into('<f',r,offset,value);invalid.append(bytes(r))
inputs=b''.join(records+invalid);gold=b''.join(wanted)
for record in invalid:
    version,initial=struct.unpack_from('<2I',record,32)
    gold+=struct.pack('<I',0)+bytes([0xa5])*12+bindings[(version,initial)][:4]
(P/'input-records-private.bin').write_bytes(inputs);(P/'input-target-private.bin').write_bytes(gold)
sdk=Path('/home/cy122/x2pro-linux/libcamera214-root');work=sdk/'private/camss416-input'
files=['kernel416/'+n for n in ['input-runner.cpp','libipa/tmc_input.cpp','libipa/tmc_input.h']]
for name in files:
    dest=work/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(HERE.parent/name,dest)
rows=[]
for arch in ['host','aarch64']:
    flags=['-std=c++17','-O2','-ffp-contract=fast','-Wall','-Wextra','-Werror'];sources=[n for n in files if n.endswith('.cpp')]
    if arch=='host':
        binary=P/'input-host';command=['g++',*flags,'-fsanitize=address,undefined','-no-pie',*[str(HERE.parent/n) for n in sources],'-o',str(binary)];launch=[str(binary)]
    else:
        binary='/private/camss416-input/input-aarch64';command=['chroot',str(sdk),'g++',*flags,*['/private/camss416-input/'+n for n in sources],'-o',binary];launch=['chroot',str(sdk),binary]
    q=subprocess.run(command,capture_output=True);assert not q.returncode,q.stderr.decode()
    q=subprocess.run(launch,input=inputs,capture_output=True,timeout=45);assert not q.returncode,q.stderr.decode();assert len(q.stdout)==len(gold)
    (P/(arch+'-input-actual-private.bin')).write_bytes(q.stdout)
    diff=sum(a!=b for a,b in zip(q.stdout,gold));rows.append(dict(architecture=arch,compared_bytes=len(gold),different_bytes=diff,passed=not diff));print(json.dumps(rows[-1]),flush=True)
report=dict(stage=416,cases=count,invalid_cases=len(invalid),nonfinite_target_results_atomically_rejected=nonfinite,
    binding_cases=len(bindings),actual_ipe_input_stack_offset='0x340',prior_240_base_is256_bytes_before_input=True,
    earlier_global_version_table_claim_retracted=True,earlier_global_pointer_actual_2760_tuning_manager=True,
    request_zero_initialization=['0x2cf504','0x2cf514'],initialized_request_bytes=19928,
    binding_range=['0x2d6564','0x2d6590'],adrc_cache_node_offset='0x149a8',
    only_cache_version1_sets_request_version1_other_values_preserve_initial=True,adrc_pointer_always_bound_to_cache=True,
    hdr_range=['0x377120','0x3771b8'],aec_exposure_slot0_offsets=[0,8,12],aec_exposure_slot1_offsets=[24,32,36],
    hdr_ratios_exposure_time_gain_sensitivity=True,module88_exposure_time_ratio_module92_sensitivity_ratio=True,
    exposure_slot_long_short_semantic_names_not_assumed=True,control2_zero_not_exposure_gain_ratio=True,
    target_instructions=target.instructions,target_providers=target.providers,
    current_source_hashes=[dict(path=n,sha256=hashlib.sha256((HERE.parent/n).read_bytes()).hexdigest()) for n in files],
    architectures=rows,host_asan_ubsan=True,aarch64_sdk_qemu=True,phone_accessed=False,
    runtime_android_metadata_observed=False,last_device_evidence_stage=406,full_goal_kept_active=True,
    passed=all(r['passed'] for r in rows))
path=HERE/'input-validation.json'
if path.exists() and not json.loads(path.read_text())['passed'] and not (HERE/'input-r1-validation.json').exists():(HERE/'input-r1-validation.json').write_bytes(path.read_bytes())
path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True);assert report['passed']
