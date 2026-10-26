"""Retain full factory trees and build a pinned-source selection/encoding oracle."""
from pathlib import Path
import copy,ctypes,json,shutil,struct,subprocess
import yaml
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;OLD=P.parent/'kernel333'
def function(text,needle):
 start=text.index(needle);brace=text.index('{',start);depth=1;end=brace+1
 while depth:depth+=(text[end]=='{')-(text[end]=='}');end+=1
 return text[start:end]
source=(OLD/'stock-source-oracle-private.cpp').read_text()
utility=(OLD/'sources/iqsettingutil.cpp').read_text();header=(OLD/'sources/iqsettingutil.h').read_text()
source=source.replace('class IQSettingUtils {public:', '''struct TriggerRegion {FLOAT start,end;};
struct InterpolationOutput {UINT32 startIndex,endIndex;FLOAT interpolationRatio;};
class IQSettingUtils {public:
static VOID GetIndexPtTrigger(TriggerRegion*,UINT32,FLOAT,InterpolationOutput*);
'''+function(header,'static  __inline FLOAT CalculateInterpolationRatio('))
source+='\n'+function(utility,'VOID IQSettingUtils::GetIndexPtTrigger(')
source+='''
extern "C" void choose(TriggerRegion *regions,UINT32 count,FLOAT value,InterpolationOutput *result) {
 IQSettingUtils::GetIndexPtTrigger(regions,count,value,result);
}
extern "C" void blend(cc_1_2_0::cc12_rgn_dataType *a,cc_1_2_0::cc12_rgn_dataType *b,FLOAT t,cc_1_2_0::cc12_rgn_dataType *out) {
 if(t==0)*out=*a;else if(t==1)*out=*b;else assert(IFECC12Interpolation::InterpolationData(a,b,t,out));
}
extern "C" void encode(cc_1_2_0::cc12_rgn_dataType *data,UINT32 q,CC12UnpackedField *result) {
 CC12InputData info;cc_1_2_0::chromatix_cc12_reserveType reserve{q};
 assert(IFECC12Setting::CalculateHWSetting(&info,data,&reserve,result));
}
'''
(P/'selection-oracle-private.cpp').write_text(source)
q=subprocess.run(['g++','-std=c++17','-O2','-ffp-contract=off','-shared','-fPIC',str(P/'selection-oracle-private.cpp'),'-o',str(P/'selection-oracle-private.so')],capture_output=True)
(P/'oracle-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
class Data(ctypes.Structure):_fields_=[('matrix',ctypes.c_float*9),('offsets',ctypes.c_int32*3)]
class Region(ctypes.Structure):_fields_=[('start',ctypes.c_float),('end',ctypes.c_float)]
class Selection(ctypes.Structure):_fields_=[('first',ctypes.c_uint32),('second',ctypes.c_uint32),('weight',ctypes.c_float)]
lib=ctypes.CDLL(str(P/'selection-oracle-private.so'));lib.choose.argtypes=[ctypes.POINTER(Region),ctypes.c_uint32,ctypes.c_float,ctypes.POINTER(Selection)]
lib.blend.argtypes=[ctypes.POINTER(Data),ctypes.POINTER(Data),ctypes.c_float,ctypes.POINTER(Data)];lib.encode.argtypes=[ctypes.POINTER(Data),ctypes.c_uint32,ctypes.c_void_p]
def evaluate(nodes,level,kelvin,coordinates):
 def child(n):return Data((ctypes.c_float*9)(*n['matrix']),(ctypes.c_int32*3)(*n['offsets'])) if level==4 else evaluate(n['children'],level+1,kelvin,coordinates)
 if level==2:return child(next(n for n in nodes if n['trigger'][0]==coordinates['led_index']))
 pos=2 if level==1 else 0
 value=kelvin if level==4 else coordinates[{0:'drc_gain',1:'hdr_ratio',3:'aec_value'}[level]]
 regions=(Region*len(nodes))(*(Region(*n['trigger'][pos:pos+2]) for n in nodes));selected=Selection()
 lib.choose(regions,len(nodes),value,ctypes.byref(selected));a=child(nodes[selected.first])
 if selected.first==selected.second:return a
 b=child(nodes[selected.second]);out=Data();lib.blend(ctypes.byref(a),ctypes.byref(b),selected.weight,ctypes.byref(out));return out
def encoded(data,q):
 fields=(ctypes.c_uint16*26)();lib.encode(ctypes.byref(data),q,fields);assert list(fields[:13])==list(fields[13:])
 signed=[ctypes.c_int16(fields[i]).value for i in range(9)]
 rgb=[0.]*9
 for i,rgbindex in enumerate([4,5,3,7,8,6,1,2,0]):rgb[rgbindex]=signed[i]/(1<<(7+q))
 abc=[fields[i*3+j]&0xfff for j in range(3) for i in range(3)]
 return struct.pack('<HHI13H3H',3,2,40,*abc,*[fields[9+i]&0x7ff for i in range(3)],fields[12],0,0,0)+struct.pack('<9f',*rgb)
cases=json.loads((P.parent/'kernel332/cases-private.json').read_text());(P/'profiles').mkdir(exist_ok=True)
for name,case in cases.items():
 root=next(r for r in json.loads((OLD/(case['variant']+'-ccm-trees-private.json')).read_text()) if r['uid']==37)
 assert root['control_method']==[0,1]
 coordinates=dict(drc_gain=1.,hdr_ratio=1.,led_index=0,aec_value=100.)
 profile=yaml.safe_load((P.parent/'kernel332/profiles'/(name+'.yaml')).read_text())
 tuning=dict(enabled=bool(root['enabled']),qfactor=root['qfactor'],aec_control='lux_index',hdr_control='sensitivity_ratio',reference_triggers=coordinates,core=root['core'])
 for mode in profile['modes']:mode['colour_correction']=copy.deepcopy(tuning)
 (P/'profiles'/(name+'.yaml')).write_text(yaml.safe_dump(profile,sort_keys=False))
 expected=bytearray()
 for kelvin in range(1500,12001):expected.extend(encoded(evaluate(root['core'],0,kelvin,coordinates),root['qfactor']))
 (P/'profiles'/(name+'-oracle-private.bin')).write_bytes(expected)
 shutil.copyfile(P.parent/'kernel332'/(name+'-points-private.bin'),P/(name+'-points-private.bin'))
 case['ccm_uid']=37;case['ccm_reference_triggers']=coordinates;case['ccm_enabled']=bool(root['enabled']);case['factory_ccm_enabled']=bool(root['enabled'])
extra={}
for name,case in cases.items():
 if case['ccm_enabled']:continue
 experiment=name+'-ccm-experiment';item=copy.deepcopy(case);item['ccm_enabled']=True;item['experimental_enable_override']=True;item['profile']=experiment
 profile=yaml.safe_load((P/'profiles'/(name+'.yaml')).read_text())
 for mode in profile['modes']:mode['colour_correction']['enabled']=True
 (P/'profiles'/(experiment+'.yaml')).write_text(yaml.safe_dump(profile,sort_keys=False))
 for suffix in ['-oracle-private.bin']:shutil.copyfile(P/'profiles'/(name+suffix),P/'profiles'/(experiment+suffix))
 shutil.copyfile(P/(name+'-points-private.bin'),P/(experiment+'-points-private.bin'));extra[experiment]=item
cases.update(extra)
# Independent asymmetric manual matrix, not a factory table.
data=Data((ctypes.c_float*9)(0,0,1,0,.75,0,1,0,0),(ctypes.c_int32*3)(0,0,0))
(P/'manual-oracle-private.bin').write_bytes(encoded(data,0))
(P/'cases-private.json').write_text(json.dumps(cases,indent=2)+'\n')
(HERE/'profile-validation.json').write_text(json.dumps(dict(stage=335,profiles=len(cases),factory_ccm_root_uid=37,full_trigger_hierarchy_preserved=True,
 oracle='compiled pinned public CamX GetIndexPtTrigger, InterpolationData, CalculateHWSetting and rounding/ratio helpers',
 expected_cct_samples_per_profile=10501,aec_hdr_drc_led_are_explicit_reference_coordinates=True,factory_front_ccm_disabled_preserved=True,front_explicit_enable_experiments=2,supplier_binding_verified=False,default_profiles_changed=False,passed=True),indent=2)+'\n')
print('Prepared factory-enabled/disabled profiles and explicit front CCM experiments.')
