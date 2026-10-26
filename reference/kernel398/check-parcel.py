"""Check complete typed IQ/program storage against the recovered firmware layout."""
from pathlib import Path
import json,re,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;old=P
assert json.loads((HERE/'colour-validation.json').read_text())['passed']
inc=P/'include';(inc/'linux').mkdir(parents=True,exist_ok=True)
(inc/'linux/types.h').write_text('#include <stdint.h>\ntypedef uint8_t u8;typedef int16_t s16;typedef uint32_t u32;typedef uint64_t u64;\n')
(inc/'linux/errno.h').write_text('#define EINVAL 22\n#define ERANGE 34\n')
(inc/'linux/string.h').write_text('#include <string.h>\n')
(inc/'linux/unaligned.h').write_text('#include <stdint.h>\nstatic inline void put_unaligned_le32(uint32_t v,void *p){uint8_t *b=p;b[0]=v;b[1]=v>>8;b[2]=v>>16;b[3]=v>>24;}\n')
(inc/'camss-icp-a5-colour.h').write_bytes((P/'camss-icp-a5-colour.h.proposed').read_bytes())
(inc/'camss-icp-a5-ipe.h').write_text('#include <linux/types.h>\n#define CAMSS_A5_IPE_IQ_BYTES 2584U\nint camss_a5_ipe_encode_bypass_iq(void *,u32);\n')
c=P/'colour.c';c.write_bytes((P/'camss-icp-a5-colour.c.proposed').read_bytes())
s=(P.parent/'kernel397/camss-icp-a5-ipe.c.before').read_text();m=re.search(r'int camss_a5_ipe_encode_bypass_iq\([^;]+?\n\{.*?^\}\n',s,re.S|re.M);assert m
base=P/'bypass.c';base.write_text('#include <string.h>\n#include <linux/errno.h>\n#include <linux/unaligned.h>\n#include "camss-icp-a5-ipe.h"\n'+m[0])
runner=P/'parcel-runner.c';runner.write_text(r'''#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "camss-icp-a5-colour.h"
static unsigned invalid;
static void reject(struct camss_a5_ipe_cc *c,unsigned size,uint32_t iova){unsigned char b[2732],old[2732];memset(b,0xa7,sizeof b);memcpy(old,b,sizeof b);assert(camss_a5_ipe_encode_cc_iq(b,size,iova,c)<0);assert(!memcmp(b,old,sizeof b));invalid++;}
int main(int argc,char **argv){assert(argc==3);FILE *in=fopen(argv[1],"rb"),*out=fopen(argv[2],"wb");assert(in&&out);unsigned char record[28],b[2732];struct camss_a5_ipe_cc cc={0};unsigned n=0;
 while(fread(record,1,28,in)==28){memcpy(&cc,record,28);memset(b,0xa7,sizeof b);assert(!camss_a5_ipe_encode_cc_iq(b,sizeof b,0x07802000,&cc));for(unsigned j=2700;j<sizeof b;j++)assert(b[j]==0xa7);assert(fwrite(b,1,2700,out)==2700);n++;}
 assert(feof(in));fclose(in);assert(!fclose(out));memset(&cc,0,sizeof cc);
 for(unsigned j=0;j<2700;j++)reject(&cc,j,0x07802000);
 reject(NULL,sizeof b,0x07802000);assert(camss_a5_ipe_encode_cc_iq(NULL,sizeof b,0x07802000,&cc)<0);invalid++;
 reject(&cc,sizeof b,0);reject(&cc,sizeof b,0x07802004);reject(&cc,sizeof b,0xfffff580);
 cc.shift=4;reject(&cc,sizeof b,0x07802000);cc.shift=0;
 for(unsigned j=0;j<9;j++){cc.matrix[j]=-2049;reject(&cc,sizeof b,0x07802000);cc.matrix[j]=2048;reject(&cc,sizeof b,0x07802000);cc.matrix[j]=0;}
 for(unsigned j=0;j<3;j++){cc.offset[j]=-1025;reject(&cc,sizeof b,0x07802000);cc.offset[j]=1024;reject(&cc,sizeof b,0x07802000);cc.offset[j]=0;}
 assert(!camss_a5_ipe_encode_cc_iq(b,sizeof b,0x20,&cc));assert(!camss_a5_ipe_encode_cc_iq(b,sizeof b,0xfffff560,&cc));
 printf("cases=%u invalid=%u\n",n,invalid);return 0;}
''')
packets=(old/'cc-expected-private.bin').read_bytes();records=(old/'cc-input-private.bin').read_bytes();assert len(packets)//44==len(records)//28==1121
expected=[]
for i in range(1121):
 b=bytearray(2700)
 for off in [52,68,244,260,2188,2628]:struct.pack_into('<I',b,off,1)
 struct.pack_into('<II',b,2632,0x07802000+2656,43<<12);b[2656:2700]=packets[i*44:(i+1)*44];expected.append(b)
expected=b''.join(expected);rows=[]
for arch,compiler,flags,launch in [('host','gcc',['-fsanitize=address,undefined','-no-pie'],[]),('aarch64','aarch64-linux-gnu-gcc',['-static'],['qemu-aarch64'])]:
 binary=P/('parcel-'+arch);args=[compiler,'-std=c11','-O2','-Wall','-Wextra','-Werror',*flags,'-I'+str(inc),str(c),str(base),str(runner),'-o',str(binary)]
 q=subprocess.run(args,capture_output=True);assert q.returncode==0,q.stderr.decode()
 actual=P/(arch+'-iq-private.bin');q=subprocess.run([*launch,str(binary),str(old/'cc-input-private.bin'),str(actual)],capture_output=True,timeout=30);assert q.returncode==0,q.stderr.decode()
 match=re.fullmatch(r'cases=(\d+) invalid=(\d+)\n',q.stdout.decode());assert match and int(match[1])==1121 and actual.read_bytes()==expected
 rows.append(dict(arch=arch,cases=int(match[1]),invalid_no_write_cases=int(match[2]),compared_bytes=len(expected),different_bytes=0,passed=True))
report=dict(stage=398,tests=rows,actual_colour_encoder_and_base_iq_functions=True,program_arrays_and_commands_in_existing_iq_page=True,iq_bytes=2700,empty_array_offset=2592,post_array_offset=2624,command_offset=2656,command_bytes=44,full_output_compared_to_recovered_hal_commands_and_fw_layout=True,unmapped_and_wrapping_iova_rejected=True,short_and_invalid_output_unchanged=True,host_asan_ubsan=True,aarch64_qemu_not_hardware=True,passed=True)
(HERE/'parcel-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
