"""Connect TMC10-derived gains through target ADRC and native typed LUTs."""
from pathlib import Path
import ctypes,hashlib,importlib.util,json,math,shutil,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
report=json.loads((HERE/'tmc-validation.json').read_text());assert report['passed']
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);out=importlib.util.module_from_spec(spec);spec.loader.exec_module(out);return out
adrc=module('adrc409',HERE.parent/'kernel409/adrc-model.py').AdrcMachine()
source=(P/'tmc-valid-input-private.bin').read_bytes();tmc=(P/'tmc-source-expected-private.bin').read_bytes()
gamma=(P.parent/'kernel348/factory-gamma-private.bin').read_bytes()
forward=[float(struct.unpack_from('<H',gamma,8+256+i*4)[0]) for i in range(64)]
forward.append(forward[-1]+struct.unpack_from('<h',gamma,8+256+63*4+2)[0])
variants=['qtech_s5kgw1','sunny_s5kgw1','sunny_imx471','qtech_s5k3m5sx','sunny_imx319']
region_variant=[name for name in variants for _ in json.loads((P/(name+'-tmc10-trees-private.json')).read_text())[0]['core']]
profiles=json.loads((P.parent/'kernel351/mode-profiles-private.json').read_text())
old_cases=json.loads((P.parent/'kernel407/curve-cases-private.json').read_text());old_curves=(P.parent/'kernel407/curves-host-output-private.bin').read_bytes()
fixed={}
for name in variants:
    if name in profiles:
        selected=next(p for p in profiles[name] if p['usecase']=='Preview')['modules']['ltm13_ipe']
    else:
        # This supplier variant is retained for numeric checks, not bound
        # to an extra physical camera or assigned another supplier's mode.
        roots=json.loads((P.parent/'kernel351'/(name+'-ltm13_ipe-trees-private.json')).read_text())
        selected=next(r for r in roots if r['uid']==42)
    uid=selected['uid'];index=next(i for i,c in enumerate(old_cases) if c.get('variant')==name and c.get('uid')==uid)
    values=struct.unpack_from('<65f',old_curves,index*788+8)
    scales=[int(math.copysign(math.floor(abs(v)+.5),v)) for v in values]
    fixed[name]=(selected['reserve']['ltm_curve_tab'],scales)
records=[];oracle_records=[];success_indices=[];status=[];rejected_nonboost=0
for i in range(report['cases']):
    name=region_variant[i//60] if i<1080 else variants[i%5]
    curve,scale=fixed[name];raw=source[i*288:(i+1)*288]
    record=raw+struct.pack('<65f65i65h2x',*forward,*curve,*scale);assert len(record)==940;records.append(record)
    sampled=struct.unpack_from('<I',tmc,i*340+76)[0]
    if not sampled:
        status.append(False);continue
    gain=list(struct.unpack_from('<65f',tmc,i*340+80))
    if gain[0]<1024:
        rejected_nonboost+=1;status.append(False);continue
    mix=struct.unpack_from('<f',tmc,i*340+72)[0]
    r=raw[28:]+struct.pack('<65f65ff65i65h2x',*gain,*forward,mix,*curve,*scale)
    assert len(r)==1176
    output,_=adrc.evaluate(r)
    blended=output[528:918]
    oracle_records.append(struct.pack('<2I65i',0,64,*struct.unpack_from('<65i',blended))+
                          struct.pack('<2I65i',1,64,*struct.unpack_from('<65h',blended,260)))
    success_indices.append(i);status.append(True)
    if i%350==0:print(json.dumps(dict(target_adrc_cases=len(success_indices))),flush=True)
q=subprocess.run([str(P.parent/'kernel405/original-packers-private')],input=b''.join(oracle_records),capture_output=True);assert not q.returncode,q.stderr.decode()
gold=q.stdout;assert len(gold)==len(success_indices)*512
expected=[];j=0
for ok in status:
    expected.append(struct.pack('<I',ok)+(gold[j*512:(j+1)*512] if ok else bytes([0xa5])*512));j+=ok
inputs=b''.join(records);wanted=b''.join(expected)
(P/'chain-input-private.bin').write_bytes(inputs);(P/'chain-expected-private.bin').write_bytes(wanted)
sdk=Path('/home/cy122/x2pro-linux/libcamera214-root');work=sdk/'private/camss410-chain'
names=['kernel410/chain-runner.cpp','kernel410/libipa/tmc10.cpp','kernel410/libipa/tmc10.h','kernel409/libipa/ltm_adrc.cpp','kernel409/libipa/ltm_adrc.h']
for name in names:
    dest=work/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(HERE.parent/name,dest)
rows=[]
for arch in ['host','aarch64']:
    rels=['kernel410/chain-runner.cpp','kernel410/libipa/tmc10.cpp','kernel409/libipa/ltm_adrc.cpp'];flags=['-std=c++17','-O2','-ffp-contract=fast','-Wall','-Wextra','-Werror']
    if arch=='host':
        binary=P/'chain-host';command=['g++',*flags,'-fsanitize=address,undefined','-no-pie',*[str(HERE.parent/n) for n in rels],'-o',str(binary)];launch=[str(binary)]
    else:
        binary='/private/camss410-chain/chain-aarch64';command=['chroot',str(sdk),'g++',*flags,*['/private/camss410-chain/'+n for n in rels],'-o',binary];launch=['chroot',str(sdk),binary]
    q=subprocess.run(command,capture_output=True);assert not q.returncode,q.stderr.decode()
    q=subprocess.run(launch,input=inputs,capture_output=True,timeout=45);assert not q.returncode,q.stderr.decode()
    (P/('chain-'+arch+'-actual-private.bin')).write_bytes(q.stdout)
    assert q.stdout==wanted,(arch,sum(a!=b for a,b in zip(q.stdout,wanted)))
    rows.append(dict(architecture=arch,cases=len(records),passed=True));print(json.dumps(rows[-1]),flush=True)
storage=module('storage284',HERE.parent/'kernel284/storage.py');kernel=storage.mounted_build().parent/'source354/drivers/media/platform/qcom/camss'
assert (P.parent/'kernel405/colour.c').read_bytes()==(kernel/'camss-icp-a5-colour.c').read_bytes()
assert (P.parent/'kernel405/include/camss-icp-a5-colour.h').read_bytes()==(kernel/'camss-icp-a5-colour.h').read_bytes()
lib=ctypes.CDLL(str(P.parent/'kernel409/current-colour-codec.so'));encode=lib.camss_a5_ipe_encode_ltm_iq
encode.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p];encode.restype=ctypes.c_int
for i in range(len(success_indices)):
    lut=gold[i*512:(i+1)*512];typed=bytearray(2800);struct.pack_into('<I',typed,84,1)
    for family,at in [(0,624),(1,880)]:
        for n,word in enumerate(struct.unpack_from('<64I',lut,family*256)):
            base=word&4095;delta=(word>>12)&4095
            if delta&2048:delta-=4096
            if family:
                if base&2048:base-=4096
                struct.pack_into('<hh',typed,at+n*4,base,delta)
            else:struct.pack_into('<Hh',typed,at+n*4,base,delta)
    request=ctypes.create_string_buffer(bytes(typed));out=ctypes.create_string_buffer(bytes([0xa7])*9008)
    assert not encode(out,9008,0x7802000,None,None,request)
    assert out.raw[6768:7280]==lut and request.raw[:2800]==typed and out.raw[8944:9008]==bytes([0xa7])*64
result=dict(stage=410,cases=len(records),successful_boost_chain_cases=len(success_indices),rejected_cases=len(records)-len(success_indices),
    rejected_finite_subunity_gain_cases=rejected_nonboost,architectures=rows,
    tmc_source_generated_knees_and_target_verified_sampling_feeds_actual_target_adrc=True,
    target_adrc_instructions=adrc.instructions,target_adrc_providers=adrc.providers,
    native_typed_lut_cases=len(success_indices),compared_lut_bytes=len(gold),different_bytes=0,
    maintained_native_codec_reused_from_verified409=True,other_iq_luts_zero_not_full_pipeline=True,
    numeric_chain_only_disabled_roots_not_activated=True,tmc11_and_version_selection_not_implemented=True,
    qtech_gw1_unbound_supplier_variant_is_numeric_fixture_only=True,
    current_source_hashes=[dict(path=n,sha256=hashlib.sha256((HERE.parent/n).read_bytes()).hexdigest()) for n in names],
    phone_accessed=False,full_goal_kept_active=True,passed=True)
(HERE/'chain-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
