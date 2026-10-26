"""Compare the common encoder with Gamma15 source and the prior IFE reference."""
from pathlib import Path
import json,shutil,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
def function(text,needle):
 start=text.index(needle);brace=text.index('{',start);depth=1;end=brace+1
 while depth:depth+=(text[end]=='{')-(text[end]=='}');end+=1
 return text[start:end]
utility=(P.parent/'kernel333/sources/iqsettingutil.h').read_text();setting=(P/'sources/gamma15setting.cpp').read_text()
oracle='''#include <cmath>
#include <cstdio>
#include <cstdint>
#include <cassert>
using FLOAT=float;using INT=int;using INT32=int32_t;using UINT16=uint16_t;using UINT32=uint32_t;using VOID=void;
constexpr UINT16 NMAX10=1024;constexpr INT32 MIN_INT10=-512,MAX_INT10=511;
constexpr UINT32 Gamma15LUTNumEntriesPerChannel=256;
class IQSettingUtils {public:
'''
for name in ['static __inline INT RoundFLOAT(','static __inline UINT32 ClampUINT32(','static __inline INT32 ClampINT32(']:oracle+=function(utility,name)+'\n'
oracle+='};\nclass Gamma15Setting {public:static VOID GenerateGammaLUT(FLOAT*,UINT32*);};\n'+function(setting,'VOID Gamma15Setting::GenerateGammaLUT(')
oracle+='''
int main(int argc,char **argv){assert(argc==3);FILE *in=fopen(argv[1],"rb"),*out=fopen(argv[2],"wb");assert(in&&out);
FLOAT curve[257];while(fread(curve,sizeof(FLOAT),257,in)==257){UINT32 lut[256];Gamma15Setting::GenerateGammaLUT(curve,lut);assert(fwrite(lut,sizeof(UINT32),256,out)==256);}
int fail=ferror(in);fclose(in);return fclose(out)||fail?3:0;}
'''
(P/'stock-source-oracle-private.cpp').write_text(oracle)
def leaves(nodes):
 for n in nodes:
  if 'table' in n:yield n
  else:yield from leaves(n['children'])
curves={};source_count=0
for path in sorted(P.glob('*-gamma-trees-private.json')):
 for root in json.loads(path.read_text()):
  for leaf in leaves(root['core']):
   source_count+=1;key=struct.pack('<257f',*leaf['table']);curves[key]=leaf['table']
   assert all(0<=v<=1024 for v in leaf['table'])
cases=[dict(kind='factory',values=values,valid=True) for values in curves.values()]
for label,values in [('linear',[float(i*4) for i in range(257)]),('reverse',[float(1024-i*4) for i in range(257)]),
 ('delta-clamps',[0. if i%2 else 1024. for i in range(257)]),('halves',[min(1024.,i*4.+.5) for i in range(257)])]:cases.append(dict(kind=label,values=values,valid=True))
for position in [0,255,256]:
 for value in [0.,.5,511.5,512.,1023.5,1024.]:
  values=[float(i*4) for i in range(257)];values[position]=value;cases.append(dict(kind='endpoint',values=values,valid=True))
valid=len(cases);(P/'oracle-input-private.bin').write_bytes(b''.join(struct.pack('<257f',*c['values']) for c in cases))
q=subprocess.run(['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror',str(P/'stock-source-oracle-private.cpp'),'-o',str(P/'stock-source-oracle')],capture_output=True);assert not q.returncode,q.stderr.decode()
subprocess.run([str(P/'stock-source-oracle'),str(P/'oracle-input-private.bin'),str(P/'oracle-output-private.bin')],check=True)
raw=(P/'oracle-output-private.bin').read_bytes();assert len(raw)==valid*1024
expected=b''.join(struct.pack('<I',1)+raw[i*1024:(i+1)*1024] for i in range(valid))
for value in [-1.,1024.1,float('nan'),float('inf')]:
 values=[float(i*4) for i in range(257)];values[128]=value;cases.append(dict(kind='invalid',values=values,valid=False));expected+=b'\0'*1028
(P/'input256-private.bin').write_bytes(b''.join(struct.pack('<257f',*c['values']) for c in cases));(P/'expected256-private.bin').write_bytes(expected)
(P/'cases256-private.json').write_text(json.dumps(cases,allow_nan=True)+'\n')
work=SDK/'private/camss350-math';work.mkdir(exist_ok=True)
shutil.copyfile(HERE/'gamma-runner.cpp',work/'gamma-runner.cpp');shutil.copyfile(HERE/'libipa/gamma_segments.h',work/'gamma_segments.h')
for src,dest in [(P/'input256-private.bin','input256-private.bin'),(P.parent/'kernel347/math-input-private.bin','input64-private.bin')]:shutil.copyfile(src,work/dest)
rows=[]
for arch in ['host','aarch64']:
 command=['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I'+str(HERE/'libipa'),str(HERE/'gamma-runner.cpp'),'-o',str(P/'gamma-host')] if arch=='host' else ['chroot',str(SDK),'g++','-std=c++17','-O2','-Wall','-Wextra','-Werror','/private/camss350-math/gamma-runner.cpp','-o','/private/camss350-math/gamma-aarch64']
 q=subprocess.run(command,capture_output=True);(P/(arch+'-build.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
 for count in [64,256]:
  source=P/'input256-private.bin' if count==256 else P.parent/'kernel347/math-input-private.bin'
  wanted=expected if count==256 else (P.parent/'kernel347/expected-private.bin').read_bytes()
  out=P/(arch+'-'+str(count)+'-private.bin')
  command=[str(P/'gamma-host'),str(count),str(source),str(out)] if arch=='host' else ['chroot',str(SDK),'/private/camss350-math/gamma-aarch64',str(count),'/private/camss350-math/input'+str(count)+'-private.bin','/private/camss350-math/output-private.bin']
  subprocess.run(command,check=True,timeout=15)
  if arch=='aarch64':shutil.copyfile(work/'output-private.bin',out)
  actual=out.read_bytes();assert len(actual)==len(wanted);size=4+count*4
  different=sum(actual[i:i+size]!=wanted[i:i+size] for i in range(0,len(actual),size))
  row=dict(architecture=arch,segments=count,cases=len(actual)//size,compared_bytes=len(actual),differing_records=different,passed=not different);rows.append(row);print(json.dumps(row),flush=True)
report=dict(stage=350,factory_channel_curves=source_count,unique_factory_curves=len(curves),identical_curves_tested_once=True,
 architectures=rows,original_gamma15_source_function_compiled_privately=True,ife64_reference_reused_from347=True,
 gamma15_runtime_tree_selection_not_yet_integrated=True,phone_changed=False,passed=all(r['passed'] for r in rows))
(HERE/'gamma-math-validation.json').write_text(json.dumps(report,indent=2)+'\n');assert report['passed']
