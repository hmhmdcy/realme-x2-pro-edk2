"""Compare the portable LTM inverse table with the pinned source implementation."""
from pathlib import Path
import hashlib,json,random,shutil,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
def function(text,needle):
 start=text.index(needle);brace=text.index('{',start);depth=1;end=brace+1
 while depth:depth+=(text[end]=='{')-(text[end]=='}');end+=1
 return text[start:end]
utility_path=P.parent/'kernel333/sources/iqsettingutil.h';setting_path=P.parent/'kernel350/sources/ltm13setting.cpp'
utility=utility_path.read_text();setting=setting_path.read_text()
oracle='''#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <algorithm>
using INT=int;using INT32=int32_t;using INT16=int16_t;using UINT32=uint32_t;using UINT16=uint16_t;using FLOAT=float;using VOID=void;
constexpr UINT32 LTM_GAMMA_LUT_SIZE=64;constexpr FLOAT LTM_GAMMA_MIN_VALUE=0.0f,LTM_GAMMA_MAX_VALUE=4095.0f;constexpr INT32 GAMMA_MAX=16383;
struct LTM13InputData {INT32 *pGammaPrev,*pIGammaPrev;};
class IQSettingUtils {public:
static int Memcmp(const void *a,const void *b,size_t n){return std::memcmp(a,b,n);}
static void *Memcpy(void *a,const void *b,size_t n){return std::memcpy(a,b,n);}
'''
for needle in ['static __inline INT32 ClampINT32(','static __inline UINT32 AbsoluteINT(','static  __inline INT32 MinINT32(']:oracle+=function(utility,needle)+'\n'
oracle+='};\n'+function(setting,'static void Pack1D64EntryUnsignedHLUT(')+'\n'+function(setting,'static VOID InverseGamma(')
oracle+='''
int main(int argc,char **argv){assert(argc==3);FILE *in=fopen(argv[1],"rb"),*out=fopen(argv[2],"wb");assert(in&&out);uint16_t nodes[64];
while(fread(nodes,sizeof(uint16_t),64,in)==64){INT32 input[64],packed[64],cached[64],previous[64],previousInverse[64];
for(int i=0;i<64;i++){input[i]=nodes[i];previous[i]=-1;previousInverse[i]=-123;}
LTM13InputData state{previous,previousInverse};InverseGamma(input,packed,&state);InverseGamma(input,cached,&state);
assert(!memcmp(packed,cached,sizeof(packed))&&!memcmp(input,previous,sizeof(input))&&!memcmp(packed,previousInverse,sizeof(packed)));
assert(fwrite(packed,sizeof(INT32),64,out)==64);}
int fail=ferror(in);fclose(in);return fclose(out)||fail?3:0;}
'''
(P/'inverse-source-oracle-private.cpp').write_text(oracle)
factory=(P.parent/'kernel348/factory-gamma-private.bin').read_bytes();assert len(factory)==776
nodes=[struct.unpack_from('<H',factory,8+256+i*4)[0] for i in range(64)]
cases=[dict(kind='factory-ife-green-base',nodes=nodes),dict(kind='linear',nodes=[i*16 for i in range(64)]),
 dict(kind='reverse',nodes=[1023-i*16 for i in range(64)]),dict(kind='black',nodes=[0]*64),dict(kind='white',nodes=[1023]*64),
 dict(kind='alternating',nodes=[0 if i%2 else 1023 for i in range(64)]),dict(kind='plateaus',nodes=[(i//8)*128 for i in range(64)])]
for at in [0,31,63]:
 c=[i*16 for i in range(64)];c[at]=1023;cases.append(dict(kind='high-impulse',nodes=c))
 c=[i*16 for i in range(64)];c[at]=0;cases.append(dict(kind='low-impulse',nodes=c))
rng=random.Random(0x352)
for sorted_input in [True,False]:
 for _ in range(8):
  c=[rng.randrange(1024) for i in range(64)]
  if sorted_input:c.sort()
  cases.append(dict(kind='monotonic' if sorted_input else 'nonmonotonic',nodes=c))
valid_count=len(cases);(P/'inverse-oracle-input-private.bin').write_bytes(b''.join(struct.pack('<64H',*c['nodes']) for c in cases))
q=subprocess.run(['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror',str(P/'inverse-source-oracle-private.cpp'),'-o',str(P/'inverse-source-oracle')],capture_output=True)
(P/'inverse-oracle-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
subprocess.run([str(P/'inverse-source-oracle'),str(P/'inverse-oracle-input-private.bin'),str(P/'inverse-oracle-output-private.bin')],check=True,timeout=15)
raw=(P/'inverse-oracle-output-private.bin').read_bytes();assert len(raw)==valid_count*256
expected=b''.join(struct.pack('<I',1)+raw[i*256:(i+1)*256] for i in range(valid_count))
for bad in [1024,65535]:
 c=nodes.copy();c[17]=bad;cases.append(dict(kind='invalid',nodes=c));expected+=struct.pack('<I64I',0,*([0xa5a5a5a5]*64))
(P/'inverse-input-private.bin').write_bytes(b''.join(struct.pack('<64H',*c['nodes']) for c in cases));(P/'inverse-expected-private.bin').write_bytes(expected)
(P/'inverse-cases-private.json').write_text(json.dumps(cases,indent=2)+'\n')
work=SDK/'private/camss352-math';work.mkdir(exist_ok=True)
for source in [HERE/'inverse-gamma-runner.cpp',HERE/'libipa/ltm_inverse_gamma.cpp',HERE/'libipa/ltm_inverse_gamma.h',P/'inverse-input-private.bin']:shutil.copyfile(source,work/source.name)
rows=[]
for arch in ['host','aarch64']:
 command=['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I'+str(HERE/'libipa'),str(HERE/'inverse-gamma-runner.cpp'),str(HERE/'libipa/ltm_inverse_gamma.cpp'),'-o',str(P/'inverse-host')] if arch=='host' else ['chroot',str(SDK),'g++','-std=c++17','-O2','-Wall','-Wextra','-Werror','/private/camss352-math/inverse-gamma-runner.cpp','/private/camss352-math/ltm_inverse_gamma.cpp','-o','/private/camss352-math/inverse-aarch64']
 q=subprocess.run(command,capture_output=True);(P/('inverse-'+arch+'-build.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
 output=P/('inverse-'+arch+'-private.bin')
 command=[str(P/'inverse-host'),str(P/'inverse-input-private.bin'),str(output)] if arch=='host' else ['chroot',str(SDK),'/private/camss352-math/inverse-aarch64','/private/camss352-math/inverse-input-private.bin','/private/camss352-math/inverse-output-private.bin']
 subprocess.run(command,check=True,timeout=20)
 if arch=='aarch64':shutil.copyfile(work/'inverse-output-private.bin',output)
 actual=output.read_bytes();assert len(actual)==len(expected)
 differences=sum(a!=b for a,b in zip(actual,expected));rows.append(dict(architecture=arch,cases=len(cases),compared_bytes=len(actual),differing_bytes=differences,passed=not differences))
sources=[]
for file,path in [(setting_path,'camx/src/hwl/iqsetting/ltm13setting.cpp'),(P/'ltm13setting-reference-private.h','camx/src/hwl/iqsetting/ltm13setting.h'),(utility_path,'camx/src/hwl/iqsetting/iqsettingutil.h')]:
 data=file.read_bytes();sources.append(dict(path=path,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),url='https://github.com/bjzhou/CamxChi/blob/9f17f1b568626b393e785b369c5dc94543774d7a/'+path))
report=dict(stage=352,reference='privately compiled pinned InverseGamma + Pack1D64EntryUnsignedHLUT + numeric utilities',sources=sources,
 valid_reference_cases=valid_count,source_cache_hit_and_miss_outputs_equal=True,source_initial_previous_curve_forced_invalid=True,
 original_hal_instruction_equivalence_not_yet_checked=True,input_ife_green_nodes=64,input_bits=10,output_segments=64,output_base_bits=14,output_delta_signed_bits=14,
 earliest_index_tie_rule_preserved_for_nonmonotonic_input=True,negative_difference_sign_bit_forcing_preserved=True,portable_avoids_signed_right_shift=True,
 invalid_input_and_null_output_rejected=True,architectures=rows,not_yet_ipa_or_kernel_integrated=True,phone_changed=False,passed=all(r['passed'] for r in rows))
(HERE/'inverse-gamma-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));assert report['passed']
