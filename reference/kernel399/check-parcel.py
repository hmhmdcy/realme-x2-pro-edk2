"""Compare complete C-generated typed conversion pages with target HAL packets."""
from pathlib import Path
import importlib.util,json,math,random,re,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('colour399',HERE/'colour-model.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
assert json.loads((HERE/'native-leaf-validation.json').read_text())['passed']
oracle=m.Colour();records=[];expected=[];counts=dict(cst=0,cc=0,cv=0,combinations=0)
f32=lambda x:struct.unpack('<f',struct.pack('<f',x))[0]
roundaway=lambda x:math.floor(x+.5) if x>=0 else math.ceil(x-.5)
clamp=lambda x,lo,hi:min(max(x,lo),hi)
def add(mask,cst=None,cc=None,cv=None):
 cq=[0]*21;mq=[0]*12;shift=0;vq=[0]*14;packets={}
 if mask&1:
  cq=[clamp(roundaway(f32(f32(x)*1024)),-4096,4095) for x in cst['m_tab']]+[clamp(x,-1024,1023) for x in cst['s_tab']]+[clamp(x,0,1023) for x in cst['o_tab']]+[clamp(x,0,1023) for x in cst['c_x0_tab']]+[clamp(x,0,1023) for x in cst['c_x1_tab']]
  assert all(cq[15+i]<=cq[18+i] for i in range(3))
  packets[1]=oracle.command(0x5a68,oracle.cst(cst))
 if mask&2:
  shift=cc['shift'];mq=[roundaway(f32(f32(v)*(1<<(7+shift)))) for v in cc['matrix']]+[roundaway(v) for v in cc['offsets']]
  assert all(-2048<=v<=2047 for v in mq[:9]) and all(-1024<=v<=1023 for v in mq[9:])
  packets[2]=oracle.command(0x5e68,oracle.cc(cc['matrix'],cc['offsets'],shift))
 if mask&4:
  vals=[cv[k] for k in m.CV_FIELDS]
  vq=[clamp(roundaway(f32(f32(v)*(256 if i in [0,1,2,4,5,6,7,8,9,10,11] else 1))),-2048 if i in [0,1,2,4,5,6,7,8,9,10,11] else -1024,2047 if i in [0,1,2,4,5,6,7,8,9,10,11] else 1023) for i,v in enumerate(vals)]
  vq[-2:]=vq[-2:][::-1]
  packets[4]=oracle.command(0x6468,oracle.cv(cv))
 records.append(struct.pack('<I21h12hI14h',mask,*cq,*mq,shift,*vq))
 b=bytearray(2860)
 for off in [52,68,244,260]:struct.pack_into('<I',b,off,1)
 post_count=0
 for bit,enable,packetoff,size in [(1,2092,2720,56),(2,2188,2776,44),(4,2200,2820,40)]:
  if not mask&bit:continue
  struct.pack_into('<I',b,enable,1);packet=packets[bit];assert len(packet)==size;b[packetoff:packetoff+size]=packet
  if bit==1:struct.pack_into('<III',b,2628,1,0x07802000+packetoff,(size-1)<<12)
  else:struct.pack_into('<II',b,2664+post_count*24,0x07802000+packetoff,(size-1)<<12);post_count+=1
 struct.pack_into('<I',b,2660,post_count);expected.append(b)
for p in sorted(P.glob('*-cst12_ipe-trees-private.json')):
 for root in json.loads(p.read_text()):add(1,cst=root['reserve']);counts['cst']+=1
for p in sorted((P.parent/'kernel351').glob('*-cc13_ipe-trees-private.json')):
 for root in json.loads(p.read_text()):
  for leaf in m.leaves(root['core']):add(2,cc=dict(matrix=leaf['matrix'],offsets=leaf['offsets'],shift=root['qfactor']));counts['cc']+=1
for p in sorted(P.glob('*-cv12_ipe-trees-private.json')):
 for root in json.loads(p.read_text()):
  for leaf in m.leaves(root['core']):add(4,cv=leaf['data']);counts['cv']+=1
assert counts==dict(cst=17,cc=737,cv=1350,combinations=0)
rng=random.Random(399)
for mask in range(8):
 for _ in range(16):
  low=[rng.randrange(1024) for _ in range(3)];high=[rng.randrange(low[i],1024) for i in range(3)]
  cst=dict(m_tab=[rng.randrange(-4096,4096)/1024 for _ in range(9)],s_tab=[rng.randrange(-1024,1024) for _ in range(3)],o_tab=[rng.randrange(1024) for _ in range(3)],c_x0_tab=low,c_x1_tab=high)
  shift=rng.randrange(4);cc=dict(shift=shift,matrix=[rng.randrange(-2048,2048)/(1<<(7+shift)) for _ in range(9)],offsets=[rng.randrange(-1024,1024) for _ in range(3)])
  cv=dict(zip(m.CV_FIELDS,[rng.randrange(-4096,4096)/256 if i in [0,1,2,4,5,6,7,8,9,10,11] else rng.randrange(-2048,2048)/2 for i in range(14)]))
  add(mask,cst,cc,cv);counts['combinations']+=1
(P/'colour-input-private.bin').write_bytes(b''.join(records));(P/'colour-expected-private.bin').write_bytes(b''.join(expected))
inc=P/'include';(inc/'linux').mkdir(parents=True,exist_ok=True)
(inc/'linux/types.h').write_text('#include <stdint.h>\ntypedef uint8_t u8;typedef uint16_t u16;typedef int16_t s16;typedef uint32_t u32;typedef uint64_t u64;\n')
(inc/'linux/errno.h').write_text('#define EINVAL 22\n#define ERANGE 34\n');(inc/'linux/string.h').write_text('#include <string.h>\n')
(inc/'linux/unaligned.h').write_text('#include <stdint.h>\nstatic inline void put_unaligned_le32(uint32_t v,void *p){uint8_t *b=p;b[0]=v;b[1]=v>>8;b[2]=v>>16;b[3]=v>>24;}\n')
(inc/'camss-icp-a5-colour.h').write_bytes((P/'camss-icp-a5-colour.h.proposed').read_bytes());(inc/'camss-icp-a5-ipe.h').write_text('#include <linux/types.h>\n#define CAMSS_A5_IPE_IQ_BYTES 2584U\nint camss_a5_ipe_encode_bypass_iq(void *,u32);\n')
(P/'colour.c').write_bytes((P/'camss-icp-a5-colour.c.proposed').read_bytes());source=(P/'camss-icp-a5-ipe.c.before').read_text();f=re.search(r'int camss_a5_ipe_encode_bypass_iq\([^;]+?\n\{.*?^\}\n',source,re.S|re.M);assert f
(P/'bypass.c').write_text('#include <string.h>\n#include <linux/errno.h>\n#include <linux/unaligned.h>\n#include "camss-icp-a5-ipe.h"\n'+f[0])
(P/'parcel-runner.c').write_text(r'''#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "camss-icp-a5-colour.h"
_Static_assert(sizeof(struct camss_a5_ipe_cst)==42,"CST fixture layout");
_Static_assert(sizeof(struct camss_a5_ipe_cc)==28,"CC fixture layout");
_Static_assert(sizeof(struct camss_a5_ipe_cv)==28,"CV fixture layout");
static unsigned invalid;
static void reject(struct camss_a5_ipe_colour *c,unsigned size,uint32_t iova){unsigned char b[2892],old[2892];memset(b,0xa7,sizeof b);memcpy(old,b,sizeof b);assert(camss_a5_ipe_encode_colour_iq(b,size,iova,c)<0);assert(!memcmp(b,old,sizeof b));invalid++;}
int main(int argc,char **argv){assert(argc==3);FILE *in=fopen(argv[1],"rb"),*out=fopen(argv[2],"wb");assert(in&&out);unsigned char record[102],b[2892];struct camss_a5_ipe_colour c={0};unsigned n=0;
 while(fread(record,1,102,in)==102){memset(&c,0,sizeof c);memcpy(&c.modules,record,4);memcpy(&c.cst,record+4,42);memcpy(&c.cc,record+46,28);memcpy(&c.cv,record+74,28);memset(b,0xa7,sizeof b);assert(!camss_a5_ipe_encode_colour_iq(b,sizeof b,0x07802000,&c));for(unsigned j=2860;j<sizeof b;j++)assert(b[j]==0xa7);assert(fwrite(b,1,2860,out)==2860);n++;}
 assert(feof(in));fclose(in);assert(!fclose(out));memset(&c,0,sizeof c);
 for(unsigned j=0;j<2860;j++)reject(&c,j,0x07802000);
 reject(NULL,sizeof b,0x07802000);assert(camss_a5_ipe_encode_colour_iq(NULL,sizeof b,0x07802000,&c)<0);invalid++;
 reject(&c,sizeof b,0);reject(&c,sizeof b,0x07802004);reject(&c,sizeof b,0xfffff500);
 c.modules=8;reject(&c,sizeof b,0x07802000);c.modules=0xffffffff;reject(&c,sizeof b,0x07802000);
 c.modules=1;
 for(unsigned i=0;i<9;i++){c.cst.matrix[i]=-4097;reject(&c,sizeof b,0x07802000);c.cst.matrix[i]=4096;reject(&c,sizeof b,0x07802000);c.cst.matrix[i]=0;}
 for(unsigned i=0;i<3;i++){c.cst.subtract[i]=-1025;reject(&c,sizeof b,0x07802000);c.cst.subtract[i]=1024;reject(&c,sizeof b,0x07802000);c.cst.subtract[i]=0;c.cst.offset[i]=1024;reject(&c,sizeof b,0x07802000);c.cst.offset[i]=0;c.cst.minimum[i]=1024;reject(&c,sizeof b,0x07802000);c.cst.minimum[i]=1;reject(&c,sizeof b,0x07802000);c.cst.minimum[i]=0;c.cst.maximum[i]=1024;reject(&c,sizeof b,0x07802000);c.cst.maximum[i]=0;}
 c.modules=2;c.cc.shift=4;reject(&c,sizeof b,0x07802000);c.cc.shift=0;
 for(unsigned i=0;i<9;i++){c.cc.matrix[i]=-2049;reject(&c,sizeof b,0x07802000);c.cc.matrix[i]=2048;reject(&c,sizeof b,0x07802000);c.cc.matrix[i]=0;}
 for(unsigned i=0;i<3;i++){c.cc.offset[i]=-1025;reject(&c,sizeof b,0x07802000);c.cc.offset[i]=1024;reject(&c,sizeof b,0x07802000);c.cc.offset[i]=0;}
 c.modules=4;
 for(unsigned i=0;i<3;i++){c.cv.luma[i]=-2049;reject(&c,sizeof b,0x07802000);c.cv.luma[i]=2048;reject(&c,sizeof b,0x07802000);c.cv.luma[i]=0;}
 for(unsigned i=0;i<8;i++){c.cv.chroma[i]=-2049;reject(&c,sizeof b,0x07802000);c.cv.chroma[i]=2048;reject(&c,sizeof b,0x07802000);c.cv.chroma[i]=0;}
 c.cv.y_offset=-1025;reject(&c,sizeof b,0x07802000);c.cv.y_offset=1024;reject(&c,sizeof b,0x07802000);c.cv.y_offset=0;
 for(unsigned i=0;i<2;i++){c.cv.offset[i]=-1025;reject(&c,sizeof b,0x07802000);c.cv.offset[i]=1024;reject(&c,sizeof b,0x07802000);c.cv.offset[i]=0;}
 c.modules=0;memset(&c.cst,0xff,sizeof c.cst);memset(&c.cc,0xff,sizeof c.cc);memset(&c.cv,0xff,sizeof c.cv);assert(!camss_a5_ipe_encode_colour_iq(b,sizeof b,0x20,&c));assert(!camss_a5_ipe_encode_colour_iq(b,sizeof b,0xfffff4c0,&c));
 printf("cases=%u invalid=%u\n",n,invalid);return 0;}
''')
rows=[];expected=b''.join(expected)
for arch,compiler,flags,launch in [('host','gcc',['-fsanitize=address,undefined','-no-pie'],[]),('aarch64','aarch64-linux-gnu-gcc',['-static'],['qemu-aarch64'])]:
 binary=P/('parcel-'+arch);q=subprocess.run([compiler,'-std=c11','-O2','-Wall','-Wextra','-Werror',*flags,'-I'+str(inc),str(P/'colour.c'),str(P/'bypass.c'),str(P/'parcel-runner.c'),'-o',str(binary)],capture_output=True);assert not q.returncode,q.stderr.decode()
 actual=P/(arch+'-iq-private.bin');q=subprocess.run([*launch,str(binary),str(P/'colour-input-private.bin'),str(actual)],capture_output=True,timeout=30);assert not q.returncode,q.stderr.decode()
 match=re.fullmatch(r'cases=(\d+) invalid=(\d+)\n',q.stdout.decode());assert match and int(match[1])==len(records) and actual.read_bytes()==expected
 rows.append(dict(arch=arch,cases=int(match[1]),invalid_no_write_cases=int(match[2]),compared_bytes=len(expected),different_bytes=0,passed=True))
assert set(oracle.providers)=={'0x4cd8b0','0x4cda68'}
report=dict(stage=399,tests=rows,input_cases=counts,actual_c_full_parameter_page=True,original_hal_numerical_and_cdm_packets=True,actual_target_native_cv_order_used=True,cst_and_cc_complete_calculation_executed=True,cv_inlined_oem_calculation_executed=True,no_arithmetic_or_cdm_stub=True,iq_bytes=2860,within_existing4096_iq_page=True,enabled_modules_only_validated=True,invalid_output_unchanged=True,host_asan_ubsan=True,aarch64_qemu_not_hardware=True,original_instructions=oracle.instructions,phone_changed=False,passed=True)
(HERE/'parcel-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
