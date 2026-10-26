"""Check actual TMC11 model2 normalization/PCHIP/contrast and portable code."""
from pathlib import Path
import hashlib,importlib.util,json,math,shutil,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('tmc11target',HERE/'tmc11-model.py')
k=importlib.util.module_from_spec(spec);spec.loader.exec_module(k);target=k.Tmc11Machine()
axis=target.axis();axis_values=struct.unpack('<1024f',axis)
assert all(a<b for a,b in zip(axis_values,axis_values[1:])) and axis_values[0]>=0 and axis_values[-1]<=1
(P/'contrast-axis-private.bin').write_bytes(axis)

def function(text,needle):
    start=text.index(needle);brace=text.index('{',start);end=brace+1;depth=1
    while depth:depth+=(text[end]=='{')-(text[end]=='}');end+=1
    return text[start:end]
source=(P/'sources/tmc11interpolation.cpp').read_text();utils=(P.parent/'kernel410/sources/iqsettingutil.cpp').read_text()
prefix='''#include <cmath>
#include <cstdio>
#include <cstring>
#include <cstdint>
using FLOAT=float;using BOOL=bool;using UINT32=uint32_t;using INT32=int32_t;
constexpr BOOL TRUE=true,FALSE=false;constexpr int TMC11_KNEE_POINTS_NUM=5,LUTSize=64;
struct ADRCData{FLOAT contrastHEBright,contrastHEDark,contrastEnhanceCurve[1024];};
const FLOAT*logBinNormalized;
struct IQSettingUtils{static FLOAT AbsoluteFLOAT(FLOAT v){return fabsf(v);}static FLOAT ClampFLOAT(FLOAT v,FLOAT a,FLOAT b){return v<a?a:(v>b?b:v);}
static BOOL PCHIPCurve(FLOAT*,FLOAT*,FLOAT*,const FLOAT*,FLOAT*,UINT32);
static void EnhanceGlobalContrast(const FLOAT*,FLOAT*,ADRCData*,FLOAT,UINT32,UINT32);};
struct TMC11Interpolation{static BOOL CalculateKneePoints(FLOAT*,FLOAT*,FLOAT*);};
'''
oracle=prefix+function(source,'BOOL TMC11Interpolation::CalculateKneePoints(')+'\n'
oracle+='''int main(){FLOAT xy[10],c[9];while(fread(xy,sizeof xy,1,stdin)==1){TMC11Interpolation::CalculateKneePoints(xy,xy+5,c);if(fwrite(c,sizeof c,1,stdout)!=1)return 2;}return ferror(stdin)||ferror(stdout);}'''
(P/'coefficient-oracle-private.cpp').write_text(oracle)
q=subprocess.run(['g++','-std=c++17','-O2','-ffp-contract=off','-Wall','-Wextra','-Werror',str(P/'coefficient-oracle-private.cpp'),'-o',str(P/'coefficient-oracle')],capture_output=True);assert not q.returncode,q.stderr.decode()
f32=lambda v:struct.unpack('<f',struct.pack('<f',v))[0]
def leaves(nodes):
    for n in nodes:
        if 'children' in n:yield from leaves(n['children'])
        else:yield n['data']
fixtures=[];regions=0
for variant in ['qtech_s5kgw1','sunny_s5kgw1','sunny_imx471','qtech_s5k3m5sx','sunny_imx319']:
    for root in json.loads((P/(variant+'-tmc11-trees-private.json')).read_text()):
        assert root['reserve']['curve_model']==2 and root['reserve']['curve_order']==5
        for data in leaves(root['core']):
            regions+=1;a=data['tone_anchors_tab']
            for gain in [1,2,8]:
                for ratio in [1,4]:
                    dy=f32(min(f32(a[2]/ratio),a[1]));x=[0,f32(dy/(gain*ratio)),f32(a[2]/gain),a[3],1];y=[0,dy,a[2],a[3],1]
                    fixtures.append(dict(xy=struct.pack('<10f',*(x+y)),percentage=data['ltm_percentage'],variant=variant))
assert regions==198
for first_y in [0,.025,.05,.09999999]:
    fixtures.append(dict(xy=struct.pack('<10f',0,.1,.25,.6,1,0,first_y,.3,.7,1),
                         percentage=.8,variant='sunny_s5kgw1'))
q=subprocess.run([str(P/'coefficient-oracle')],input=b''.join(r['xy'] for r in fixtures),capture_output=True);assert not q.returncode and len(q.stdout)==len(fixtures)*36
coefficients=q.stdout;records=[];expected=[];normalizations=[];raw_gains=[];enhanced_gains=[]
inverse=(P.parent/'kernel352/inverse-oracle-output-private.bin').read_bytes()
for i,fixture in enumerate(fixtures):
    coeff=coefficients[i*36:(i+1)*36];curve=fixture['xy']+coeff
    assert all(math.isfinite(v) for v in struct.unpack('<19f',curve)),('nonfinite fixture',i)
    offset=(i%29)*256;eq=[float((v&16383)//4) for v in struct.unpack_from('<64I',inverse,offset)]+[4095.]
    eqraw=struct.pack('<65f',*eq)
    norm,mix=target.normalize(eqraw,curve);gain=target.pchip(curve,norm)
    pattern=i%4;hist=struct.pack('<1024f',*[v if pattern==0 else (math.sqrt(v) if pattern==1 else (v*v if pattern==2 else 1)) for v in axis_values])
    controls=struct.pack('<3f',fixture['percentage'],[0,.25,1,1][pattern],[0,1,.25,1][pattern])
    enhanced=target.contrast(norm,gain,controls,hist)
    assert all(math.isfinite(v) for v in struct.unpack('<130f',gain+enhanced)),i
    raw=eqraw+curve+controls+axis+hist;assert len(raw)==8540
    out=struct.pack('<I',1)+norm+struct.pack('<I',1)+gain+mix+struct.pack('<I',1)+enhanced;assert len(out)==796
    records.append(raw);expected.append(out);normalizations.append(norm);raw_gains.append(gain);enhanced_gains.append(enhanced)
    if i%250==0:print('target TMC11 sampling',i+1,flush=True)
count=len(records)
(P/'sampling-variants-private.json').write_text(json.dumps([f['variant'] for f in fixtures])+'\n')
oracle=prefix+function(utils,'BOOL IQSettingUtils::PCHIPCurve(')+'\n'+function(utils,'void IQSettingUtils::EnhanceGlobalContrast(')
oracle+='''
struct Record{FLOAT eq[65],x[5],y[5],c[9],p[3],axis[1024],hist[1024];};
int main(){Record r;while(fread(&r,sizeof r,1,stdin)==1){FLOAT n[65],g[65];for(int i=0;i<64;++i)n[i]=(r.eq[i]+1)/4095;n[63]=n[63]>1?1:n[63];n[64]=1;
IQSettingUtils::PCHIPCurve(r.x,r.y,r.c,n,g,64);if(fwrite(g,sizeof g,1,stdout)!=1)return 2;
ADRCData a{r.p[1],r.p[2],{}};memcpy(a.contrastEnhanceCurve,r.hist,sizeof r.hist);logBinNormalized=r.axis;
IQSettingUtils::EnhanceGlobalContrast(n,g,&a,r.p[0],10,3);if(fwrite(g,sizeof g,1,stdout)!=1)return 2;}return ferror(stdin)||ferror(stdout);}
'''
(P/'sampling-source-oracle-private.cpp').write_text(oracle)
q=subprocess.run(['g++','-std=c++17','-O2','-ffp-contract=off','-Wno-unused-variable',str(P/'sampling-source-oracle-private.cpp'),'-o',str(P/'sampling-source-oracle')],capture_output=True);assert not q.returncode,q.stderr.decode()
q=subprocess.run([str(P/'sampling-source-oracle')],input=b''.join(records),capture_output=True);assert not q.returncode and len(q.stdout)==count*520
(P/'sampling-source-output-private.bin').write_bytes(q.stdout)
source_pchip_diff=sum(a!=b for i in range(count) for a,b in zip(q.stdout[i*520:i*520+260],raw_gains[i]))
source_pchip_factory_diff=sum(a!=b for i in range(1188) for a,b in zip(q.stdout[i*520:i*520+260],raw_gains[i]))
source_contrast_diff=sum(a!=b for i in range(count) for a,b in zip(q.stdout[i*520+260:(i+1)*520],enhanced_gains[i]))
assert not source_pchip_factory_diff
invalid=[];bad=[];sentinel=bytes([0xa5]);first=expected[0]
for offset,value,phase in [(0,math.nan,0),(12,-1,0),(256,0,0),(256,4094,0),(20,4096,0),
                           (264,0,1),(284,-1,1),(300,math.inf,1),(308,math.nan,1),
                           (336,-1,2),(336,1.1,2),(340,math.inf,2),(344,-1,2),
                           (348,math.nan,2),(352,math.inf,2),(348+4096,math.nan,2)]:
    raw=bytearray(records[0]);struct.pack_into('<f',raw,offset,value);invalid.append(bytes(raw))
    if phase==0:bad.append(struct.pack('<I',0)+sentinel*260+struct.pack('<I',0)+sentinel*264+struct.pack('<I',0)+sentinel*260)
    elif phase==1:bad.append(first[:264]+struct.pack('<I',0)+sentinel*264+struct.pack('<I',0)+sentinel*260)
    else:bad.append(first[:532]+struct.pack('<I',0)+sentinel*260)
inputs=b''.join(records+invalid);wanted=b''.join(expected+bad)
(P/'sampling-input-private.bin').write_bytes(inputs);(P/'sampling-expected-private.bin').write_bytes(wanted)
(P/'sampling-valid-input-private.bin').write_bytes(b''.join(records));(P/'sampling-target-normalized-private.bin').write_bytes(b''.join(normalizations))
sdk=Path('/home/cy122/x2pro-linux/libcamera214-root');work=sdk/'private/camss412-sampling'
files=['tmc11-runner.cpp','libipa/tmc11_ltm.cpp','libipa/tmc11_ltm.h']
for name in files:
    dest=work/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(HERE/name,dest)
rows=[]
for arch in ['host','aarch64']:
    flags=['-std=c++17','-O2','-ffp-contract=fast','-Wall','-Wextra','-Werror']
    if arch=='host':
        binary=P/'sampling-host';command=['g++',*flags,'-fsanitize=address,undefined','-no-pie',str(HERE/'tmc11-runner.cpp'),str(HERE/'libipa/tmc11_ltm.cpp'),'-o',str(binary)];launch=[str(binary)]
    else:
        binary='/private/camss412-sampling/sampling-aarch64';command=['chroot',str(sdk),'g++',*flags,'/private/camss412-sampling/tmc11-runner.cpp','/private/camss412-sampling/libipa/tmc11_ltm.cpp','-o',binary];launch=['chroot',str(sdk),binary]
    q=subprocess.run(command,capture_output=True);assert not q.returncode,q.stderr.decode()
    q=subprocess.run(launch,input=inputs,capture_output=True,timeout=45);assert not q.returncode,q.stderr.decode()
    (P/(arch+'-sampling-actual-private.bin')).write_bytes(q.stdout);assert len(q.stdout)==len(wanted)
    diffs=sum(a!=b for a,b in zip(q.stdout,wanted));rows.append(dict(architecture=arch,cases=count,invalid_cases=len(invalid),compared_bytes=len(wanted),different_bytes=diffs,passed=not diffs));print(json.dumps(rows[-1]),flush=True)
result=dict(stage=412,cases=count,factory_regions=regions,extra_finite_subunity_linear_gain_cases=4,
    factory_anchor_based_source_coefficient_fixtures=True,
    target_tmc11_knee_generation_and_histogram_generation_not_executed=True,histogram_contrast_curves_synthetic=True,
    target_normalization_range=['0x362588','0x3626dc'],target_pchip_entry='0x3c7070',target_contrast_entry='0x3c7c98',
    normalized_node63_clipped_only_and_node64_fixed_one=True,pchip_mix_uses_y1_over_x1=True,
    target_contrast_always_reads_histogram_and_clamps_q10_to8191=True,source_pchip_different_bytes=source_pchip_diff,
    source_pchip_factory_fixture_different_bytes=source_pchip_factory_diff,
    target_inclusive_unity_lower_comparison_matters_for_subunity_linear_gain=True,
    source_contrast_different_bytes=source_contrast_diff,target_instructions=target.instructions,target_providers=target.providers,
    powf_is_host_libm_not_target_bionic=True,architectures=rows,input_records_unchanged=True,failed_outputs_preserved=True,
    all_68_factory_roots_model2_not_bezier=True,bezier_not_implemented_or_tested=True,runtime_version_not_observed=True,
    current_source_hashes=[dict(path='kernel412/'+n,sha256=hashlib.sha256((HERE/n).read_bytes()).hexdigest()) for n in files],
    phone_accessed=False,full_goal_kept_active=True,passed=all(r['passed'] for r in rows))
path=HERE/'sampling-validation.json'
if path.exists() and not json.loads(path.read_text())['passed'] and not (HERE/'sampling-r1-validation.json').exists():(HERE/'sampling-r1-validation.json').write_bytes(path.read_bytes())
path.write_text(json.dumps(result,indent=2)+'\n')
difference_path=HERE/'source-helper-r1-validation.json'
if difference_path.exists():
    prior=json.loads(difference_path.read_text())
    assert prior['cases']==count and prior['source_pchip_edge_different_bytes']==source_pchip_diff and prior['source_contrast_different_bytes']==source_contrast_diff
else:
    difference_path.write_text(json.dumps(dict(stage=412,cases=count,source_pchip_factory_fixture_different_bytes=source_pchip_factory_diff,
        source_pchip_edge_different_bytes=source_pchip_diff,source_contrast_different_bytes=source_contrast_diff,
        source_and_target_outputs_retained_privately=True,public_implementation_matches_target=result['passed'],phone_accessed=False,passed=False),indent=2)+'\n')
print(json.dumps(result,indent=2),flush=True);assert result['passed']
