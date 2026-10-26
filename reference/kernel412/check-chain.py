"""Connect target TMC11 PCHIP/contrast gains to ADRC and native typed LUTs."""
from pathlib import Path
import ctypes,hashlib,importlib.util,json,math,shutil,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
report=json.loads((HERE/'sampling-validation.json').read_text());assert report['passed']
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);out=importlib.util.module_from_spec(spec);spec.loader.exec_module(out);return out
adrc=module('adrc409',HERE.parent/'kernel409/adrc-model.py').AdrcMachine()
source=(P/'sampling-valid-input-private.bin').read_bytes();sampled=(P/'sampling-expected-private.bin').read_bytes()
variants=['qtech_s5kgw1','sunny_s5kgw1','sunny_imx471','qtech_s5k3m5sx','sunny_imx319']
case_variants=json.loads((P/'sampling-variants-private.json').read_text())
assert len(case_variants)==report['cases'] and len(source)==report['cases']*8540
profiles=json.loads((P.parent/'kernel351/mode-profiles-private.json').read_text())
old_cases=json.loads((P.parent/'kernel407/curve-cases-private.json').read_text());old_curves=(P.parent/'kernel407/curves-host-output-private.bin').read_bytes()
fixed={}
for name in variants:
    if name in profiles:selected=next(p for p in profiles[name] if p['usecase']=='Preview')['modules']['ltm13_ipe']
    else:selected=next(r for r in json.loads((P.parent/'kernel351'/(name+'-ltm13_ipe-trees-private.json')).read_text()) if r['uid']==42)
    index=next(i for i,c in enumerate(old_cases) if c.get('variant')==name and c.get('uid')==selected['uid'])
    scales=[int(math.copysign(math.floor(abs(v)+.5),v)) for v in struct.unpack_from('<65f',old_curves,index*788+8)]
    fixed[name]=(selected['reserve']['ltm_curve_tab'],scales)
gamma=(P.parent/'kernel348/factory-gamma-private.bin').read_bytes()
forward=[float(struct.unpack_from('<H',gamma,8+256+i*4)[0]) for i in range(64)]
forward.append(forward[-1]+struct.unpack_from('<h',gamma,8+256+63*4+2)[0])
records=[];status=[];oracle_records=[];success_indices=[];subunity=0
for i,name in enumerate(case_variants):
    raw=source[i*8540:(i+1)*8540];curve,scale=fixed[name]
    record=raw+struct.pack('<65f65i65h2x',*forward,*curve,*scale);assert len(record)==9192;records.append(record)
    assert struct.unpack_from('<I',sampled,i*796+532)[0]==1
    gains=struct.unpack_from('<65f',sampled,i*796+536)
    if gains[0]<1024:status.append(False);subunity+=1;continue
    mix=struct.unpack_from('<f',sampled,i*796+528)[0]
    r=raw[:260]+struct.pack('<65f65ff65i65h2x',*gains,*forward,mix,*curve,*scale);assert len(r)==1176
    output,_=adrc.evaluate(r);blend=output[528:918]
    oracle_records.append(struct.pack('<2I65i',0,64,*struct.unpack_from('<65i',blend))+
        struct.pack('<2I65i',1,64,*struct.unpack_from('<65h',blend,260)))
    success_indices.append(i);status.append(True)
    if i%250==0:print('target ADRC after TMC11',len(success_indices),flush=True)
q=subprocess.run([str(P.parent/'kernel405/original-packers-private')],input=b''.join(oracle_records),capture_output=True);assert not q.returncode,q.stderr.decode()
gold=q.stdout;assert len(gold)==len(success_indices)*512
expected=[];j=0
for ok in status:
    expected.append(struct.pack('<I',ok)+(gold[j*512:(j+1)*512] if ok else bytes([0xa5])*512));j+=ok
inputs=b''.join(records);wanted=b''.join(expected)
(P/'chain-input-private.bin').write_bytes(inputs);(P/'chain-expected-private.bin').write_bytes(wanted)
sdk=Path('/home/cy122/x2pro-linux/libcamera214-root');work=sdk/'private/camss412-chain'
names=['kernel412/chain-runner.cpp','kernel412/libipa/tmc11_ltm.cpp','kernel412/libipa/tmc11_ltm.h','kernel409/libipa/ltm_adrc.cpp','kernel409/libipa/ltm_adrc.h']
for name in names:
    dest=work/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(HERE.parent/name,dest)
rows=[]
for arch in ['host','aarch64']:
    rels=[n for n in names if n.endswith('.cpp')];flags=['-std=c++17','-O2','-ffp-contract=fast','-Wall','-Wextra','-Werror']
    if arch=='host':
        binary=P/'chain-host';command=['g++',*flags,'-fsanitize=address,undefined','-no-pie',*[str(HERE.parent/n) for n in rels],'-o',str(binary)];launch=[str(binary)]
    else:
        binary='/private/camss412-chain/chain-aarch64';command=['chroot',str(sdk),'g++',*flags,*['/private/camss412-chain/'+n for n in rels],'-o',binary];launch=['chroot',str(sdk),binary]
    q=subprocess.run(command,capture_output=True);assert not q.returncode,q.stderr.decode()
    q=subprocess.run(launch,input=inputs,capture_output=True,timeout=45);assert not q.returncode,q.stderr.decode()
    (P/('chain-'+arch+'-actual-private.bin')).write_bytes(q.stdout);assert q.stdout==wanted,(arch,sum(a!=b for a,b in zip(q.stdout,wanted)))
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
result=dict(stage=412,cases=len(records),successful_boost_chain_cases=len(success_indices),rejected_finite_subunity_cases=subunity,
    target_normalization_pchip_contrast_feeds_actual_target_adrc=True,target_adrc_instructions=adrc.instructions,target_adrc_providers=adrc.providers,
    architectures=rows,native_typed_lut_cases=len(success_indices),compared_lut_bytes=len(gold),different_bytes=0,
    maintained_native_codec_reused_from_verified409=True,other_iq_luts_zero_not_full_pipeline=True,
    knees_source_anchor_fixtures_and_histogram_curves_synthetic_not_runtime=True,disabled_roots_not_activated=True,
    qtech_gw1_unbound_supplier_variant_is_numeric_fixture_only=True,
    current_source_hashes=[dict(path=n,sha256=hashlib.sha256((HERE.parent/n).read_bytes()).hexdigest()) for n in names],
    phone_accessed=False,full_goal_kept_active=True,passed=True)
(HERE/'chain-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
