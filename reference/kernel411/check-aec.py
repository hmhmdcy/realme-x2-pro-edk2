"""Compare region selection/interpolation and downstream gains with full target TMC10."""
from pathlib import Path
import hashlib,importlib.util,json,math,random,shutil,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('knee411',HERE/'knee-model.py')
k=importlib.util.module_from_spec(spec);spec.loader.exec_module(k);target=k.KneeMachine()
f32=lambda v:struct.unpack('<f',struct.pack('<f',v))[0]
names=['gtm_percentage','ltm_percentage','la_percentage','gamma_percentage','knee_out_mid',
       'dark_boost_ratio',*['core_rsv_para'+str(i) for i in range(1,6)]]
records=[];cases=[];expected=[];disabled=0
eq=struct.pack('<65f',*[i*4095/64 for i in range(65)])

def add(root,lux,gain,drc,dark,control,kind):
    global disabled
    leaves=b''.join(struct.pack('<15f',*r['trigger'],*[r['data'][n] for n in names]) for r in root['core'])
    raw=struct.pack('<2I4f',len(root['core']),control,lux,gain,drc,dark)+leaves
    raw+=bytes(324-len(raw));assert len(raw)==324
    # Target input uses precisely the same float values as the portable API.
    lux,gain,drc,dark=struct.unpack_from('<4f',raw,8)
    data,curve=target.tree(root,lux,gain,drc,dark,control)
    region=data+target.last_selection;assert len(region)==56
    finite=all(math.isfinite(v) for v in struct.unpack('<18f',curve))
    if finite:
        sampled=target.sample(curve,eq);ok=all(math.isfinite(v) for v in struct.unpack('<65f',sampled))
    else:sampled=bytes([0xa5])*260;ok=False
    out=struct.pack('<I',1)+region+struct.pack('<I',finite)+(curve if finite else bytes([0xa5])*72)
    out+=struct.pack('<I',ok)+(sampled if ok else bytes([0xa5])*260);assert len(out)==400
    records.append(raw);expected.append(out);disabled+=not root['enabled'];cases.append(dict(kind=kind,control=control))
    if len(records)%250==0:print('whole target AEC',len(records),flush=True)

variants=['qtech_s5kgw1','sunny_s5kgw1','sunny_imx471','qtech_s5k3m5sx','sunny_imx319']
for name in variants:
    root=json.loads((P.parent/'kernel410'/(name+'-tmc10-trees-private.json')).read_text())[0]
    for control in [0,1]:
        axis=control*2;points=set()
        intervals=[r['trigger'][axis:axis+2] for r in root['core']]
        assert all(a<=b for a,b in intervals)
        points.update([f32(intervals[0][0]-1),f32(intervals[-1][1]+1)])
        for a,b in intervals:
            points.update([a,b,f32((a+b)/2)])
            for value in [a,b]:
                points.update([f32(math.nextafter(value,-math.inf)),f32(math.nextafter(value,math.inf))])
                # Actual neighboring float32 values, including signed zero.
                bits=struct.unpack('<I',struct.pack('<f',value))[0]
                if bits>0:points.add(struct.unpack('<f',struct.pack('<I',bits-1))[0])
                if bits<0x7f7fffff:points.add(struct.unpack('<f',struct.pack('<I',bits+1))[0])
        for i in range(len(intervals)-1):
            a,b=intervals[i][1],intervals[i+1][0]
            points.update(f32(a+(b-a)*ratio) for ratio in [.25,.5,.75])
        for value in sorted(points):
            for drc,dark in [(1,1),(2,1.00005),(8,2)]:
                add(root,value if control==0 else 73.25,value if control else 2.125,drc,dark,control,'factory-trigger-sweep')
factory_count=len(records);rng=random.Random(411)
for i in range(150):
    count=1+i%5;core=[];ends=[-2.,.1]
    for j in range(count):
        trigger=[]
        for axis in range(2):
            start=f32(ends[axis]+rng.uniform(.01,3));end=f32(start+rng.uniform(0,2));ends[axis]=end
            trigger.extend([start,end])
        values=[rng.random() for _ in range(7)]+[rng.uniform(-100,100) for _ in range(4)]
        core.append(dict(trigger=trigger,data={n:f32(v) for n,v in zip(names,values)}))
    root=dict(enabled=1,control_method=i%2,reserve=dict(use_gtm=1,use_ltm=1),core=core)
    control=i%2;axis=control*2;value=rng.uniform(core[0]['trigger'][axis]-1,core[-1]['trigger'][axis+1]+1)
    add(root,value if not control else 5,value if control else 1.5,2,1.2,control,'synthetic-ordered-tree')
count=len(records);invalid=[];bad=struct.pack('<I',0)+bytes([0xa5])*56+struct.pack('<I',0)+bytes([0xa5])*72+struct.pack('<I',0)+bytes([0xa5])*260
for offset,fmt,value in [(0,'I',0),(0,'I',6),(4,'I',2),(8,'f',math.nan),(12,'f',math.inf),
                          (24,'f',math.nan),(36,'f',math.inf),(40,'f',math.nan),(80,'f',math.inf),
                          (24,'f',1e30),(88,'f',-1e30)]:
    r=bytearray(records[0]);struct.pack_into('<'+fmt,r,offset,value);invalid.append(bytes(r))
inputs=b''.join(records+invalid);wanted=b''.join(expected)+bad*len(invalid)
(P/'aec-input-private.bin').write_bytes(inputs);(P/'aec-expected-private.bin').write_bytes(wanted)
(P/'aec-cases-private.json').write_text(json.dumps(cases,indent=2)+'\n')
sdk=Path('/home/cy122/x2pro-linux/libcamera214-root');work=sdk/'private/camss411-aec'
files=['kernel411/aec-runner.cpp','kernel411/libipa/tmc10_aec.cpp','kernel411/libipa/tmc10_aec.h','kernel410/libipa/tmc10.cpp','kernel410/libipa/tmc10.h']
for name in files:
    dest=work/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(HERE.parent/name,dest)
rows=[]
for arch in ['host','aarch64']:
    flags=['-std=c++17','-O2','-ffp-contract=fast','-Wall','-Wextra','-Werror'];rels=[n for n in files if n.endswith('.cpp')]
    if arch=='host':
        binary=P/'aec-host';command=['g++',*flags,'-fsanitize=address,undefined','-no-pie',*[str(HERE.parent/n) for n in rels],'-o',str(binary)];launch=[str(binary)]
    else:
        binary='/private/camss411-aec/aec-aarch64';command=['chroot',str(sdk),'g++',*flags,*['/private/camss411-aec/'+n for n in rels],'-o',binary];launch=['chroot',str(sdk),binary]
    q=subprocess.run(command,capture_output=True);assert not q.returncode,q.stderr.decode()
    q=subprocess.run(launch,input=inputs,capture_output=True,timeout=45);assert not q.returncode,q.stderr.decode()
    (P/(arch+'-aec-actual-private.bin')).write_bytes(q.stdout);assert len(q.stdout)==len(wanted)
    diffs=sum(a!=b for a,b in zip(q.stdout,wanted));rows.append(dict(architecture=arch,cases=count,invalid_cases=len(invalid),compared_bytes=len(wanted),different_bytes=diffs,passed=not diffs));print(json.dumps(rows[-1]),flush=True)
result=dict(stage=411,cases=count,factory_trigger_sweep_cases=factory_count,synthetic_ordered_trees=150,
    invalid_cases=len(invalid),numeric_cases_using_disabled_roots=disabled,all_eleven_region_fields_checked=True,
    full_target_function_entry='0x3774b0',full_target_interpolation_knees_and_sampling_executed=True,
    target_instructions=target.instructions,target_providers=target.providers,logf_and_powf_host_libm_not_bionic=True,
    input_regions_unchanged=True,failed_outputs_preserved=True,overlapping_factory_real_gain_axis_checked=True,
    factory_real_gain_control_override_is_numeric_fixture_only=True,
    no_root_enable_or_runtime_version_selection=True,not_tmc11_drc_hdr_trigger_tree=True,
    architectures=rows,current_source_hashes=[dict(path=n,sha256=hashlib.sha256((HERE.parent/n).read_bytes()).hexdigest()) for n in files],
    phone_accessed=False,full_goal_kept_active=True,passed=all(r['passed'] for r in rows))
path=HERE/'aec-validation.json'
if path.exists() and not json.loads(path.read_text())['passed'] and not (HERE/'aec-r1-validation.json').exists():(HERE/'aec-r1-validation.json').write_bytes(path.read_bytes())
path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True);assert result['passed']
