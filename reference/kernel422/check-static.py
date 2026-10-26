"""Validate new LTM table/scalar assembly using retained selected OEM data."""
from pathlib import Path
import hashlib,importlib.util,json,math,random,shutil,struct,subprocess
HERE=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel422');P.mkdir(mode=0o700,exist_ok=True)
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
storage=module('storage284',HERE.parent/'kernel284/storage.py');storage.mounted_build()
model=module('static422',HERE/'static-model.py').StaticMachine()
records=[];wanted=[];sources=[];selected=json.loads((HERE.parent/'kernel351/mode-colour-chain-validation.json').read_text())['selected']
seen=set()
def record(reserve,data):
    r=reserve;d=data
    return struct.pack('<5f5I24i6i65i65fI',*[r[k] for k in ['c1','c2','c3','c4']],d['y_ratio_max'],
        *[r[k] for k in ['igamma_en','la_en','mask_filter_en','data_collect_en','img_process_en']],
        *r['wt_tab'],*r['mask_filter_kernel_tab'],*r['mask_rect_curve_tab'],*d['la_curve_tab'],r['lce_thd'])
for context in selected:
    path=P.parent/'kernel351'/(context['variant']+'-ltm13_ipe-trees-private.json')
    root=next(r for r in json.loads(path.read_text()) if r['uid']==context['ltm_root'])
    for drc in root['core']:
        for hdr in drc['children']:
            for aec in hdr['children']:
                raw=record(root['reserve'],aec['data'])
                if raw not in seen:seen.add(raw);records.append(raw)
factory_count=len(records)
# Probe packing edges and source mask-kernel zero exponents using target code.
rng=random.Random(422)
for i in range(24):
    data=bytearray(records[i%factory_count])
    struct.pack_into('<5f',data,0,*([-.5,0,.5,1,1.5][(i+j)%5] for j in range(4)),[-1.9,0,1023.9,2048][i%4])
    struct.pack_into('<5I',data,20,*([0,1,2,0xffffffff][(i+j)%4] for j in range(5)))
    struct.pack_into('<6i',data,136,*([0,1,6,9,-1][(i+j)%5] for j in range(6)))
    struct.pack_into('<65i',data,160,*([0,4095,16383,2048,8192][(i+j)%5] for j in range(65)))
    struct.pack_into('<65f',data,420,*(rng.choice([0,.5,1.5,4095.5,8191.5]) for _ in range(65)))
    struct.pack_into('<I',data,680,[0,1023,1024,0xffffffff][i%4]);records.append(bytes(data))
for i,raw in enumerate(records):
    out=model.evaluate(raw);assert len(out)==636
    wanted.append(struct.pack('<I',1)+out)
valid=len(records)
invalid=[]
for offset,fmt,value in [(0,'f',math.nan),(16,'f',math.inf),(420,'f',math.nan),(420,'f',-1),(160,'i',-1),(40,'i',256),(0,'f',3e38)]:
    raw=bytearray(records[0]);struct.pack_into('<'+fmt,raw,offset,value);invalid.append(bytes(raw))
inputs=b''.join(records+invalid);gold=b''.join(wanted)+len(invalid)*(struct.pack('<I',0)+bytes([0xa5])*636)
(P/'static-input-private.bin').write_bytes(inputs);(P/'static-target-private.bin').write_bytes(gold)
sdk=Path('/home/cy122/x2pro-linux/libcamera214-root');work=sdk/'private/camss422-static'
files=['static-runner.cpp','libipa/ltm13_static.h','libipa/ltm13_static.cpp']
for name in files:
    out=work/name;out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(HERE/name,out)
results=[]
for arch in ['host','aarch64']:
    flags=['-std=c++17','-O2','-Wall','-Wextra','-Werror']
    cpp=['static-runner.cpp','libipa/ltm13_static.cpp']
    if arch=='host':
        binary=P/'static-host';command=['g++',*flags,'-fsanitize=address,undefined','-no-pie',*[str(HERE/n) for n in cpp],'-o',str(binary)];launch=[str(binary)]
    else:
        binary='/private/camss422-static/static-arm64';command=['chroot',str(sdk),'g++',*flags,*['/private/camss422-static/'+n for n in cpp],'-o',binary];launch=['chroot',str(sdk),binary]
    q=subprocess.run(command,capture_output=True);(P/(arch+'-static-build.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
    q=subprocess.run(launch,input=inputs,capture_output=True,timeout=45);(P/(arch+'-static-output-private.bin')).write_bytes(q.stdout);assert not q.returncode,q.stderr.decode()
    assert len(q.stdout)==len(gold),(len(q.stdout),len(gold))
    diff=[i for i,(a,b) in enumerate(zip(q.stdout,gold)) if a!=b]
    row=dict(architecture=arch,cases=valid,invalid_cases=len(invalid),compared_bytes=len(gold),different_bytes=len(diff),passed=not diff)
    results.append(row);print(json.dumps(row),flush=True)
    if diff:print('first mismatch record, byte',diff[0]//640,diff[0]%640,flush=True)
report=dict(stage=422,factory_unique_leaf_inputs=factory_count,additional_boundary_cases=24,invalid_cases=len(invalid),
    selected_factory_tables_reused=True,prior_inverse_gamma_352_403_reused_without_rerun=True,
    scalar_weight_and_unsigned_pack_actual_target_fragments=True,dc_ip_boolean_policy_not_full_pass_state_verified=True,
    sixth_mask_normalization_contribution_fixed4_matches_actual_target=True,
    cases=valid,architectures=results,target_instructions=model.instructions,target_providers=model.providers,
    phone_accessed=False,full_automatic_tmc_ltm_integrated=False,passed=all(r['passed'] for r in results))
path=HERE/'static-validation.json'
if path.exists():
    i=1
    while (HERE/('static-r'+str(i)+'-validation.json')).exists():i+=1
    (HERE/('static-r'+str(i)+'-validation.json')).write_bytes(path.read_bytes())
path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));assert report['passed']
