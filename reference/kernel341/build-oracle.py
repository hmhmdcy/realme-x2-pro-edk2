"""Compile only retained pinned LSC interpolation/calibration functions."""
from pathlib import Path
import subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
def function(text,needle):
 start=text.index(needle);brace=text.index('{',start);depth=1;end=brace+1
 while depth:depth+=(text[end]=='{')-(text[end]=='}');end+=1
 return text[start:end]
source=(P.parent/'kernel317/sources/lsc34interpolation.cpp').read_text();utility=(P.parent/'kernel333/sources/iqsettingutil.h').read_text()
out='''#include <cstdint>
#include <cstddef>
#include <cassert>
using FLOAT=float;using DOUBLE=double;using INT32=int32_t;using UINT32=uint32_t;using UINT=unsigned;using BOOL=bool;
constexpr BOOL TRUE=true;constexpr UINT32 MESH_ROLLOFF_SIZE=221;
struct Trigger {FLOAT start,end;};
namespace lsc_3_4_0 {
struct lsc34_rgn_dataType {
 struct{FLOAT r_gain[221];}r_gain_tab;struct{FLOAT gr_gain[221];}gr_gain_tab;
 struct{FLOAT gb_gain[221];}gb_gain_tab;struct{FLOAT b_gain[221];}b_gain_tab;
};
struct mod_lsc34_golden_cct_dataType {Trigger cct_trigger;};
struct chromatix_lsc34_goldenType {UINT32 mod_lsc34_golden_cct_dataCount;mod_lsc34_golden_cct_dataType *mod_lsc34_golden_cct_data;};
}
struct Chromatix {lsc_3_4_0::chromatix_lsc34_goldenType chromatix_lsc34_golden;};
struct Calibration {FLOAT *pRGain,*pGRGain,*pGBGain,*pBGain;};
struct LSC34InputData {Chromatix *pChromatix;UINT32 numberOfEEPROMTable;Calibration *pCalibrationTable;};
class IQSettingUtils {public:static UINT32 MinUINT32(UINT32 a,UINT32 b){return a<b?a:b;}
'''+function(utility,'static __inline FLOAT InterpolationFloatBilinear(')+'''};
class LSC34Interpolation {public:
static BOOL InterpolationData(lsc_3_4_0::lsc34_rgn_dataType*,lsc_3_4_0::lsc34_rgn_dataType*,FLOAT,lsc_3_4_0::lsc34_rgn_dataType*);
static BOOL InterpolateAndCalibrate(lsc_3_4_0::lsc34_rgn_dataType*,const LSC34InputData*,lsc_3_4_0::lsc34_rgn_dataType*,FLOAT);
};
'''+function(source,'BOOL LSC34Interpolation::InterpolationData(')+'\n'+function(source,'BOOL LSC34Interpolation::InterpolateAndCalibrate(')+'''
using Mesh=lsc_3_4_0::lsc34_rgn_dataType;
extern "C" void blend(Mesh *a,Mesh *b,FLOAT weight,Mesh *result){
 if(weight==0)*result=*a;else if(weight==1)*result=*b;else assert(LSC34Interpolation::InterpolationData(a,b,weight,result));
}
extern "C" void calibrate(Mesh *base,Mesh *golden,Mesh *unit,Mesh *result){
 Mesh factors;
 FLOAT *f=reinterpret_cast<FLOAT*>(&factors),*g=reinterpret_cast<FLOAT*>(golden),*u=reinterpret_cast<FLOAT*>(unit);
 for(unsigned i=0;i<884;i++){assert(g[i]>0&&u[i]>0);f[i]=g[i]/u[i];}
 lsc_3_4_0::mod_lsc34_golden_cct_dataType entry{{1,10000}};Chromatix chromatix{{1,&entry}};
 Calibration table{factors.r_gain_tab.r_gain,factors.gr_gain_tab.gr_gain,factors.gb_gain_tab.gb_gain,factors.b_gain_tab.b_gain};
 LSC34InputData input{&chromatix,1,&table};assert(LSC34Interpolation::InterpolateAndCalibrate(base,&input,result,6500));
}
'''
(P/'pinned-lsc-oracle-private.cpp').write_text(out);q=subprocess.run(['g++','-std=c++17','-O2','-ffp-contract=off','-shared','-fPIC',str(P/'pinned-lsc-oracle-private.cpp'),'-o',str(P/'pinned-lsc-oracle-private.so')],capture_output=True)
(P/'oracle-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode();print('Built retained original LSC functions; source and binary remain private.')
