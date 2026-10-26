"""Compare typed LTM pages with target IQ/DMI and original LUT packers."""
from pathlib import Path
import json,random,re,struct,subprocess
import host
from oracle import Oracle,module,HERE
P=host.PRIVATE;rng=random.Random(405);oracle=Oracle();ltm_dmi=Oracle();g=module('gamma402',HERE.parent/'kernel402/gamma-model.py').Gamma()
source=(P.parent/'kernel403/sources/ltm13setting.cpp').read_text();packers=[]
for name in ['Pack1D16EntrySignedLUT','Pack1D64EntrySignedLUT','Pack1D64EntryUnsignedLUT','Pack1D64EntryUnsignedHLUT']:
 match=re.search(r'static void '+name+r'\([^;]+?\n\{.*?^\}',source,re.S|re.M);assert match;packers.append(match[0])
prefix='''#include <algorithm>
#include <cassert>
#include <cstdint>
#include <cstdio>
using INT16=int16_t;using INT32=int32_t;using UINT16=uint16_t;using UINT32=uint32_t;
constexpr unsigned LCE_SCALE_LUT_SIZE=17,LTM_SCALE_LUT_SIZE=65,LTM_CURVE_LUT_SIZE=65,LTM_GAMMA_LUT_SIZE=64;
struct IQSettingUtils{static INT16 MinINT16(INT16 a,INT16 b){return std::min(a,b);}static INT32 MinINT32(INT32 a,INT32 b){return std::min(a,b);}};
'''
main='''int main(){uint32_t in[67];while(fread(in,sizeof in,1,stdin)==1){INT32 a[65],out[64];INT16 b[65];for(unsigned i=0;i<65;i++){a[i]=static_cast<INT32>(in[i+2]);b[i]=static_cast<INT16>(a[i]);}switch(in[0]){case 0:Pack1D64EntryUnsignedLUT(a,out,2);break;case 1:Pack1D64EntrySignedLUT(b,out,2);break;case 2:Pack1D16EntrySignedLUT(b,out,2);break;case 3:Pack1D64EntryUnsignedHLUT(a,out,2);break;default:assert(false);}assert(fwrite(out,4,in[1],stdout)==in[1]);}return 0;}'''
(P/'original-packers-private.cpp').write_text(prefix+'\n'.join(packers)+main)
q=subprocess.run(['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror',str(P/'original-packers-private.cpp'),'-o',str(P/'original-packers-private')],capture_output=True);assert not q.returncode,q.stderr.decode()
banks=[(0,64),(0,64),(0,64),(1,64),(0,64),(2,16),(2,16)]+[(3,64)]*5
node_records=[]
for index in range(128):
 for kind,count in banks:
  lo,hi=(-2048,2047) if kind in [1,2] else (0,16383 if kind==3 else 4095)
  nodes=[rng.randint(lo,hi) for _ in range(65)]
  if index%4==0:nodes=[lo if i%2 else hi for i in range(65)]
  elif index%4==1:nodes=[lo+(hi-lo)*i//64 for i in range(65)]
  elif index%4==2:nodes=[hi]*65
  node_records.append(struct.pack('<2I65i',kind,count,*nodes))
q=subprocess.run([str(P/'original-packers-private')],input=b''.join(node_records),capture_output=True);assert not q.returncode,q.stderr.decode();packed=q.stdout;table_pos=0
contract=json.loads((HERE.parent/'kernel403/contract-validation.json').read_text());widths=[f['width'] for f in contract['iq_fields'][1:]]
old=P.parent/'kernel402';chain=(old/'chain-input-private.bin').read_bytes();gold=(old/'chain-expected-private.bin').read_bytes();gamma_inputs=(old/'gamma-input-private.bin').read_bytes();gamma_gold=(old/'gamma-expected-private.bin').read_bytes()
fixtures={mask:next(i for i in reversed(range(len(chain)//102)) if struct.unpack_from('<I',chain,i*102)[0]==mask) for mask in range(8)}
inputs=[];outputs=[];rows=[]
offsets=[0,48,304,560,816,1072,1328,1392,1456,1712,1968,2224,2480]
for index in range(128):
 mask=index%8;with_gamma=(index//8)%2;dc=(index//16)%2;ip=(index//32)%2;filter_on=(index//64)%2;has_colour=index%17!=0;mask=mask if has_colour else 0
 iova=[0x20,0x07802000,0xffffdd00][index%3];j=fixtures[mask];record=chain[j*102:(j+1)*102];colour=record[:46]+bytes(2)+record[46:];gamma=gamma_inputs[(index%97)*3174+102:(index%97+1)*3174]
 values=[rng.randrange(1<<bits) for bits in widths];values[2]=filter_on;values[-2:]=[dc,ip]
 if index==0:values=[0]*22
 elif index==127:values=[(1<<bits)-1 for bits in widths]
 iq=struct.pack('<22I',*values);weights=[rng.getrandbits(16) for _ in range(12)];typed=bytearray(iq+struct.pack('<12H',*weights));tables=bytearray(struct.pack('<12I',*weights))
 for kind,count in banks:
  raw=packed[table_pos:table_pos+4*count];table_pos+=4*count;tables+=raw;bits=14 if kind==3 else 12;limit=1<<bits
  for word in struct.unpack('<'+str(count)+'I',raw):
   base=word&(limit-1);delta=(word>>bits)&(limit-1);delta=delta-limit if delta&(limit//2) else delta
   if kind in [1,2]:base=base-limit if base&(limit//2) else base;typed+=struct.pack('<hh',base,delta)
   else:typed+=struct.pack('<Hh',base,delta)
 assert len(typed)==2800 and len(tables)==2736
 b=bytearray(8944);b[:2584]=gold[j*2860:j*2860+2584];b[2784:2924]=gold[j*2860+2720:(j+1)*2860];b[2096:2188]=oracle.iq(values)
 def program(at,address,size,kind=20):struct.pack_into('<6I',b,at,address,(size-1)<<12,kind,0,0,0)
 pre=2624;post=2688;n=0
 if mask&1:program(pre+8,iova+2784,56);n+=1
 program(pre+8+24*n,iova+6048,156,11);struct.pack_into('<I',b,pre+4,n+1);n=0
 for bit,off,size in [(2,2840,44),(4,2884,40)]:
  if mask&bit:program(post+8+24*n,iova+off,size);n+=1
 if with_gamma:
  program(post+8+24*n,iova+2928,36,12);n+=1;struct.pack_into('<I',b,2192,1);b[2928:2964]=g.headers(iova+2976);b[2976:6048]=gamma_gold[(index%97)*6016+2944:(index%97+1)*6016]
 struct.pack_into('<I',b,post+4,n);b[6048:6204]=ltm_dmi.headers(iova+6208)[0];b[6208:8944]=tables
 inputs.append(struct.pack('<3I',has_colour,with_gamma,iova)+colour+gamma+typed);outputs.append(b);rows.append(dict(case=index,modules=mask,gamma=bool(with_gamma),data_collection=values[-2],image_processing=values[-1],mask_filter=values[2],iova=iova))
assert table_pos==len(packed);(P/'ltm-input-private.bin').write_bytes(b''.join(inputs));(P/'ltm-expected-private.bin').write_bytes(b''.join(outputs))
runner=r'''#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "camss-icp-a5-colour.h"
_Static_assert(sizeof(struct camss_a5_ipe_ltm)==2800,"LTM fixture ABI");
_Static_assert(sizeof(struct camss_a5_ipe_colour)==104,"colour fixture ABI");
static unsigned rejects;
static void reject(struct camss_a5_ipe_colour *c,struct camss_a5_ipe_gamma *g,struct camss_a5_ipe_ltm *l,unsigned size,uint32_t iova){unsigned char out[9008],old[9008];memset(out,0xa7,sizeof out);memcpy(old,out,sizeof out);assert(camss_a5_ipe_encode_ltm_iq(out,size,iova,c,g,l)<0);assert(!memcmp(out,old,sizeof out));rejects++;}
int main(int argc,char **argv){assert(argc==3);FILE *in=fopen(argv[1],"rb"),*out=fopen(argv[2],"wb");assert(in&&out);unsigned char record[5988],b[9008];unsigned n=0;struct camss_a5_ipe_colour c;struct camss_a5_ipe_gamma g;struct camss_a5_ipe_ltm l;
while(fread(record,1,sizeof record,in)==sizeof record){uint32_t flags[3];memcpy(flags,record,12);memcpy(&c,record+12,104);memcpy(&g,record+116,3072);memcpy(&l,record+3188,2800);memset(b,0xa7,sizeof b);assert(!camss_a5_ipe_encode_ltm_iq(b,sizeof b,flags[2],flags[0]?&c:NULL,flags[1]?&g:NULL,&l));for(unsigned i=8944;i<sizeof b;i++)assert(b[i]==0xa7);assert(fwrite(b,1,8944,out)==8944);n++;}assert(feof(in));fclose(in);assert(!fclose(out));memset(&c,0,sizeof c);memset(&g,0,sizeof g);memset(&l,0,sizeof l);
for(unsigned i=0;i<3;i++){unsigned sizes[]={0,2583,8943};reject(&c,&g,&l,sizes[i],0x7802000);}reject(&c,&g,NULL,sizeof b,0x7802000);reject(&c,&g,&l,sizeof b,0);reject(&c,&g,&l,sizeof b,4);reject(&c,&g,&l,sizeof b,0xffffdd20);assert(camss_a5_ipe_encode_ltm_iq(NULL,sizeof b,0x7802000,&c,&g,&l)<0);
unsigned widths[]={1,1,1,4,6,6,6,7,10,10,3,3,3,2,2,2,5,12,1,1,1,1};for(unsigned i=0;i<22;i++){uint32_t v=1u<<widths[i];memcpy((unsigned char*)&l.iq+4*i,&v,4);reject(&c,&g,&l,sizeof b,0x7802000);memset(&l.iq,0,sizeof l.iq);}
for(unsigned family=0;family<5;family++)for(unsigned bank=0;bank<(family==0?2:family==4?5:1);bank++)for(unsigned edge=0;edge<2;edge++){
struct camss_a5_ipe_ltm_unsigned *u=family==0?l.la[bank]:family==1?l.curve:family==2?l.mask:family==4?l.reverse_gamma[bank]:NULL;
if(u){unsigned bits=family==4?14:12,k=edge?63:0;u[k].base=1u<<bits;reject(&c,&g,&l,sizeof b,0x7802000);u[k].base=0;u[k].delta=-(1<<(bits-1))-1;reject(&c,&g,&l,sizeof b,0x7802000);u[k].delta=1<<(bits-1);reject(&c,&g,&l,sizeof b,0x7802000);u[k].delta=0;}}
for(unsigned family=0;family<3;family++)for(unsigned edge=0;edge<2;edge++){struct camss_a5_ipe_ltm_signed *s=family?l.lce[family-1]:l.scale;unsigned k=edge?(family?15:63):0;s[k].base=-2049;reject(&c,&g,&l,sizeof b,0x7802000);s[k].base=2048;reject(&c,&g,&l,sizeof b,0x7802000);s[k].base=0;s[k].delta=-2049;reject(&c,&g,&l,sizeof b,0x7802000);s[k].delta=2048;reject(&c,&g,&l,sizeof b,0x7802000);s[k].delta=0;}
c.modules=8;reject(&c,&g,&l,sizeof b,0x7802000);c.modules=0;g.base[2][255]=1024;reject(&c,&g,&l,sizeof b,0x7802000);g.base[2][255]=0;g.delta[1][0]=-513;reject(&c,&g,&l,sizeof b,0x7802000);printf("cases=%u invalid=%u\n",n,rejects);return 0;}
'''
(P/'ltm-runner.c').write_text(runner);arch_rows=[]
for arch,cc,flags,launch in [('host','gcc',['-fsanitize=address,undefined','-no-pie'],[]),('aarch64','aarch64-linux-gnu-gcc',['-static'],['qemu-aarch64'])]:
 binary=P/('ltm-page-'+arch);q=subprocess.run([cc,'-std=c11','-O2','-Wall','-Wextra','-Werror',*flags,'-I'+str(P/'include'),str(P/'colour.c'),str(P/'bypass.c'),str(P/'ltm-runner.c'),'-o',str(binary)],capture_output=True);assert not q.returncode,q.stderr.decode()
 actual=P/(arch+'-ltm-page-private.bin');q=subprocess.run([*launch,str(binary),str(P/'ltm-input-private.bin'),str(actual)],capture_output=True);assert not q.returncode,q.stderr.decode();assert actual.read_bytes()==b''.join(outputs),arch
 match=re.fullmatch(r'cases=(\d+) invalid=(\d+)\n',q.stdout.decode());assert match and int(match[1])==128
 arch_rows.append(dict(architecture=arch,cases=128,invalid_unchanged_destination=int(match[2]),compared_bytes=len(outputs)*8944,different_bytes=0,passed=True))
report=dict(stage=405,architectures=arch_rows,case_parameters=rows,iq_actual_original_hal_fragment=True,dmi_actual_original_hal_and_nested_relocations=True,lut_packing_original_pinned_source_reference=True,full_ltm_numeric_math_not_claimed=True,typed_quantized_segments_no_arbitrary_commands_or_iova=True,iq_bytes=8944,iq_allocation_bytes=12288,ltm_cpu_copy_bytes=2800,pre_max_programs=2,post_max_programs=3,host_asan_ubsan=True,aarch64_qemu=True,phone_accessed=False,passed=True)
(HERE/'parcel-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='case_parameters'},indent=2))
