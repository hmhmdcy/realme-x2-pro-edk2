"""Compare generic encoding against the pinned source routine, deduplicating curves."""
from pathlib import Path
import json,shutil,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
def function(text,needle):
 start=text.index(needle);brace=text.index('{',start);depth=1;end=brace+1
 while depth:
  depth+=(text[end]=='{')-(text[end]=='}');end+=1
 return text[start:end]
utility=(P.parent/'kernel333/sources/iqsettingutil.h').read_text();setting=(P/'sources/gamma16setting.cpp').read_text()
oracle='''#include <cmath>
#include <cstdio>
#include <cstdint>
#include <cassert>
using FLOAT=float;using INT=int;using INT32=int32_t;using UINT16=uint16_t;using UINT32=uint32_t;using VOID=void;
constexpr UINT16 NMAX10=1024;constexpr INT32 MIN_INT10=-512,MAX_INT10=511;
constexpr UINT32 DMIRAM_RGB_CH0_LENGTH_RGBLUT_V16=64,GAMMA16_HW_PACK_BIT=10;
class IQSettingUtils {public:
'''
for name in ['static __inline INT RoundFLOAT(','static __inline UINT16 ClampUINT16(','static __inline INT32 ClampINT32(']:oracle+=function(utility,name)+'\n'
oracle+='};\nclass Gamma16Setting {public:static VOID GenerateGammaLUT(FLOAT*,UINT32*);};\n'
oracle+=function(setting,'VOID Gamma16Setting::GenerateGammaLUT(')
oracle+='''
int main(int argc,char **argv){assert(argc==3);FILE *in=fopen(argv[1],"rb"),*out=fopen(argv[2],"wb");assert(in&&out);
FLOAT curve[65];while(fread(curve,sizeof(FLOAT),65,in)==65){UINT32 lut[64];Gamma16Setting::GenerateGammaLUT(curve,lut);assert(fwrite(lut,sizeof(UINT32),64,out)==64);}
int fail=ferror(in);fclose(in);return fclose(out)||fail?3:0;}
'''
(P/'stock-source-oracle-private.cpp').write_text(oracle)
def leaves(nodes):
 for n in nodes:
  if 'table' in n:yield n
  else:yield from leaves(n['children'])
unique={};source_count=0
for path in sorted(P.glob('*-gamma-trees-private.json')):
 for root in json.loads(path.read_text()):
  for leaf in leaves(root['core']):
   source_count+=1;unique[struct.pack('<65f',*leaf['table'])]=leaf['table']
cases=[dict(kind='factory',curve=c,valid=True) for c in unique.values()]
for label,c in [('linear',[16.*i for i in range(65)]),('zero',[0.]*65),('maximum',[1024.]*65),
 ('decreasing',[1024.-16.*i for i in range(65)]),('slope-clamps',[0. if i%2 else 1024. for i in range(65)]),
 ('half-rounding',[min(1024.,i*16.+.5) for i in range(65)])]:cases.append(dict(kind=label,curve=c,valid=True))
for value in [0.,.5,511.,511.5,512.,512.5,1022.5,1023.,1023.5,1024.]:
 for at in [0,63,64]:
  c=[16.*i for i in range(65)];c[at]=value;cases.append(dict(kind='endpoint-or-half',curve=c,valid=True))
valid=[c for c in cases if c['valid']];valid_input=b''.join(struct.pack('<65f',*c['curve']) for c in valid)
(P/'oracle-input-private.bin').write_bytes(valid_input)
for value in [-1.,1024.1,float('nan'),float('inf')]:
 c=[16.*i for i in range(65)];c[32]=value;cases.append(dict(kind='invalid',curve=c,valid=False))
(P/'math-input-private.bin').write_bytes(b''.join(struct.pack('<65f',*c['curve']) for c in cases))
(P/'math-cases-private.json').write_text(json.dumps(cases,allow_nan=True)+'\n')
command=['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror',str(P/'stock-source-oracle-private.cpp'),'-o',str(P/'stock-source-oracle')]
q=subprocess.run(command,capture_output=True);assert not q.returncode,q.stderr.decode()
subprocess.run([str(P/'stock-source-oracle'),str(P/'oracle-input-private.bin'),str(P/'oracle-output-private.bin')],check=True,timeout=15)
stock=(P/'oracle-output-private.bin').read_bytes();assert len(stock)==len(valid)*256
expected=b''.join(struct.pack('<I',1)+stock[i*256:(i+1)*256] for i in range(len(valid)))+b'\0'*260*(len(cases)-len(valid))
(P/'expected-private.bin').write_bytes(expected)
work=SDK/'private/camss347-math';work.mkdir(exist_ok=True)
for source in [HERE/'gamma-runner.cpp',*sorted((HERE/'libipa').glob('*'))]:shutil.copyfile(source,work/source.name)
shutil.copyfile(P/'math-input-private.bin',work/'input-private.bin');rows=[]
for arch in ['host','aarch64']:
 command=['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I'+str(HERE/'libipa'),str(HERE/'gamma-runner.cpp'),str(HERE/'libipa/gamma_curve.cpp'),'-o',str(P/'gamma-host')] if arch=='host' else ['chroot',str(SDK),'g++','-std=c++17','-O2','-Wall','-Wextra','-Werror','/private/camss347-math/gamma-runner.cpp','/private/camss347-math/gamma_curve.cpp','-o','/private/camss347-math/gamma-aarch64']
 q=subprocess.run(command,capture_output=True);(P/(arch+'-build.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
 out=P/(arch+'-output-private.bin')
 command=[str(P/'gamma-host'),str(P/'math-input-private.bin'),str(out)] if arch=='host' else ['chroot',str(SDK),'/private/camss347-math/gamma-aarch64','/private/camss347-math/input-private.bin','/private/camss347-math/output-private.bin']
 subprocess.run(command,check=True,timeout=15)
 if arch=='aarch64':shutil.copyfile(work/'output-private.bin',out)
 actual=out.read_bytes();assert len(actual)==len(expected)
 different=[i for i in range(len(cases)) if actual[i*260:(i+1)*260]!=expected[i*260:(i+1)*260]]
 rows.append(dict(architecture=arch,cases=len(cases),compared_bytes=len(actual),differing_records=len(different),passed=not different));print(json.dumps(rows[-1]),flush=True)
report=dict(stage=347,factory_channel_curves=source_count,unique_factory_curves=len(unique),identical_curves_tested_once=True,
 architectures=rows,oracle='compiled pinned source GenerateGammaLUT and RoundFLOAT/clamp helpers',
 oracle_is_not_target_hal_instruction_emulation=True,all_64_words_compared=True,invalid_input_rejected=True,
 gamma_ipa_integrated=False,phone_changed=False,passed=all(r['passed'] for r in rows))
(HERE/'gamma-math-validation.json').write_text(json.dumps(report,indent=2)+'\n');assert report['passed']
