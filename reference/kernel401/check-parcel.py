"""Compare actual C old/new pages against target packets and LUT encodings."""
from pathlib import Path
import importlib.util,json,re,shutil,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'contract-validation.json').read_text())['passed']
spec=importlib.util.spec_from_file_location('gamma401',HERE/'gamma-model.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g);oracle=g.Gamma()
inc=P/'include';shutil.copytree(P.parent/'kernel399/include',inc,dirs_exist_ok=True)
(inc/'camss-icp-a5-colour.h').write_bytes((P/'camss-icp-a5-colour.h.proposed').read_bytes());(P/'colour.c').write_bytes((P/'camss-icp-a5-colour.c.proposed').read_bytes())
s=(P/'camss-icp-a5-ipe.c.before').read_text();f=re.search(r'int camss_a5_ipe_encode_bypass_iq\([^;]+?\n\{.*?^\}\n',s,re.S|re.M);assert f
(P/'bypass.c').write_text('#include <string.h>\n#include <linux/errno.h>\n#include <linux/unaligned.h>\n#include "camss-icp-a5-ipe.h"\n'+f[0])
old=P.parent/'kernel399';chain_input=(old/'colour-input-private.bin').read_bytes();chain_gold=bytearray((old/'colour-expected-private.bin').read_bytes());assert len(chain_input)//102==2232
for i in range(2232):
 mask=struct.unpack_from('<I',chain_input,i*102)[0];n=0
 if mask&1:struct.pack_into('<I',chain_gold,i*2860+2640,20)
 for bit in [2,4]:
  if mask&bit:struct.pack_into('<I',chain_gold,i*2860+2672+24*n,20);n+=bool(mask&bit)
(P/'chain-input-private.bin').write_bytes(chain_input);(P/'chain-expected-private.bin').write_bytes(chain_gold)
cc_input=(P.parent/'kernel398/cc-input-private.bin').read_bytes();cc_gold=bytearray((P.parent/'kernel398/aarch64-iq-private.bin').read_bytes());assert len(cc_input)//28==1121
for i in range(1121):struct.pack_into('<I',cc_gold,i*2700+2640,20)
(P/'cc-input-private.bin').write_bytes(cc_input);(P/'cc-expected-private.bin').write_bytes(cc_gold)
lutraw=(P/'gamma-lut-oracle-private.bin').read_bytes();luts=[lutraw[i:i+1024] for i in range(0,len(lutraw),1024)];assert len(luts)==97
fixtures={mask:next(i for i in reversed(range(2232)) if struct.unpack_from('<I',chain_input,i*102)[0]==mask) for mask in range(8)}
records=[];expected=[];iova=0x07802000;headers=oracle.headers(iova+2944)
for i in range(97):
 mask=i%8;j=fixtures[mask];record=chain_input[j*102:(j+1)*102];tables=[luts[(i+17*bank)%97] for bank in range(3)];words=[struct.unpack('<256I',b) for b in tables]
 base=[v&1023 for bank in words for v in bank];delta=[((v>>10)&1023)-1024 if v&(1<<19) else (v>>10)&1023 for bank in words for v in bank]
 records.append(record+struct.pack('<768H768h',*base,*delta))
 b=bytearray(6016);b[:2860]=chain_gold[j*2860:(j+1)*2860];b[2752:2892]=b[2720:2860];b[2720:2752]=bytes(32)
 if mask&1:struct.pack_into('<I',b,2632,iova+2752)
 n=0
 for bit,off in [(2,2808),(4,2852)]:
  if mask&bit:struct.pack_into('<I',b,2664+24*n,iova+off);n+=1
 struct.pack_into('<6I',b,2664+24*n,iova+2896,35<<12,12,0,0,0);struct.pack_into('<I',b,2660,n+1);struct.pack_into('<I',b,2192,1)
 b[2896:2932]=headers;b[2944:6016]=b''.join(tables);expected.append(b)
(P/'gamma-input-private.bin').write_bytes(b''.join(records));(P/'gamma-expected-private.bin').write_bytes(b''.join(expected))
(P/'parcel-runner.c').write_text(r'''#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "camss-icp-a5-colour.h"
_Static_assert(sizeof(struct camss_a5_ipe_gamma)==3072,"Gamma fixture layout");
static unsigned invalid;
static void reject(const struct camss_a5_ipe_colour *c,const struct camss_a5_ipe_gamma *g,unsigned size,uint32_t iova){unsigned char b[6048],old[6048];memset(b,0xa7,sizeof b);memcpy(old,b,sizeof b);assert(camss_a5_ipe_encode_gamma_iq(b,size,iova,c,g)<0);assert(!memcmp(b,old,sizeof b));invalid++;}
int main(int argc,char **argv){assert(argc==4);int gamma=!strcmp(argv[1],"gamma"),cc=!strcmp(argv[1],"cc");unsigned input=gamma?3174:cc?28:102,output=gamma?6016:cc?2700:2860;
 FILE *in=fopen(argv[2],"rb"),*out=fopen(argv[3],"wb");assert(in&&out);unsigned char record[3174],b[6048];struct camss_a5_ipe_colour c={0};struct camss_a5_ipe_gamma g={0};unsigned n=0;
 while(fread(record,1,input,in)==input){memset(&c,0,sizeof c);if(cc)memcpy(&c.cc,record,28);else{memcpy(&c.modules,record,4);memcpy(&c.cst,record+4,42);memcpy(&c.cc,record+46,28);memcpy(&c.cv,record+74,28);}if(gamma)memcpy(&g,record+102,3072);memset(b,0xa7,sizeof b);
 int ret=gamma?camss_a5_ipe_encode_gamma_iq(b,sizeof b,0x07802000,&c,&g):cc?camss_a5_ipe_encode_cc_iq(b,sizeof b,0x07802000,&c.cc):camss_a5_ipe_encode_colour_iq(b,sizeof b,0x07802000,&c);
 assert(!ret);for(unsigned j=output;j<sizeof b;j++)assert(b[j]==0xa7);assert(fwrite(b,1,output,out)==output);n++;}
 assert(feof(in));fclose(in);assert(!fclose(out));memset(&c,0,sizeof c);memset(&g,0,sizeof g);
 if(gamma){for(unsigned j=0;j<6016;j++)reject(&c,&g,j,0x07802000);reject(&c,NULL,sizeof b,0x07802000);assert(camss_a5_ipe_encode_gamma_iq(NULL,sizeof b,0x07802000,&c,&g)<0);invalid++;
 reject(&c,&g,sizeof b,0);reject(&c,&g,sizeof b,0x07802004);reject(&c,&g,sizeof b,0xffffe8a0);c.modules=8;reject(&c,&g,sizeof b,0x07802000);c.modules=0;
 for(unsigned bank=0;bank<3;bank++)for(unsigned edge=0;edge<2;edge++){unsigned i=edge?255:0;g.base[bank][i]=1024;reject(&c,&g,sizeof b,0x07802000);g.base[bank][i]=0;g.delta[bank][i]=-513;reject(&c,&g,sizeof b,0x07802000);g.delta[bank][i]=512;reject(&c,&g,sizeof b,0x07802000);g.delta[bank][i]=0;}
 assert(!camss_a5_ipe_encode_gamma_iq(b,sizeof b,0x20,NULL,&g));assert(!camss_a5_ipe_encode_gamma_iq(b,sizeof b,0xffffe880,NULL,&g));}
 printf("cases=%u invalid=%u\n",n,invalid);return 0;}
''')
rows=[]
for arch,compiler,flags,launch in [('host','gcc',['-fsanitize=address,undefined','-no-pie'],[]),('aarch64','aarch64-linux-gnu-gcc',['-static'],['qemu-aarch64'])]:
 binary=P/('parcel-'+arch);q=subprocess.run([compiler,'-std=c11','-O2','-Wall','-Wextra','-Werror',*flags,'-I'+str(inc),str(P/'colour.c'),str(P/'bypass.c'),str(P/'parcel-runner.c'),'-o',str(binary)],capture_output=True);assert not q.returncode,q.stderr.decode()
 for kind,count,width in [('cc',1121,2700),('chain',2232,2860),('gamma',97,6016)]:
  actual=P/(arch+'-'+kind+'-private.bin');q=subprocess.run([*launch,str(binary),kind,str(P/(kind+'-input-private.bin')),str(actual)],capture_output=True,timeout=40);assert not q.returncode,q.stderr.decode()
  match=re.fullmatch(r'cases=(\d+) invalid=(\d+)\n',q.stdout.decode());assert match and int(match[1])==count and actual.read_bytes()==(P/(kind+'-expected-private.bin')).read_bytes()
  rows.append(dict(arch=arch,kind=kind,cases=count,invalid_no_write_cases=int(match[2]),compared_bytes=count*width,different_bytes=0,passed=True))
report=dict(stage=401,tests=rows,actual_c_encoders_executed=True,generic_type20_correction_compared_to_target_submit=True,gamma_lut_math_reused_from_original97_curves=True,original_three_dmi_headers_and_nested_relocations_used=True,typed_base_delta_inputs_no_arbitrary_cdm=True,channel_order='G B R, selectors1/2/3',gamma_iq_bytes=6016,gamma_lut_bytes=3072,host_asan_ubsan=True,aarch64_qemu_not_hardware=True,phone_changed=False,passed=True)
(HERE/'parcel-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
