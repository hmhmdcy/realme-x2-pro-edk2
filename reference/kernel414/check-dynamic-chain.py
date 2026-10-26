"""Feed verified portable tree output into generation and LTM LUT encoding."""
from pathlib import Path
import ctypes,hashlib,importlib.util,json,math,shutil,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);out=importlib.util.module_from_spec(spec);spec.loader.exec_module(out);return out
tree_report=json.loads((HERE/'tree-validation.json').read_text());assert tree_report['passed']
metadata=json.loads((P/'tree-cases-private.json').read_text())
tree_input=(P/'tree-valid-input-private.bin').read_bytes();tree_gold=(P/'tree-target-expected-private.bin').read_bytes()
tree_records=[];at=0
while at<len(tree_input):
    size=struct.unpack_from('<I',tree_input,at)[0];tree_records.append(tree_input[at:at+4+size]);at+=4+size
assert len(tree_records)==len(metadata)
bindings={}
for i,c in enumerate(metadata):
    if c['kind']=='factory-original-controls':bindings.setdefault((c['variant'],c['uid']),[]).append(i)
assert len(bindings)==68
chosen=[]
for key,indices in bindings.items():
    gaps=[i for i in indices if any(0<n['ratio']<1 for n in metadata[i]['target_nodes'])]
    chosen.extend([indices[0],gaps[len(gaps)//2] if gaps else indices[len(indices)//2]])
sample=module('sample412',HERE.parent/'kernel412/tmc11-model.py').Tmc11Machine()
adrc=module('adrc409',HERE.parent/'kernel409/adrc-model.py').AdrcMachine()
generation=module('generation413',HERE.parent/'kernel413/generation-model.py').GenerationMachine()
profiles=json.loads((P.parent/'kernel351/mode-profiles-private.json').read_text())
old_cases=json.loads((P.parent/'kernel407/curve-cases-private.json').read_text());old_curves=(P.parent/'kernel407/curves-host-output-private.bin').read_bytes()
fixed={}
for name in ['qtech_s5kgw1','sunny_s5kgw1','sunny_imx471','qtech_s5k3m5sx','sunny_imx319']:
    if name in profiles:selected=next(p for p in profiles[name] if p['usecase']=='Preview')['modules']['ltm13_ipe']
    else:selected=next(r for r in json.loads((P.parent/'kernel351'/(name+'-ltm13_ipe-trees-private.json')).read_text()) if r['uid']==42)
    index=next(i for i,c in enumerate(old_cases) if c.get('variant')==name and c.get('uid')==selected['uid'])
    scale=[int(math.copysign(math.floor(abs(v)+.5),v)) for v in struct.unpack_from('<65f',old_curves,index*788+8)]
    fixed[name]=(selected['reserve']['ltm_curve_tab'],scale)
gamma=(P.parent/'kernel348/factory-gamma-private.bin').read_bytes()
forward=[float(struct.unpack_from('<H',gamma,8+256+i*4)[0]) for i in range(64)]
forward.append(forward[-1]+struct.unpack_from('<h',gamma,8+256+63*4+2)[0])
inverse=(P.parent/'kernel352/inverse-oracle-output-private.bin').read_bytes();axis=sample.axis()
default_gamma=(P.parent/'kernel413/target-default-gamma-private.bin').read_bytes()
weights=(P.parent/'kernel413/histogram-log-weights-private.bin').read_bytes()
assert hashlib.sha256(default_gamma).hexdigest()==json.loads((HERE.parent/'kernel413/gamma-default-validation.json').read_text())['compiled_default_gamma_sha256']
generation_gold=[];generation_records=[];chain_records=[];pack_records=[];status=[];rejected_nonfinite=0;rejected_subunity=0
for j,i in enumerate(chosen):
    c=metadata[i];region=tree_gold[i*180+4:(i+1)*180]
    gain,dark=(2,1.2) if j%2==0 else (8,4)
    gains=struct.pack('<2f',gain,dark)
    hist=struct.pack('<1024I',*([64]*1024)) if j%2==0 else struct.pack('<1024I',65536,*([0]*1023))
    result=generation.generate(region,gains,default_gamma,hist);a=result['adrc']
    state=a[16:56]+a[92:128]+a[64:68]+a[4228:4236]+a[56:64]+result['processed_hist']+a[128:4224]
    finite=all(math.isfinite(v) for v in struct.unpack('<2072f',state))
    generation_gold.append(struct.pack('<I',finite)+(state if finite else bytes([0xa5])*8288))
    record=region+gains+struct.pack('<I',1)+default_gamma+weights+hist
    assert len(record)==9408;generation_records.append(record)
    curve,scale=fixed[c['variant']]
    eq=struct.pack('<65f',*[float((w&16383)//4) for w in struct.unpack_from('<64I',inverse,(j%29)*256)],4095.)
    chain_records.append(record+eq+axis+struct.pack('<65f65i65h2x',*forward,*curve,*scale))
    if not finite:status.append(False);rejected_nonfinite+=1;continue
    pchip=state[:76];controls=state[76:88];hist_curve=state[4192:8288]
    norm,mix=sample.normalize(eq,pchip);linear=sample.pchip(pchip,norm);gain_bytes=sample.contrast(norm,linear,controls,hist_curve)
    values=struct.unpack('<65f',gain_bytes);assert all(math.isfinite(v) for v in values)
    if values[0]<1024:status.append(False);rejected_subunity+=1;continue
    raw=eq+gain_bytes+struct.pack('<65f',*forward)+mix+struct.pack('<65i65h2x',*curve,*scale)
    output,_=adrc.evaluate(raw);blend=output[528:918]
    pack_records.append(struct.pack('<2I65i',0,64,*struct.unpack_from('<65i',blend))+
                        struct.pack('<2I65i',1,64,*struct.unpack_from('<65h',blend,260)))
    status.append(True)
    if j%25==0:print('dynamic target generation and LUT',j+1,flush=True)
q=subprocess.run([str(P.parent/'kernel405/original-packers-private')],input=b''.join(pack_records),capture_output=True);assert not q.returncode,q.stderr.decode()
gold=q.stdout;assert len(gold)==sum(status)*512
chain_gold=[];at=0
for ok in status:
    chain_gold.append(struct.pack('<I',ok)+(gold[at:at+512] if ok else bytes([0xa5])*512));at+=512*ok
inputs=b''.join(tree_records[i] for i in chosen);wanted_tree=b''.join(tree_gold[i*180:(i+1)*180] for i in chosen)
gen_input=b''.join(generation_records);wanted_gen=b''.join(generation_gold);wanted_chain=b''.join(chain_gold)
(P/'dynamic-tree-input-private.bin').write_bytes(inputs)
(P/'dynamic-generation-target-private.bin').write_bytes(wanted_gen)
(P/'dynamic-chain-target-private.bin').write_bytes(wanted_chain)
(P/'dynamic-selected-cases-private.json').write_text(json.dumps(chosen)+'\n')
sdk=Path('/home/cy122/x2pro-linux/libcamera214-root');work=sdk/'private/camss414-dynamic'
names=['kernel413/generation-runner.cpp','kernel413/chain-runner.cpp','kernel413/libipa/tmc11_generation.cpp',
       'kernel413/libipa/tmc11_generation.h','kernel412/libipa/tmc11_ltm.cpp','kernel412/libipa/tmc11_ltm.h',
       'kernel409/libipa/ltm_adrc.cpp','kernel409/libipa/ltm_adrc.h']
for name in names:
    dest=work/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(HERE.parent/name,dest)
rows=[]
for arch in ['host','aarch64']:
    launch=[str(P/'tree-host')] if arch=='host' else ['chroot',str(sdk),'/private/camss414-tree/tree-aarch64']
    q=subprocess.run(launch,input=inputs,capture_output=True,timeout=45);assert not q.returncode,q.stderr.decode();assert q.stdout==wanted_tree
    portable_regions=[q.stdout[j*180+4:(j+1)*180] for j in range(len(chosen))]
    portable_gen=b''.join(r+generation_records[j][176:] for j,r in enumerate(portable_regions))
    portable_chain=b''.join(r+chain_records[j][176:] for j,r in enumerate(portable_regions))
    assert portable_gen==gen_input
    flags=['-std=c++17','-O2','-ffp-contract=fast','-Wall','-Wextra','-Werror']
    for stage,data,wanted in [('generation',portable_gen,wanted_gen),('chain',portable_chain,wanted_chain)]:
        rels=['kernel413/'+stage+'-runner.cpp','kernel413/libipa/tmc11_generation.cpp']
        if stage=='chain':rels+=['kernel412/libipa/tmc11_ltm.cpp','kernel409/libipa/ltm_adrc.cpp']
        if arch=='host':
            binary=P/('dynamic-'+stage+'-host');command=['g++',*flags,'-fsanitize=address,undefined','-no-pie',*[str(HERE.parent/n) for n in rels],'-o',str(binary)];launch=[str(binary)]
        else:
            binary='/private/camss414-dynamic/'+stage+'-aarch64';command=['chroot',str(sdk),'g++',*flags,*['/private/camss414-dynamic/'+n for n in rels],'-o',binary];launch=['chroot',str(sdk),binary]
        q=subprocess.run(command,capture_output=True);assert not q.returncode,q.stderr.decode()
        q=subprocess.run(launch,input=data,capture_output=True,timeout=45);assert not q.returncode,q.stderr.decode()
        (P/('dynamic-'+stage+'-'+arch+'-actual-private.bin')).write_bytes(q.stdout)
        assert q.stdout==wanted,(arch,stage,len(q.stdout),sum(a!=b for a,b in zip(q.stdout,wanted)))
    rows.append(dict(architecture=arch,cases=len(chosen),compared_tree_bytes=len(wanted_tree),
        compared_generation_bytes=len(wanted_gen),compared_chain_bytes=len(wanted_chain),different_bytes=0,passed=True))
    print(json.dumps(rows[-1]),flush=True)
storage=module('storage284',HERE.parent/'kernel284/storage.py');kernel=storage.mounted_build().parent/'source354'
prior=json.loads((HERE.parent/'kernel413/source-state.json').read_text())
assert subprocess.check_output(['git','-C',str(kernel),'rev-parse','HEAD'],text=True).strip()==prior['commit']
assert not subprocess.check_output(['git','-C',str(kernel),'status','--porcelain'])
native=kernel/'drivers/media/platform/qcom/camss'
assert (P.parent/'kernel405/colour.c').read_bytes()==(native/'camss-icp-a5-colour.c').read_bytes()
assert (P.parent/'kernel405/include/camss-icp-a5-colour.h').read_bytes()==(native/'camss-icp-a5-colour.h').read_bytes()
codec=ctypes.CDLL(str(P.parent/'kernel409/current-colour-codec.so'));encode=codec.camss_a5_ipe_encode_ltm_iq
encode.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p];encode.restype=ctypes.c_int
for at in range(0,len(gold),512):
    lut=gold[at:at+512];typed=bytearray(2800);struct.pack_into('<I',typed,84,1)
    for family,offset in [(0,624),(1,880)]:
        for n,word in enumerate(struct.unpack_from('<64I',lut,family*256)):
            base=word&4095;delta=(word>>12)&4095
            if delta&2048:delta-=4096
            if family:
                if base&2048:base-=4096
                struct.pack_into('<hh',typed,offset+n*4,base,delta)
            else:struct.pack_into('<Hh',typed,offset+n*4,base,delta)
    request=ctypes.create_string_buffer(bytes(typed));out=ctypes.create_string_buffer(bytes([0xa7])*9008)
    assert not encode(out,9008,0x7802000,None,None,request)
    assert out.raw[6768:7280]==lut and request.raw[:2800]==typed and out.raw[8944:9008]==bytes([0xa7])*64
result=dict(stage=414,cases=len(chosen),factory_roots=68,root_enable_unchanged_numeric_fixtures_only=True,
    actual_gap_interpolation_cases=sum(any(0<n['ratio']<1 for n in metadata[i]['target_nodes']) for i in chosen),
    chain_success_cases=sum(status),rejected_nonfinite_generation_cases=rejected_nonfinite,
    rejected_finite_subunity_cases=rejected_subunity,native_typed_lut_bytes=len(gold),different_bytes=0,
    actual_target_interpolation_gold_reused=True,original_generation_instructions=generation.instructions,
    original_generation_providers=generation.providers,original_sampling_instructions=sample.instructions,
    original_sampling_providers=sample.providers,original_adrc_instructions=adrc.instructions,original_adrc_providers=adrc.providers,
    logf_expf_powf_host_libm_not_target_bionic=True,source_final_packer_not_original_hal_final_packer=True,
    portable_tree_output_feeds_generation_and_lut_chain=True,separate_process_stages_not_runtime_integration=True,
    statistics_synthetic_not_device_samples=True,maintained_kernel_clean_unchanged_from413=True,
    architectures=rows,current_source_hashes=[dict(path=n,sha256=hashlib.sha256((HERE.parent/n).read_bytes()).hexdigest()) for n in names],
    full_ltm_numeric_math_complete=False,runtime_version_selection_verified=False,
    phone_accessed=False,new_hardware_verification=False,last_device_evidence_stage=406,
    full_goal_kept_active=True,passed=True)
(HERE/'dynamic-chain-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)
