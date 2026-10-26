"""Compare the C encoder with full target HAL numerical and CDM functions."""
from pathlib import Path
import importlib.util,json,math,random,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('colour398',HERE/'colour-model.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
oracle=m.Colour();records=[];expected=[];counts={}
(P/'colour.c').write_bytes((P/'camss-icp-a5-colour.c.proposed').read_bytes())
f32=lambda x:struct.unpack('<f',struct.pack('<f',x))[0]
round_away=lambda x:math.floor(x+.5) if x>=0 else math.ceil(x-.5)
def add(matrix,offset,shift):
 matrix=list(map(f32,matrix));offset=list(map(f32,offset));scale=1<<(7+shift)
 values=[round_away(f32(v*scale)) for v in matrix];ofs=list(map(round_away,offset))
 assert all(-2048<=v<=2047 for v in values) and all(-1024<=v<=1023 for v in ofs)
 registers=oracle.calculate(matrix,offset,shift);command=oracle.command(registers)
 records.append(struct.pack('<12hI',*values,*ofs,shift));expected.append(command)
for path in sorted((P.parent/'kernel351').glob('*-cc13_ipe-trees-private.json')):
 roots=json.loads(path.read_text());n=0
 for root in roots:
  for leaf in m.leaves(root['core']):add(leaf['matrix'],leaf['offsets'],root['qfactor']);n+=1
 counts[path.name.split('-cc13')[0]]=n
assert sum(counts.values())==737
for shift in range(4):
 for index in range(9):
  for value in [-2048,-1,0,1,2047]:
   matrix=[0.]*9;matrix[index]=value/(1<<(7+shift));add(matrix,[0,0,0],shift)
 for index in range(3):
  for value in [-1024,-1,0,1,1023]:
   offset=[0.]*3;offset[index]=value;add([0.]*9,offset,shift)
 for value in [-1.5,-.5,.5,1.5]:add([value/(1<<(7+shift))]*9,[value]*3,shift)
rng=random.Random(398)
for _ in range(128):
 shift=rng.randrange(4);add([rng.randrange(-2048,2048)/(1<<(7+shift)) for _ in range(9)],[rng.randrange(-1024,1024) for _ in range(3)],shift)
(P/'cc-input-private.bin').write_bytes(b''.join(records));(P/'cc-expected-private.bin').write_bytes(b''.join(expected))
include=P/'include';(include/'linux').mkdir(parents=True,exist_ok=True)
(include/'linux/types.h').write_text('#include <stdint.h>\ntypedef uint8_t u8;typedef int16_t s16;typedef uint32_t u32;typedef uint64_t u64;\n')
(include/'linux/errno.h').write_text('#define EINVAL 22\n#define ERANGE 34\n')
(include/'linux/string.h').write_text('#include <string.h>\n')
(include/'linux/unaligned.h').write_text('#include <stdint.h>\nstatic inline void put_unaligned_le32(uint32_t v,void *p){uint8_t *b=p;b[0]=v;b[1]=v>>8;b[2]=v>>16;b[3]=v>>24;}\n')
(include/'camss-icp-a5-ipe.h').write_text('#define CAMSS_A5_IPE_IQ_BYTES 2584U\nint camss_a5_ipe_encode_bypass_iq(void *,u32);\n')
(include/'camss-icp-a5-colour.h').write_bytes((P/'camss-icp-a5-colour.h.proposed').read_bytes())
runner=P/'colour-runner.c';runner.write_text(r'''#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "camss-icp-a5-colour.h"
static unsigned invalid;
static void rejected(struct camss_a5_ipe_cc *c,unsigned n){unsigned char b[64],old[64];memset(b,0xa7,sizeof b);memcpy(old,b,sizeof b);assert(camss_a5_ipe_cc_encode(b,n,c)<0);assert(!memcmp(b,old,sizeof b));invalid++;}
int main(int argc,char **argv){assert(argc==3);FILE *f=fopen(argv[1],"rb"),*o=fopen(argv[2],"wb");assert(f&&o);struct camss_a5_ipe_cc c={0};unsigned char record[28],b[64];unsigned n=0;
 while(fread(record,1,28,f)==28){memcpy(&c,record,28);memset(b,0xa7,sizeof b);assert(!camss_a5_ipe_cc_encode(b,sizeof b,&c));for(unsigned j=44;j<sizeof b;j++)assert(b[j]==0xa7);assert(fwrite(b,1,44,o)==44);n++;}
 assert(feof(f));fclose(f);assert(!fclose(o));memset(&c,0,sizeof c);
 for(unsigned j=0;j<44;j++)rejected(&c,j);
 rejected(NULL,64);assert(camss_a5_ipe_cc_encode(NULL,64,&c)<0);invalid++;
 c.shift=4;rejected(&c,64);c.shift=0xffffffff;rejected(&c,64);c.shift=0;
 for(unsigned j=0;j<9;j++){c.matrix[j]=-2049;rejected(&c,64);c.matrix[j]=2048;rejected(&c,64);c.matrix[j]=0;}
 for(unsigned j=0;j<3;j++){c.offset[j]=-1025;rejected(&c,64);c.offset[j]=1024;rejected(&c,64);c.offset[j]=0;}
 printf("cases=%u invalid=%u\n",n,invalid);return 0;}
''')
binary=P/'colour-runner';q=subprocess.run(['gcc','-std=c11','-O2','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-no-pie','-ffunction-sections','-Wl,--gc-sections','-I'+str(include),str(P/'colour.c'),str(runner),'-o',str(binary)],capture_output=True);assert q.returncode==0,q.stderr.decode()
q=subprocess.run([str(binary),str(P/'cc-input-private.bin'),str(P/'cc-actual-private.bin')],capture_output=True);assert q.returncode==0,q.stderr.decode()
actual=(P/'cc-actual-private.bin').read_bytes();assert actual==b''.join(expected)
assert set(oracle.providers)=={'0x4cd8b0','0x4cda68'}
report=dict(stage=398,factory_regions=sum(counts.values()),factory_regions_by_file=counts,synthetic_cases=len(records)-sum(counts.values()),compared_bytes=len(actual),different_bytes=0,invalid_no_write_cases=72,sanitizers=['ASan','UBSan'],actual_ipe_caller_type=2,target_hal_complete_cc13_oem_override_path_executed=True,previous_type1_oracle_not_reused=True,target_hal_complete_register_range_packet_encoding_executed=True,only_cmd_buffer_storage_begin_commit_modelled=True,no_numerical_or_packet_stub=True,original_instructions=oracle.instructions,register_words=9,cdm_command_bytes=44,matrix_bits_signed=12,offset_bits_signed=11,qfraction_base=7,qshift_bits=2,rgb_to_register_order='GBR rows and columns',module_enable_iq_offset=2188,module_enable_register=0x5e60,register_range_start=0x5e68,factory_interpolation_not_executed_by_this_check=True,hardware_execution=False,phone_changed=False,passed=True)
assert b'invalid=72' in q.stdout,q.stdout
(HERE/'colour-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
