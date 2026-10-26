"""Compare clean portable CCM math with compiled pinned source fragments."""
from pathlib import Path
import hashlib,json,re,shutil,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
manifest=json.loads((HERE/'primary-sources.json').read_text());repo=Path('/home/cy122/x2pro-linux/refs/CamxChi-k117')
for row in manifest['sources']:
 assert hashlib.sha256((P/'sources'/Path(row['path']).name).read_bytes()).hexdigest()==row['sha256']
for name in ['iqsettingutil.h','iqsettingutil.cpp']:
 path='camx/src/hwl/iqsetting/'+name;raw=(P/'sources'/name).read_bytes()
 assert raw==subprocess.check_output(['git','-C',str(repo),'show',manifest['sources'][0]['commit']+':'+path])
 if not any(r['path']==path for r in manifest['sources']):manifest['sources'].append(dict(repository=manifest['sources'][0]['repository'],commit=manifest['sources'][0]['commit'],path=path,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
(HERE/'primary-sources.json').write_text(json.dumps(manifest,indent=2)+'\n')
registers=P.parent/'kernel296/titan170-ife-source-1-private.h'
assert hashlib.sha256(registers.read_bytes()).hexdigest()=='800a9dbbf2bdf16ec36a03bd670d733bee8f63d4d9ed0311de9b24e29413cf53'
header=registers.read_text();wanted=['regIFE_IFE_0_VFE_MODULE_COLOR_EN','IFE_IFE_0_VFE_MODULE_COLOR_EN_COLOR_CORRECT_EN_MASK',
 'regIFE_IFE_0_VFE_COLOR_CORRECT_COEFF_0','regIFE_IFE_0_VFE_COLOR_CORRECT_OFFSET_0','regIFE_IFE_0_VFE_COLOR_CORRECT_COEFF_Q',
 'IFE_IFE_0_VFE_COLOR_CORRECT_COEFF_0_CN_MASK','IFE_IFE_0_VFE_COLOR_CORRECT_COEFF_0_RIGHT_CN_MASK',
 'IFE_IFE_0_VFE_COLOR_CORRECT_OFFSET_0_KN_MASK','IFE_IFE_0_VFE_COLOR_CORRECT_OFFSET_0_RIGHT_KN_MASK']
defs={n:int(re.search(r'^#define '+n+r' (0x[0-9a-f]+)',header,re.M)[1],16) for n in wanted}
(HERE/'hardware-protocol.json').write_text(json.dumps(dict(stage=333,source_evidence='../kernel296/dmi-protocol-sources.json',definitions=defs,
 coefficients_signed_bits=12,offsets_signed_bits=11,q_fraction_bits=[7,8,9,10],register_order='output GBR, input GBR, left/right fields duplicated',
 deployed_backend_supports_ccm=False,no_hardware_operation=True),indent=2)+'\n')
def function(text,needle):
 start=text.index(needle);brace=text.index('{',start);depth=1;end=brace+1
 while depth:
  depth+=(text[end]=='{')-(text[end]=='}');end+=1
 return text[start:end]
utility=(P/'sources/iqsettingutil.h').read_text();setting=(P/'sources/ifecc12setting.cpp').read_text();setting_header=(P/'sources/ifecc12setting.h').read_text();interpolation=(P/'sources/ifecc12interpolation.cpp').read_text()
oracle='''#include <cmath>
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <cassert>
using FLOAT=float;using DOUBLE=double;using INT=int32_t;using INT32=int32_t;using INT16=int16_t;
using UINT=unsigned int;using UINT32=uint32_t;using UINT16=uint16_t;using BOOL=bool;using VOID=void;
constexpr BOOL TRUE=true,FALSE=false;constexpr UINT32 CC12_Q_FACTOR=7;
namespace cc_1_2_0 {
struct cc12_rgn_dataType {struct {FLOAT c[9];} c_tab;struct {INT32 k[3];} k_tab;};
struct chromatix_cc12_reserveType {UINT32 q_factor;};
}
struct CC12InputData {};
'''
oracle+=function(setting_header,'struct CC12UnpackedField')+';\n'
oracle+='class IQSettingUtils {public:\n'+function(utility,'static __inline INT RoundFLOAT(')+function(utility,'static __inline FLOAT InterpolationFloatBilinear(')+'};\n'
oracle+='''class IFECC12Setting {public:static BOOL CalculateHWSetting(const CC12InputData*,cc_1_2_0::cc12_rgn_dataType*,cc_1_2_0::chromatix_cc12_reserveType*,VOID*);};
class IFECC12Interpolation {public:static BOOL InterpolationData(cc_1_2_0::cc12_rgn_dataType*,cc_1_2_0::cc12_rgn_dataType*,FLOAT,cc_1_2_0::cc12_rgn_dataType*);};
'''
oracle+=function(setting,'BOOL IFECC12Setting::CalculateHWSetting(')+'\n'+function(interpolation,'BOOL IFECC12Interpolation::InterpolationData(')+'\n'
oracle+='''int main(int argc,char **argv) {
 assert(argc==3);FILE *in=fopen(argv[1],"rb"),*out=fopen(argv[2],"wb");assert(in&&out);
 static_assert(sizeof(cc_1_2_0::cc12_rgn_dataType)==48);static_assert(sizeof(CC12UnpackedField)==52);
 UINT32 mode,q;while(fread(&mode,4,1,in)==1){
 cc_1_2_0::cc12_rgn_dataType a,b,c;assert(fread(&q,4,1,in)==1&&fread(&a,48,1,in)==1);
 if(mode==2){FLOAT t;assert(fread(&b,48,1,in)==1&&fread(&t,4,1,in)==1);
 if(t==0)c=a;else if(t==1)c=b;else assert(IFECC12Interpolation::InterpolationData(&a,&b,t,&c));
 a=c;assert(fwrite(&a,48,1,out)==1);
 }else assert(mode==1);
 CC12UnpackedField result;CC12InputData info;cc_1_2_0::chromatix_cc12_reserveType reserve{q};
 assert(IFECC12Setting::CalculateHWSetting(&info,&a,&reserve,&result));
 UINT16 fields[26];memcpy(fields,&result,sizeof(fields));for(int i=0;i<13;i++)assert(fields[i]==fields[i+13]);
 for(int i=0;i<12;i++)fields[i]&=i<9?0xfff:0x7ff;
 assert(fwrite(fields,26,1,out)==1);
 }fclose(in);return fclose(out)?2:0;
}
'''
(P/'stock-source-oracle-private.cpp').write_text(oracle)
inputs=bytearray();cases=[]
def add(a,q,b=None,weight=None,kind='factory'):
 mode=2 if b is not None else 1
 inputs.extend(struct.pack('<II9f3i',mode,q,*a['matrix'],*a['offsets']))
 if b is not None:inputs.extend(struct.pack('<9f3if',*b['matrix'],*b['offsets'],weight))
 cases.append(dict(kind=kind,interpolation=mode==2,qfactor=q))
def leaves(nodes):
 for n in nodes:
  if 'matrix' in n:yield n
  else:yield from leaves(n['children'])
def sibling_leaves(nodes):
 if 'matrix' in nodes[0]:yield nodes
 else:
  for n in nodes:yield from sibling_leaves(n['children'])
for name in ['qtech_s5kgw1','sunny_s5kgw1','sunny_imx471','qtech_s5k3m5sx','sunny_imx319']:
 for root in json.loads((P/(name+'-ccm-trees-private.json')).read_text()):
  for leaf in leaves(root['core']):add(leaf,root['qfactor'])
  for rows in sibling_leaves(root['core']):
   for a,b in zip(rows,rows[1:]):
    for weight in [0.,.125,.5,.875,1.]:add(a,root['qfactor'],b,weight)
for q in range(4):
 a=dict(matrix=[1.,-.125,.25,-.5,.75,.0625,.375,-.25,.875],offsets=[-1024,1023,-1])
 b=dict(matrix=[-.875,.25,-.375,.5,-.75,-.0625,-.25,.125,-1.],offsets=[1023,-1024,1])
 add(a,q,kind='asymmetric-signed')
 for weight in [0.,.125,.5,.875,1.]:add(a,q,b,weight,'asymmetric-signed')
 for sign in [-1,1]:
  for integer in [0,1,127,511,1023]:
   v=sign*(integer+.5)/(1<<(7+q));a=dict(matrix=[v]*9,offsets=[-17,0,21]);add(a,q,kind='rounding-half')
(P/'math-input-private.bin').write_bytes(inputs)
flags=['-std=c++17','-O2','-ffp-contract=off','-Wall','-Wextra','-Werror'];sdk=Path('/home/cy122/x2pro-linux/libcamera214-root');relative=Path('/private/camss333-ccm');stage=sdk/str(relative).lstrip('/');stage.mkdir(mode=0o700,exist_ok=True);(stage/'libipa').mkdir(exist_ok=True)
q=subprocess.run(['g++',*flags,str(P/'stock-source-oracle-private.cpp'),'-o',str(P/'stock-source-oracle')],capture_output=True)
(P/'oracle-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
subprocess.run([str(P/'stock-source-oracle'),str(P/'math-input-private.bin'),str(P/'stock-expected-private.bin')],check=True)
for name in ['ccm-runner.cpp','libipa/colour_correction.cpp','libipa/colour_correction.h']:shutil.copyfile(HERE/name,stage/name)
shutil.copyfile(P/'math-input-private.bin',stage/'math-input-private.bin')
expected=(P/'stock-expected-private.bin').read_bytes();results=[]
for architecture in ['host','aarch64']:
 exe=P/('math-'+architecture)
 args=['g++',*flags,str(HERE/'ccm-runner.cpp'),str(HERE/'libipa/colour_correction.cpp'),'-o',str(exe)] if architecture=='host' else ['chroot',str(sdk),'g++',*flags,str(relative/'ccm-runner.cpp'),str(relative/'libipa/colour_correction.cpp'),'-o',str(relative/'math-aarch64')]
 q=subprocess.run(args,capture_output=True);(P/(architecture+'-build.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
 output=P/(architecture+'-output-private.bin')
 args=[str(exe),str(P/'math-input-private.bin'),str(output)] if architecture=='host' else ['chroot',str(sdk),str(relative/'math-aarch64'),str(relative/'math-input-private.bin'),str(relative/'aarch64-output-private.bin')]
 q=subprocess.run(args,capture_output=True);assert not q.returncode,(architecture,q.returncode,q.stderr.decode())
 if architecture=='aarch64':shutil.copyfile(stage/'aarch64-output-private.bin',output)
 actual=output.read_bytes();assert len(actual)==len(expected)
 different=sum(a!=b for a,b in zip(actual,expected));results.append(dict(architecture=architecture,cases=len(cases),compared_bytes=len(expected),differing_bytes=different))
 assert not different,results[-1]
report=dict(stage=333,architectures=results,factory_regions=567,quantization_cases=sum(not c['interpolation'] for c in cases),interpolation_cases=sum(c['interpolation'] for c in cases),
 oracle='compiled selected pinned public CamX calculation/interpolation bodies and original rounding helpers; no OEM native library',
 generic_matrix_to_gbr_mapping_verified=True,signed_coefficients_and_offsets_verified=True,all_qformats_verified=True,
 interpolation_arithmetic='separate integer/fractional rounding in pinned utility, float32 decimal scale; integer offsets truncate at each blend',
 hardware_register_source_stage=296,deployed_driver_ccm_support=False,ipa_integrated=False,phone_changed=False,passed=True)
(HERE/'math-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
