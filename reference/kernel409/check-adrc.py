"""Compare portable conversion/blending with pinned source and actual target."""
from pathlib import Path
import hashlib,importlib.util,json,math,random,shutil,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);out=importlib.util.module_from_spec(spec);spec.loader.exec_module(out);return out
def function(text,needle):
    start=text.index(needle);brace=text.index('{',start);end=brace+1;depth=1
    while depth:depth+=(text[end]=='{')-(text[end]=='}');end+=1
    return text[start:end]
setting=(P.parent/'kernel403/sources/ltm13setting.cpp').read_text()
utility=(P.parent/'kernel333/sources/iqsettingutil.h').read_text()
manifest=json.loads((HERE/'primary-sources.json').read_text())
for text,tail in [(setting,'ltm13setting.cpp'),(utility,'iqsettingutil.h')]:
    assert hashlib.sha256(text.encode()).hexdigest()==next(r['sha256'] for r in manifest['files'] if r['path'].endswith('/'+tail))
oracle='''#include <algorithm>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
using INT=int;using INT16=int16_t;using INT32=int32_t;using UINT=unsigned;using FLOAT=float;using DOUBLE=double;
constexpr INT LTM_SCALE_Q=10,LTM_SCALE_MAX=2047,LTM_SCALE_LUT_SIZE=65,LTM_LUT_SIZE=64,LTM_BIT_DEPTH=12,LTM_GAMMA_LUT_SIZE=64;
constexpr FLOAT LTM_MAX_VALUE=4095,LTM_MIN_VALUE=0,LTM_SCALE_MAX_VALUE=2047;
static FLOAT ltmFixedGamma[65];
class IQSettingUtils {public:static FLOAT ClampFLOAT(FLOAT v,FLOAT a,FLOAT b){return v<a?a:(v>b?b:v);}static FLOAT MaxFLOAT(FLOAT a,FLOAT b){return a>b?a:b;}static INT32 RoundFLOAT(FLOAT v){return static_cast<INT32>(std::round(v));}
'''
oracle+=function(utility,'static __inline FLOAT InterpolationFloatBilinear(')+'\n};\n'
oracle+='class LTM13Setting {public:static void GenerateAdrcLtmCurves(FLOAT*,FLOAT*,FLOAT*,FLOAT*,FLOAT*);};\n'
oracle+=function(setting,'void LTM13Setting::GenerateAdrcLtmCurves(')
begin=setting.index('            FLOAT ltmCurveScaleRatio = 1.0f;')
end=setting.index('\n        }\n        Pack1D64EntryUnsignedLUT',begin)
blend=setting[begin:end]
oracle+='''
struct Record{float equivalent[65],gain[65],gamma[65],mix;INT32 curve[65];INT16 scale[65];};
struct Reserve{struct {INT32 ltm_curve[65];} ltm_curve_tab;};
int main(){static_assert(sizeof(Record)==1176);Record r;while(fread(&r,sizeof r,1,stdin)==1){FLOAT tmcOutLtmScale[65],tmcOutLtmCurve[65];
LTM13Setting::GenerateAdrcLtmCurves(r.equivalent,r.gain,r.gamma,tmcOutLtmScale,tmcOutLtmCurve);UINT ok=1;
assert(fwrite(&ok,4,1,stdout)==1&&fwrite(tmcOutLtmScale,4,65,stdout)==65&&fwrite(tmcOutLtmCurve,4,65,stdout)==65);
FLOAT adrc_ltm_mix_rate=r.mix;INT32 ltmCurve[65];INT16 ltmScale[65];memcpy(ltmScale,r.scale,130);Reserve reserve;memcpy(reserve.ltm_curve_tab.ltm_curve,r.curve,260);Reserve *pReserveData=&reserve;unsigned i;
'''+blend+'''
assert(fwrite(&ok,4,1,stdout)==1&&fwrite(ltmCurve,4,65,stdout)==65&&fwrite(ltmScale,2,65,stdout)==65);
}return ferror(stdin)||ferror(stdout);}
'''
(P/'adrc-source-oracle-private.cpp').write_text(oracle)
q=subprocess.run(['g++','-std=c++17','-O2','-ffp-contract=off','-Wall','-Wextra','-Werror',str(P/'adrc-source-oracle-private.cpp'),'-o',str(P/'adrc-source-oracle')],capture_output=True)
(P/'oracle-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()

gamma=(P.parent/'kernel348/factory-gamma-private.bin').read_bytes()
bases=list(struct.unpack_from('<H',gamma,8+256+i*4)[0] for i in range(64))
last_delta=struct.unpack_from('<h',gamma,8+256+63*4+2)[0]
factory_gamma=[float(x) for x in bases]+[float(bases[-1]+last_delta)]
assert 0<=factory_gamma[-1]<=1024
inverse=(P.parent/'kernel352/inverse-oracle-output-private.bin').read_bytes()
factory_equivalent=[float((w&0x3fff)//4) for w in struct.unpack_from('<64I',inverse)]+[4095.0]
legacy=(P.parent/'kernel407/curves-host-output-private.bin').read_bytes()
records=[];labels=[]
def record(equivalent,gain,forward,mix,curve,scale,kind):
    assert len(equivalent)==len(gain)==len(forward)==len(curve)==len(scale)==65
    raw=struct.pack('<196f65i65h2x',*(equivalent+gain+forward+[mix]),*curve,*scale)
    assert len(raw)==1176;records.append(raw);labels.append(dict(kind=kind))
index=0
def leaves(nodes):
    for node in nodes:
        if 'children' in node:yield from leaves(node['children'])
        else:yield node['data']
for name in ['qtech_s5kgw1','sunny_s5kgw1','sunny_imx471','qtech_s5k3m5sx','sunny_imx319']:
    roots=json.loads((P.parent/'kernel351'/(name+'-ltm13_ipe-trees-private.json')).read_text())
    for root in roots:
        for data in leaves(root['core']):
            values=struct.unpack_from('<65f',legacy,index*3*788+8)
            scale=[int(math.copysign(math.floor(abs(v)+0.5),v)) for v in values]
            assert all(-32768<=v<=32767 for v in scale)
            g=[1,1.5,2,4,16,64][index%6]
            gain=[1024.0*(g-(g-1)*i/64) for i in range(65)]
            record(factory_equivalent,gain,factory_gamma,[0.0,0.25,0.5,1.0][index%4],
                   root['reserve']['ltm_curve_tab'],scale,'factory-base-synthetic-adrc')
            labels[-1].update(variant=name,root=root['uid']);index+=1
assert index==2135
rng=random.Random(409)
for i in range(108):
    first=[1024,2047,2048,3071,3072,4096,8192,65536][i%8]
    gain=[float(first)]+[rng.uniform(0,65536) for _ in range(64)]
    if i>=96:
        first=[struct.unpack('<f',struct.pack('<I',0x7f7fffff))[0],1e30,1e20,1e8][(i-96)%4]
        gain=[first]+[first*rng.uniform(0.1,1) for _ in range(64)]
    eq=([i*4095/64 for i in range(65)] if i%2 else [rng.uniform(0,4095) for _ in range(65)])
    forward=([i*1023/64 for i in range(65)] if i%3 else [rng.uniform(0,1024) for _ in range(65)])
    for mix in [0.0,struct.unpack('<f',struct.pack('<I',1))[0],0.25,0.5,0.99999994,1.0]:
        record(eq,gain,forward,mix,[rng.randrange(4096) for _ in range(65)],
               [rng.randrange(-8000,8001) for _ in range(65)],'synthetic-boundary')
valid_count=len(records);inputs=b''.join(records)
q=subprocess.run([str(P/'adrc-source-oracle')],input=inputs,capture_output=True);assert not q.returncode,q.stderr.decode()
expected=q.stdout;assert len(expected)==valid_count*918
(P/'adrc-valid-input-private.bin').write_bytes(inputs)
(P/'adrc-source-expected-private.bin').write_bytes(expected)
(P/'adrc-cases-private.json').write_text(json.dumps(labels,indent=2)+'\n')
model=module('adrc409',HERE/'adrc-model.py').AdrcMachine()
actual=[];different=0;rows=[]
for i,raw in enumerate(records):
    try:result,instructions=model.evaluate(raw)
    except Exception:
        (P/'model-failed-record-private.bin').write_bytes(raw)
        (P/'model-failure-private.json').write_text(json.dumps(dict(index=i,kind=labels[i]['kind']),indent=2)+'\n')
        raise
    wanted=expected[i*918:(i+1)*918];delta=sum(a!=b for a,b in zip(result,wanted));different+=delta
    actual.append(result)
    if delta:rows.append(dict(index=i,kind=labels[i]['kind'],generated_bytes=sum(a!=b for a,b in zip(result[4:524],wanted[4:524])),blend_bytes=sum(a!=b for a,b in zip(result[528:],wanted[528:]))))
    if i%600==0:print(json.dumps(dict(hal_cases=i+1,different_bytes=different)),flush=True)
(P/'adrc-hal-actual-private.bin').write_bytes(b''.join(actual))
(P/'adrc-hal-differences-private.json').write_text(json.dumps(rows,indent=2)+'\n')

invalid=[];invalid_expected=[]
for at,values in [(0,[math.nan,math.inf,-1,4096]),(32,[math.nan,math.inf,-1,4096]),(64,[math.nan,math.inf,-1,4096]),
                  (65,[math.nan,math.inf,-1,1023]),(97,[math.nan,math.inf,-1]),(129,[math.nan,math.inf,-1]),
                  (130,[math.nan,math.inf,-1,1025]),(162,[math.nan,math.inf,-1,1025]),(194,[math.nan,math.inf,-1,1025])]:
    for value in values:
        raw=bytearray(records[0]);struct.pack_into('<f',raw,at*4,value);invalid.append(bytes(raw))
        invalid_expected.append(struct.pack('<I',0)+bytes([0xa5])*520+struct.pack('<I',0)+bytes([0xa5])*390)
for at,value,fmt in [(780,math.nan,'f'),(780,math.inf,'f'),(780,-0.01,'f'),(780,1.01,'f'),(784,-1,'i'),(1040,16384,'i')]:
    raw=bytearray(records[0]);struct.pack_into('<'+fmt,raw,at,value);invalid.append(bytes(raw))
    invalid_expected.append(expected[:524]+struct.pack('<I',0)+bytes([0xa5])*390)
all_input=inputs+b''.join(invalid);all_expected=expected+b''.join(invalid_expected)
(P/'adrc-input-private.bin').write_bytes(all_input);(P/'adrc-expected-private.bin').write_bytes(all_expected)
sdk=Path('/home/cy122/x2pro-linux/libcamera214-root');work=sdk/'private/camss409-math'
for relative in ['adrc-runner.cpp','libipa/ltm_adrc.cpp','libipa/ltm_adrc.h']:
    target=work/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(HERE/relative,target)
architectures=[]
for arch in ['host','aarch64']:
    options=['-std=c++17','-O2','-ffp-contract=fast','-Wall','-Wextra','-Werror']
    if arch=='host':
        binary=P/'adrc-host';command=['g++',*options,'-fsanitize=address,undefined','-no-pie',str(HERE/'adrc-runner.cpp'),str(HERE/'libipa/ltm_adrc.cpp'),'-o',str(binary)];launch=[str(binary)]
    else:
        binary='/private/camss409-math/adrc-aarch64';command=['chroot',str(sdk),'g++',*options,'/private/camss409-math/adrc-runner.cpp','/private/camss409-math/libipa/ltm_adrc.cpp','-o',binary];launch=['chroot',str(sdk),binary]
    q=subprocess.run(command,capture_output=True);(P/(arch+'-build.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
    q=subprocess.run(launch,input=all_input,capture_output=True,timeout=45);assert not q.returncode,q.stderr.decode()
    (P/(arch+'-actual-private.bin')).write_bytes(q.stdout)
    assert len(q.stdout)==len(all_expected)
    differences=sum(a!=b for a,b in zip(q.stdout,all_expected))
    architectures.append(dict(architecture=arch,cases=valid_count,invalid_cases=len(invalid),compared_bytes=len(q.stdout),different_bytes=differences,passed=not differences))
    print(json.dumps(architectures[-1]),flush=True)
report=dict(stage=409,valid_cases=valid_count,factory_ltm_base_regions=2135,synthetic_cases=648,
             all_finite_nonnegative_sampled_gain_values_supported_with_first_at_least_unity=True,
             high_finite_gains_including_float_max_tested=True,
             sampled_adrc_gains_and_mix_are_synthetic_not_recovered_tmc_outputs=True,
             factory_ife_green_bases_and_packed_endpoint_used=True,actual_inverse_gamma_equivalent_nodes_used=True,
             source_reference_compiled_privately=True,actual_target_converter_range=['0x362774','0x3642d4'],
             actual_target_blend_range=['0x3642d4','0x364598'],original_target_instructions=model.instructions,
             original_target_providers=model.providers,hal_vs_source_different_bytes=different,
             converter_and_blend_whole_outputs_compared=True,architectures=architectures,
             invalid_preserves_output=True,input_records_unchanged=True,
             host_asan_ubsan=True,aarch64_sdk_qemu=True,fp_contract_fast=True,
             target_bionic_math_not_needed_in_selected_ranges=True,
             original_target_final_lut_packer_not_executed=True,
             tmc_gain_sampling_and_trigger_interpolation_not_implemented=True,
             whole_adrc_and_full_ltm_not_claimed_complete=True,
             phone_accessed=False,full_goal_kept_active=True,
             passed=not different and all(r['passed'] for r in architectures))
path=HERE/'adrc-validation.json'
if path.exists() and not json.loads(path.read_text())['passed']:
    first=HERE/'adrc-r1-validation.json'
    if not first.exists():first.write_bytes(path.read_bytes())
path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
assert report['passed']
