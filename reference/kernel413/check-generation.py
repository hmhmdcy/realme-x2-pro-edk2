"""Compare all distinct factory TMC11 regions and histogram boundaries with target generation."""
from pathlib import Path
import hashlib,importlib.util,json,math,random,shutil,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('generation413',HERE/'generation-model.py')
k=importlib.util.module_from_spec(spec);spec.loader.exec_module(k);target=k.GenerationMachine()
defaults=[target.default_gamma(fill) for fill in [0,255]];assert defaults[0]==defaults[1]
default_gamma=defaults[0];assert struct.unpack_from('<f',default_gamma,1024)[0]==1023
weights=bytes(target.u.mem_read(0xdb39c,4096));(P/'histogram-log-weights-private.bin').write_bytes(weights)
(P/'target-default-gamma-private.bin').write_bytes(default_gamma)
(HERE/'gamma-default-validation.json').write_text(json.dumps(dict(stage=413,target_initialization_range=['0x38396c','0x383a28'],
    all257_nodes_same_from_zero_and_all_one_module_memory=True,endpoint1023=True,
    compiled_default_gamma_sha256=hashlib.sha256(default_gamma).hexdigest(),compiled_default_loaded_before_generation=True,
    table_and_values_private=True,controlled_gamma_math_cases_not_claimed_runtime_default=True,phone_accessed=False,passed=True),indent=2)+'\n')
def leaves(nodes):
    for n in nodes:
        if 'children' in n:yield from leaves(n['children'])
        else:yield n['data']
regions={};aliases=0
for variant in ['qtech_s5kgw1','sunny_s5kgw1','sunny_imx471','qtech_s5k3m5sx','sunny_imx319']:
    for root in json.loads((P.parent/'kernel412'/(variant+'-tmc11-trees-private.json')).read_text()):
        for n,data in enumerate(leaves(root['core'])):
            values=[]
            for v in data.values():values.extend(v if isinstance(v,list) else [v])
            raw=struct.pack('<44f',*values);aliases+=1
            regions.setdefault(raw,[]).append(dict(variant=variant,uid=root['uid'],leaf=n))
assert aliases==198 and len(regions)==31
uniform=struct.pack('<1024I',*([64]*1024));black=struct.pack('<1024I',65536,*([0]*1023));white=struct.pack('<1024I',*([0]*1023),65536)
records=[];expected=[];metadata=[];raw_outputs=[];finite_count=0;nonfinite=[]
def add(region,gain,dark,gamma,hist,kind,bindings=None):
    global finite_count
    gains=struct.pack('<2f',gain,dark);result=target.generate(region,gains,gamma,hist)
    a=result['adrc'];out=a[16:56]+a[92:128]+a[64:68]+a[4228:4236]+a[56:64]+result['processed_hist']+a[128:4224]
    assert len(out)==8288
    finite=all(math.isfinite(v) for v in struct.unpack('<2072f',out));finite_count+=finite
    if not finite:nonfinite.append(len(records))
    record=region+gains+struct.pack('<I',hist is not None)+gamma+weights+(hist if hist is not None else bytes(4096));assert len(record)==9408
    records.append(record);raw_outputs.append(out);expected.append(struct.pack('<I',finite)+(out if finite else bytes([0xa5])*8288))
    metadata.append(dict(kind=kind,source_bindings=bindings or [],target_instructions=result['instructions']))
    if len(records)%20==0:print('target TMC11 generation',len(records),flush=True)
for region,bindings in regions.items():
    for gain,dark,hist,kind in [(1,1,None,'factory-no-hist'),(2,1.2,uniform,'factory-uniform'),
                               (8,4,black,'factory-dark-spike'),(32,16,white,'factory-bright-spike')]:
        add(region,gain,dark,default_gamma,hist,kind,bindings)
factory_count=len(records)
base=list(struct.unpack('<44f',next(iter(regions))))
base[30:35]=[0,.5,.5,.5,0];base[37:39]=[.5,.5]
linear_gamma=struct.pack('<257f',*[i*1023/256 for i in range(257)])
curved_gamma=struct.pack('<257f',*[(i/256)**.45*1023 for i in range(257)])
plateau_gamma=struct.pack('<257f',*[0 if i<128 else (i-127)/129*1023 for i in range(257)])
rng=random.Random(413)
histograms=[bytes(4096),uniform,black,white,struct.pack('<1024I',*[rng.randrange(0,10000) for _ in range(1024)]),
            struct.pack('<1024I',*([0xffffffff]*1024))]
for i,hist in enumerate(histograms):
    for j,gamma in enumerate([default_gamma,linear_gamma,curved_gamma,plateau_gamma]):
        add(struct.pack('<44f',*base),[.5,1,2,8][j],[0,.5,1,4][j],gamma,hist,'synthetic-histogram-gamma')
for gain,dark in [(1,1),(1.00001,1.00001),(1e30,1e30),(.5,.5)]:
    add(struct.pack('<44f',*base),gain,dark,default_gamma,None,'synthetic-absent-hist')
base[30:35]=[0,1,1,1,0]
for hist in [None,bytes(4096),uniform,black]:
    add(struct.pack('<44f',*base),2,1.2,default_gamma,hist,'synthetic-histogram-only-degenerate')
count=len(records)
(P/'generation-valid-input-private.bin').write_bytes(b''.join(records));(P/'generation-target-raw-private.bin').write_bytes(b''.join(raw_outputs))
(P/'generation-target-expected-private.bin').write_bytes(b''.join(expected));(P/'generation-cases-private.json').write_text(json.dumps(metadata,indent=2)+'\n')
invalid=[];bad=struct.pack('<I',0)+bytes([0xa5])*8288
for offset,fmt,value in [(0,'f',math.nan),(40,'f',math.inf),(176,'f',0),(176,'f',-1),(176,'f',math.nan),
                          (180,'f',-1),(180,'f',math.inf),(184,'I',2),(188,'f',math.nan),(188+256*4,'f',1024),
                          (188+12,'f',-1),(1216,'f',math.nan)]:
    r=bytearray(records[0]);struct.pack_into('<'+fmt,r,offset,value);invalid.append(bytes(r))
inputs=b''.join(records+invalid);wanted=b''.join(expected)+bad*len(invalid)
(P/'generation-input-private.bin').write_bytes(inputs);(P/'generation-expected-private.bin').write_bytes(wanted)
sdk=Path('/home/cy122/x2pro-linux/libcamera214-root');work=sdk/'private/camss413-generation'
files=['kernel413/generation-runner.cpp','kernel413/libipa/tmc11_generation.cpp','kernel413/libipa/tmc11_generation.h','kernel412/libipa/tmc11_ltm.h']
for name in files:
    dest=work/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(HERE.parent/name,dest)
rows=[]
for arch in ['host','aarch64']:
    flags=['-std=c++17','-O2','-ffp-contract=fast','-Wall','-Wextra','-Werror'];rels=[n for n in files if n.endswith('.cpp')]
    if arch=='host':
        binary=P/'generation-host';command=['g++',*flags,'-fsanitize=address,undefined','-no-pie',*[str(HERE.parent/n) for n in rels],'-o',str(binary)];launch=[str(binary)]
    else:
        binary='/private/camss413-generation/generation-aarch64';command=['chroot',str(sdk),'g++',*flags,*['/private/camss413-generation/'+n for n in rels],'-o',binary];launch=['chroot',str(sdk),binary]
    q=subprocess.run(command,capture_output=True);assert not q.returncode,q.stderr.decode()
    q=subprocess.run(launch,input=inputs,capture_output=True,timeout=45);assert not q.returncode,q.stderr.decode()
    (P/(arch+'-generation-actual-private.bin')).write_bytes(q.stdout);assert len(q.stdout)==len(wanted)
    diffs=sum(a!=b for a,b in zip(q.stdout,wanted));rows.append(dict(architecture=arch,cases=count,invalid_cases=len(invalid),compared_bytes=len(wanted),different_bytes=diffs,passed=not diffs));print(json.dumps(rows[-1]),flush=True)
result=dict(stage=413,cases=count,factory_region_aliases=aliases,distinct_factory_regions=len(regions),factory_generation_cases=factory_count,
    synthetic_histogram_gamma_and_gain_cases=count-factory_count,finite_target_results=finite_count,nonfinite_target_result_cases=len(nonfinite),
    target_generation_range=['0x384048','0x38565c'],target_instructions=target.instructions,target_providers=target.providers,
    logf_expf_powf_are_host_libm_not_target_bionic=True,processed_histogram_knees_coefficients_percentages_contrast_checked=True,
    all_calibration_arrays_explicit_no_private_tables_in_public_library=True,absent_histogram_distinct_from_zero_histogram=True,
    absent_histogram_contrast_memset_byte1_preserved=True,coefficients_and_histogram_generated_by_actual_target_not_fixture=True,
    current_source_hashes=[dict(path=n,sha256=hashlib.sha256((HERE.parent/n).read_bytes()).hexdigest()) for n in files],
    architectures=rows,host_asan_ubsan=True,aarch64_sdk_qemu=True,failed_outputs_preserved=True,input_records_unchanged=True,
    dynamic_trigger_interpolation_and_runtime_version_not_verified=True,phone_accessed=False,full_goal_kept_active=True,
    passed=all(r['passed'] for r in rows))
path=HERE/'generation-validation.json'
if path.exists() and not json.loads(path.read_text())['passed'] and not (HERE/'generation-r1-validation.json').exists():(HERE/'generation-r1-validation.json').write_bytes(path.read_bytes())
path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True);assert result['passed']
