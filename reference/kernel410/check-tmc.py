"""Check source knee/percentage policy, target sampling, and portable TMC10."""
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
setting=(P/'sources/tmc10interpolation.cpp').read_text();sampling=(P/'sources/iqsettingutil.cpp').read_text()
prefix='''#include <algorithm>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
using FLOAT=float;using BOOL=bool;using INT=int;using INT32=int32_t;using UINT32=uint32_t;
constexpr BOOL TRUE=true,FALSE=false;
constexpr FLOAT TMC10_UNIT_GAIN_STEP=1.03f,TMC10_GAIN_RATIO_MIN=1,TMC10_GAIN_RATIO_MAX=16,TMC10_DRC_GAIN_POW_X=1.03f,TMC10_MAX_LTM_GAIN=8;
constexpr INT TMC10_DRC_INDEX_MIN=94,TMC10_KNEE_POINTS_NUM=4,TMC10_COEF_NUM=6;
constexpr FLOAT MIN_NORM_OUTPUT_GAIN=0,MAX_NORM_OUTPUT_GAIN=1;
enum class SWTMCVersion{TMC10};
struct ADRC {UINT32 enable,gtmEnable,ltmEnable;SWTMCVersion version;FLOAT ltmPercentage,gtmPercentage,drcGainDark;
struct {struct{FLOAT kneeX[4],kneeY[4];} KneePointsTMC10;}kneePoints;FLOAT coefficient[6];};
struct Chromatix {struct{UINT32 adrc_isp_enable;}enable_section;struct{UINT32 use_gtm,use_ltm;}chromatix_tmc10_reserve;};
struct TMC10InputData {FLOAT drcGain,drcGainDark;ADRC *pAdrcOutputData;Chromatix *pChromatix;};
namespace tmc_1_0_0{struct tmc10_rgn_dataType{FLOAT gtm_percentage,ltm_percentage,knee_out_mid,dark_boost_ratio,core_rsv_para1;};}
struct IQSettingUtils {
static UINT32 MinUINT32(UINT32 a,UINT32 b){return std::min(a,b);}
static FLOAT ClampFLOAT(FLOAT v,FLOAT a,FLOAT b){return v<a?a:(v>b?b:v);}
static BOOL FEqual(FLOAT a,FLOAT b){return fabs(a-b)<1e-9;}
static BOOL FEqualCoarse(FLOAT a,FLOAT b,FLOAT d){return fabsf(a-b)<d;}
static FLOAT AbsoluteFLOAT(FLOAT v){return fabsf(v);}
static void *Memcpy(void *a,const void*b,size_t n){return memcpy(a,b,n);}
static BOOL GainCurveSampling(FLOAT*,FLOAT*,FLOAT*,const FLOAT*,FLOAT*,UINT32,FLOAT,FLOAT,UINT32);
};
struct TMC10Interpolation {static BOOL CalculateKneePoints(FLOAT*,FLOAT*,FLOAT*);static BOOL CalcGainCurve(const TMC10InputData*,tmc_1_0_0::tmc10_rgn_dataType*);};
'''
oracle=prefix+function(setting,'BOOL TMC10Interpolation::CalculateKneePoints(')+'\n'+function(setting,'BOOL TMC10Interpolation::CalcGainCurve(')+'\n'+function(sampling,'BOOL IQSettingUtils::GainCurveSampling(')
oracle+='''
struct Record{FLOAT p[7],equivalent[65];};struct Curve{FLOAT x[4],y[4],c[6],dark,ltm,gtm,mix;};
int main(){Record r;while(fread(&r,sizeof r,1,stdin)==1){ADRC a{};Chromatix ch{{1},{1,1}};TMC10InputData in{r.p[0],r.p[1],&a,&ch};tmc_1_0_0::tmc10_rgn_dataType d{r.p[2],r.p[3],r.p[4],r.p[5],r.p[6]};
TMC10Interpolation::CalcGainCurve(&in,&d);Curve c;memcpy(c.x,a.kneePoints.KneePointsTMC10.kneeX,16);memcpy(c.y,a.kneePoints.KneePointsTMC10.kneeY,16);memcpy(c.c,a.coefficient,24);c.dark=a.drcGainDark;c.ltm=a.ltmPercentage;c.gtm=a.gtmPercentage;c.mix=IQSettingUtils::ClampFLOAT(2-c.dark,0,1);
UINT32 ok=1;const FLOAT *raw=reinterpret_cast<const FLOAT*>(&c);for(int i=0;i<18;i++)if(!std::isfinite(raw[i]))ok=0;
FLOAT out[65];memset(out,0xa5,sizeof out);if(ok)IQSettingUtils::GainCurveSampling(c.x,c.y,c.c,r.equivalent,out,64,c.ltm,c.dark,10);UINT32 sampled=ok;for(FLOAT v:out)if(!std::isfinite(v))sampled=0;
if(!ok){memset(&c,0xa5,sizeof c);}
if(!sampled){memset(out,0xa5,sizeof out);}
assert(fwrite(&ok,4,1,stdout)==1&&fwrite(&c,sizeof c,1,stdout)==1&&fwrite(&sampled,4,1,stdout)==1&&fwrite(out,4,65,stdout)==65);
}return ferror(stdin)||ferror(stdout);}
'''
(P/'tmc-source-oracle-private.cpp').write_text(oracle)
q=subprocess.run(['g++','-std=c++17','-O2','-ffp-contract=off','-Wall','-Wextra','-Werror',str(P/'tmc-source-oracle-private.cpp'),'-o',str(P/'tmc-source-oracle')],capture_output=True)
(P/'oracle-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
inv=(P.parent/'kernel352/inverse-oracle-output-private.bin').read_bytes()
eqs=[[float((w&16383)//4) for w in struct.unpack_from('<64I',inv,i*256)]+[4095.] for i in range(29)]
records=[];labels=[]
def add(p,eq,kind):records.append(struct.pack('<72f',*(p+eq)));labels.append(dict(kind=kind))
regions=0
for name in ['qtech_s5kgw1','sunny_s5kgw1','sunny_imx471','qtech_s5k3m5sx','sunny_imx319']:
    roots=json.loads((P/(name+'-tmc10-trees-private.json')).read_text())
    for root in roots:
        for row in root['core']:
            d=row['data'];regions+=1
            for gain in [1,1.03,1.1,1.5,2,4,8,16,32,3.4028234663852886e38]:
                for dark in [1,1.00005,1.25,2,8,1e30]:
                    add([gain,dark,d['gtm_percentage'],d['ltm_percentage'],d['knee_out_mid'],d['dark_boost_ratio'],d['core_rsv_para1']],eqs[0],'factory-region-gain-grid')
assert regions==18
rng=random.Random(410)
for i in range(200):
    add([rng.uniform(1,64),rng.uniform(1,32),rng.random(),rng.random(),rng.uniform(.01,.99),rng.random(),rng.random()],eqs[i%29],'synthetic')
for knee in [0,1,1e-30,.2]:
    for pct in [0,.5,1]:
        add([1,1,1-pct,pct,knee,0,0],eqs[0],'degenerate-knee')
for i in [0,31,63]:
    for pct in [0,.5,1]:
        eq=eqs[0].copy();eq[i+1]=0
        add([2,1.2,1-pct,pct,.3,.5,0],eq,'zero-equivalent')
count=len(records);inputs=b''.join(records)
q=subprocess.run([str(P/'tmc-source-oracle')],input=inputs,capture_output=True);assert not q.returncode,q.stderr.decode()
raw_expected=q.stdout;assert len(raw_expected)==count*340
(P/'tmc-source-raw-unchecked-private.bin').write_bytes(raw_expected)
expected=bytearray(raw_expected)
invalid_anchor_cases=0
for i,record in enumerate(records):
    if struct.unpack_from('<f',record,284)[0]<=0:
        invalid_anchor_cases+=1
        struct.pack_into('<I',expected,i*340+76,0)
        expected[i*340+80:(i+1)*340]=bytes([0xa5])*260
expected=bytes(expected)
(P/'tmc-valid-input-private.bin').write_bytes(inputs);(P/'tmc-source-expected-private.bin').write_bytes(expected)
(P/'tmc-cases-private.json').write_text(json.dumps(labels,indent=2)+'\n')
target=module('tmc410',HERE/'tmc-model.py').TmcMachine()
hal_diffs=0;mix_diffs=0;sampler_calls=0;nonfinite_samples=0
for i,record in enumerate(records):
    ok=struct.unpack_from('<I',expected,i*340)[0]
    if not ok:continue
    curve=expected[i*340+4:i*340+76];gain=target.sample(curve,record[28:]);sampler_calls+=1
    dark,percentage=struct.unpack_from('<2f',curve,56)
    mix=target.mix(dark,percentage);mix_diffs+=sum(a!=b for a,b in zip(mix,curve[68:72]))
    sampled=struct.unpack_from('<I',raw_expected,i*340+76)[0]
    finite=all(math.isfinite(v) for v in struct.unpack('<65f',gain))
    assert bool(sampled)==finite,(i,'target finite classification')
    if finite:hal_diffs+=sum(a!=b for a,b in zip(gain,raw_expected[i*340+80:(i+1)*340]))
    else:nonfinite_samples+=1
    if i%300==0:print(json.dumps(dict(target_calls=sampler_calls,different_bytes=hal_diffs,mix_diff=mix_diffs)),flush=True)

invalid=[];invalid_expected=[]
for at in range(7):
    for value in [math.nan,math.inf,-1]:
        record=bytearray(records[0]);struct.pack_into('<f',record,at*4,value);invalid.append(bytes(record));invalid_expected.append(struct.pack('<I',0)+bytes([0xa5])*72+struct.pack('<I',0)+bytes([0xa5])*260)
for at,value in [(0,.5),(1,.5),*[(i,1.01) for i in range(2,7)]]:
    record=bytearray(records[0]);struct.pack_into('<f',record,at*4,value);invalid.append(bytes(record));invalid_expected.append(struct.pack('<I',0)+bytes([0xa5])*72+struct.pack('<I',0)+bytes([0xa5])*260)
for at,value in [(7,math.nan),(39,math.inf),(71,0),(10,-1),(71,-1)]:
    record=bytearray(records[0]);struct.pack_into('<f',record,at*4,value);invalid.append(bytes(record));invalid_expected.append(expected[:76]+struct.pack('<I',0)+bytes([0xa5])*260)
all_input=inputs+b''.join(invalid);wanted=expected+b''.join(invalid_expected)
(P/'tmc-input-private.bin').write_bytes(all_input);(P/'tmc-expected-private.bin').write_bytes(wanted)
sdk=Path('/home/cy122/x2pro-linux/libcamera214-root');work=sdk/'private/camss410-math'
for rel in ['tmc-runner.cpp','libipa/tmc10.cpp','libipa/tmc10.h']:
    dest=work/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(HERE/rel,dest)
rows=[]
for arch in ['host','aarch64']:
    flags=['-std=c++17','-O2','-ffp-contract=fast','-Wall','-Wextra','-Werror']
    if arch=='host':
        binary=P/'tmc-host';command=['g++',*flags,'-fsanitize=address,undefined','-no-pie',str(HERE/'tmc-runner.cpp'),str(HERE/'libipa/tmc10.cpp'),'-o',str(binary)];launch=[str(binary)]
    else:
        binary='/private/camss410-math/tmc-aarch64';command=['chroot',str(sdk),'g++',*flags,'/private/camss410-math/tmc-runner.cpp','/private/camss410-math/libipa/tmc10.cpp','-o',binary];launch=['chroot',str(sdk),binary]
    q=subprocess.run(command,capture_output=True);assert not q.returncode,q.stderr.decode()
    q=subprocess.run(launch,input=all_input,capture_output=True,timeout=45);assert not q.returncode,q.stderr.decode()
    assert len(q.stdout)==len(wanted)
    (P/(arch+'-actual-private.bin')).write_bytes(q.stdout)
    diffs=sum(a!=b for a,b in zip(q.stdout,wanted));rows.append(dict(architecture=arch,cases=count,invalid_cases=len(invalid),compared_bytes=len(wanted),different_bytes=diffs,passed=not diffs));print(json.dumps(rows[-1]),flush=True)
report=dict(stage=410,cases=count,factory_region_cases=1080,factory_regions=18,synthetic_cases=200,edge_cases=21,
    knee_and_percentage_policy_source_reference_only=True,target_knee_generation_not_executed=True,
    target_sampler_entry='0x3c6328',target_fixed_lut_size64_qfactor_w5_10=True,target_sampler_calls=sampler_calls,
    target_mix_range=['0x3626f8','0x36273c'],target_sampler_different_bytes=hal_diffs,target_mix_different_bytes=mix_diffs,
    source_and_target_nonfinite_sampling_cases=nonfinite_samples,typed_api_rejects_nonfinite_outputs_atomically=True,
    invalid_normalization_endpoint_cases=invalid_anchor_cases,
    typed_api_rejects_zero_endpoint_even_if_zero_rate_source_result_finite=True,
    original_target_instructions=target.instructions,providers=target.providers,powf_is_host_libm_not_target_bionic=True,
    architectures=rows,host_asan_ubsan=True,aarch64_sdk_qemu=True,fp_contract_fast=True,
    input_records_unchanged=True,disabled_roots_not_enabled=True,tmc11_and_runtime_version_selection_unverified=True,
    aec_trigger_interpolation_not_implemented_here=True,phone_accessed=False,full_goal_kept_active=True,
    passed=not hal_diffs and not mix_diffs and all(r['passed'] for r in rows))
path=HERE/'tmc-validation.json'
if path.exists() and not json.loads(path.read_text())['passed'] and not (HERE/'tmc-r1-validation.json').exists():(HERE/'tmc-r1-validation.json').write_bytes(path.read_bytes())
path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True);assert report['passed']
