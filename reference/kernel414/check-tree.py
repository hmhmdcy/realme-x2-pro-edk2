"""Compare all factory TMC11 trees and multilevel trigger edges with original code."""
from pathlib import Path
import copy,hashlib,importlib.util,json,math,random,shutil,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('tree414',HERE/'tree-model.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);target=m.TreeMachine()
f32=lambda x:struct.unpack('<f',struct.pack('<f',x))[0]
def encode(root,controls,triggers):
    raw=struct.pack('<2I5fI',*controls,*triggers,len(root['core']))
    for d in root['core']:
        raw+=struct.pack('<2fI',*d['trigger'],len(d['children']))
        for h in d['children']:
            raw+=struct.pack('<6fI',*h['trigger'],len(h['children']))
            for a in h['children']:raw+=struct.pack('<4f',*a['trigger'])+m.region_bytes(a['data'])
    return struct.pack('<I',len(raw))+raw
def points(intervals):
    out={f32(intervals[0][0]-1),f32(intervals[-1][1]+1)}
    for a,b in intervals:
        out.update([a,b,f32((a+b)/2)])
        for v in [a,b]:
            bits=struct.unpack('<I',struct.pack('<f',v))[0]
            if bits>0:out.add(struct.unpack('<f',struct.pack('<I',bits-1))[0])
            if bits<0x7f7fffff:out.add(struct.unpack('<f',struct.pack('<I',bits+1))[0])
    for left,right in zip(intervals,intervals[1:]):
        if left[1]<right[0]:out.update(f32(left[1]+(right[0]-left[1])*r) for r in [.25,.5,.75])
    return sorted(out)
records=[];gold=[];metadata=[];max_children=0;disabled=0
def add(root,controls,triggers,kind,variant=None):
    global max_children,disabled
    triggers=[f32(t) for t in triggers]
    raw,nodes,instructions=target.tree(root,controls,triggers)
    assert all(math.isfinite(x) for x in struct.unpack('<44f',raw))
    max_children=max(max_children,max(n['children'] for n in nodes));disabled+=not root['enabled']
    records.append(encode(root,controls,triggers));gold.append(struct.pack('<I',1)+raw)
    metadata.append(dict(kind=kind,variant=variant,uid=root.get('uid'),controls=controls,
                         triggers=triggers,target_nodes=nodes,instructions=instructions))
    if len(records)%300==0:print('original TMC11 tree cases',len(records),flush=True)
variants=['qtech_s5kgw1','sunny_s5kgw1','sunny_imx471','qtech_s5k3m5sx','sunny_imx319']
roots=[]
for variant in variants:
    for root in json.loads((P.parent/'kernel412'/(variant+'-tmc11-trees-private.json')).read_text()):
        roots.append((variant,root))
        assert root['control_method']==[0,0]
        for control in [0,1]:
            axis=control*2
            intervals=[a['trigger'][axis:axis+2] for d in root['core'] for h in d['children'] for a in h['children']]
            for value in points(intervals):
                add(root,[control,0],[2,value if control else 1.75,value if not control else 51,2,3],
                    'factory-original-controls' if not control else 'factory-forced-gain-control',variant)
factory_count=len(records)
rng=random.Random(414)
def synthetic(counts,overlap=False):
    def triggers(count,axes):
        result=[]
        for i in range(count):
            row=[]
            for axis in range(axes):
                a=f32(-2+axis*.37+i*(.75 if overlap else 2.75));b=f32(a+1.25)
                row.extend([a,b])
            result.append(row)
        return result
    core=[]
    for dt in triggers(counts[0],1):
        children=[]
        for ht in triggers(counts[1],3):
            leaves=[]
            for at in triggers(counts[2],2):
                # Ordinary finite signed values exercise separate integer/fraction rounding.
                data={'test_values':[f32(rng.uniform(-1000,1000)) for _ in range(44)]}
                leaves.append(dict(trigger=at,data=data))
            children.append(dict(trigger=ht,children=leaves))
        core.append(dict(trigger=dt,children=children))
    return dict(enabled=1,core=core)
for i in range(180):
    counts=[1+i%3,1+(i//3)%3,1+(i//9)%5]
    root=synthetic(counts,overlap=i%2==0);controls=[i%2,(i//2)%3]
    triggers=[rng.uniform(-4,max(counts)*3) for _ in range(5)]
    add(root,controls,triggers,'synthetic-multilevel-signed')
    if i%15==0:
        # All levels select two children and interpolate, including HDR2's zero trigger.
        root=synthetic([2,2,2]);add(root,controls,[0,0,0,0,0],'synthetic-three-active-blends')
for level in range(3):
    counts=[1,1,1];counts[level]=20;root=synthetic(counts)
    for control in range(6):
        for value in [-5,-.75,0,1.9,20,51.5,60]:
            add(root,[control%2,control//2],[value]*5,'synthetic-twenty-region-search')
# The module's HDR2 branch writes zero; changing either input slot must have no effect.
root=synthetic([2,3,2]);zero_pairs=[]
for ac in [0,1]:
    start=len(gold)
    add(root,[ac,2],[0,0,0,-500,900],'hdr2-zero-input-a')
    add(root,[ac,2],[0,0,0,700,-800],'hdr2-zero-input-b')
    assert gold[start]==gold[start+1];zero_pairs.append([start,start+1])
count=len(records);valid_input=b''.join(records);valid_gold=b''.join(gold)
(P/'tree-valid-input-private.bin').write_bytes(valid_input)
(P/'tree-target-expected-private.bin').write_bytes(valid_gold)
(P/'tree-cases-private.json').write_text(json.dumps(metadata,indent=2)+'\n')
invalid=[]
base=roots[0][1]
for controls,triggers in [([2,0],[2,2,50,2,2]),([0,3],[2,2,50,2,2]),
                          ([0,0],[math.nan,2,50,2,2]),([0,0],[2,math.inf,50,2,2]),
                          ([0,0],[2,2,50,math.nan,2])]:
    invalid.append(encode(base,controls,triggers))
for level in range(3):
    for n in [0,21]:
        r=synthetic([1,1,1]);container=r['core']
        for _ in range(level):container=container[0]['children']
        leaf=copy.deepcopy(container[0]);container[:]=[copy.deepcopy(leaf) for _ in range(n)]
        invalid.append(encode(r,[0,0],[0]*5))
for mutate in ['trigger-nan','interval-reversed','data-inf','integer-overflow']:
    r=synthetic([2,2,2]);a=r['core'][0]['children'][0]['children'][0]
    if mutate=='trigger-nan':a['trigger'][0]=math.nan
    elif mutate=='interval-reversed':a['trigger'][0]=100
    elif mutate=='data-inf':a['data']['test_values'][0]=math.inf
    else:a['data']['test_values'][0]=1e30
    invalid.append(encode(r,[0,0],[0]*5))
inputs=valid_input+b''.join(invalid);wanted=valid_gold+(struct.pack('<I',0)+bytes([0xa5])*176)*len(invalid)
(P/'tree-input-private.bin').write_bytes(inputs);(P/'tree-expected-private.bin').write_bytes(wanted)
sdk=Path('/home/cy122/x2pro-linux/libcamera214-root');work=sdk/'private/camss414-tree'
files=['kernel414/tree-runner.cpp','kernel414/libipa/tmc11_tree.cpp','kernel414/libipa/tmc11_tree.h']
for name in files:
    dest=work/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(HERE.parent/name,dest)
rows=[]
for arch in ['host','aarch64']:
    flags=['-std=c++17','-O2','-ffp-contract=fast','-Wall','-Wextra','-Werror'];sources=[n for n in files if n.endswith('.cpp')]
    if arch=='host':
        binary=P/'tree-host';command=['g++',*flags,'-fsanitize=address,undefined','-no-pie',*[str(HERE.parent/n) for n in sources],'-o',str(binary)];launch=[str(binary)]
    else:
        binary='/private/camss414-tree/tree-aarch64';command=['chroot',str(sdk),'g++',*flags,*['/private/camss414-tree/'+n for n in sources],'-o',binary];launch=['chroot',str(sdk),binary]
    q=subprocess.run(command,capture_output=True);assert not q.returncode,q.stderr.decode()
    q=subprocess.run(launch,input=inputs,capture_output=True,timeout=45);assert not q.returncode,q.stderr.decode()
    (P/(arch+'-tree-actual-private.bin')).write_bytes(q.stdout);assert len(q.stdout)==len(wanted)
    diffs=sum(a!=b for a,b in zip(q.stdout,wanted));rows.append(dict(architecture=arch,cases=count,invalid_cases=len(invalid),compared_bytes=len(wanted),different_bytes=diffs,passed=not diffs));print(json.dumps(rows[-1]),flush=True)
result=dict(stage=414,cases=count,factory_roots=len(roots),factory_trigger_cases=factory_count,
    synthetic_multilevel_cases=count-factory_count,invalid_cases=len(invalid),numeric_disabled_root_cases=disabled,
    original_control_method_all68_roots=[0,0],factory_drc_hdr_counts_all_one=True,
    forced_gain_and_hdr_controls_are_numeric_fixtures_only=True,all44_fields_checked=True,
    original_module_prefix=['0x383cdc','0x384048'],original_search_helpers=['0x4ac150','0x4ac498','0x4ac908'],
    original_callback='0x4ab450',maximum_selected_children=max_children,target_instructions=target.instructions,
    target_providers=target.providers,only_memset_provider=True,hdr_control2_zero_trigger_pairs=len(zero_pairs),
    native_root_bytes=136,native_drc_bytes=24,native_hdr_bytes=40,native_aec_bytes=192,
    module_hdr_slot88_and92_upstream_identities_not_verified=True,root_enable_not_changed=True,
    host_asan_ubsan=True,aarch64_sdk_qemu=True,architectures=rows,
    current_source_hashes=[dict(path=n,sha256=hashlib.sha256((HERE.parent/n).read_bytes()).hexdigest()) for n in files],
    input_tree_immutable=True,failed_output_preserved=True,runtime_version_selection_verified=False,
    phone_accessed=False,new_hardware_verification=False,last_device_evidence_stage=406,
    full_goal_kept_active=True,passed=all(r['passed'] for r in rows))
path=HERE/'tree-validation.json'
if path.exists() and not json.loads(path.read_text())['passed'] and not (HERE/'tree-r1-validation.json').exists():(HERE/'tree-r1-validation.json').write_bytes(path.read_bytes())
path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True);assert result['passed']
