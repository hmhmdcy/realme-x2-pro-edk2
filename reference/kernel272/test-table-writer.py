"""Execute the actual C writer with mocked CCI; compare independent OEM records."""
from pathlib import Path
import hashlib,json,re,subprocess,sys
import host
R=Path(__file__).resolve().parent
attempt=int(sys.argv[1]) if len(sys.argv)>1 else 1
assert attempt in [1,2,3]
P=host.PRIVATE/('table-writer-test'+('-r'+str(attempt) if attempt>1 else ''));P.mkdir(mode=0o700)
source=(R/'s5kgw1.c').read_text()
def block(marker):
 a=source.index(marker);b=source.index('{',a);depth=1;i=b+1
 while depth:
  depth+=int(source[i]=='{')-int(source[i]=='}');i+=1
 return source[a:i]
reg=block('struct s5kgw1_reg {')+';'
writer=block('static int s5kgw1_write_table(')
prefix=r'''
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
typedef uint8_t u8; typedef uint16_t u16; typedef uint32_t u32;
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define min_t(t,a,b) ((t)(a)<(t)(b)?(t)(a):(t)(b))
#define CCI_REG8(a) ((a)|(1U<<16))
#define CCI_REG16(a) ((a)|(2U<<16))
struct regmap {int unused;};
struct s5kgw1 {struct regmap *regmap; unsigned int burst_bytes;};
static unsigned int calls,fail_at;
static void put_unaligned_be16(u16 v,u8 *p) {p[0]=v>>8;p[1]=v;}
static void usleep_range(unsigned int lo,unsigned int hi) {(void)hi;printf("d %u\n",lo);}
static int cci_write(struct regmap *m,u32 reg,uint64_t value,int *err) {
 (void)m;(void)err; calls++;
 if(calls==fail_at)return -EIO;
 unsigned int width=reg>>16;
 printf("w %04x %u ",reg&65535,width);
 for(unsigned int n=width;n;n--)printf("%02x",(unsigned int)(value>>(8*(n-1)))&255);
 puts("");return 0;
}
static int regmap_raw_write(struct regmap *m,u32 reg,const void *p,size_t n) {
 (void)m;calls++;if(calls==fail_at)return -EIO;
 printf("w %04x %zu ",reg,n);
 for(size_t i=0;i<n;i++)printf("%02x",((const u8*)p)[i]);
 puts("");return 0;
}
'''
main=r'''
int main(int argc,char **argv) {
 if(argc!=4)return 2;
 struct s5kgw1 sensor={.burst_bytes=(unsigned int)atoi(argv[2])};
 fail_at=atoi(argv[3]);
 const struct s5kgw1_reg *regs;unsigned int n;
 switch(atoi(argv[1])) {
 case 0:regs=s5kgw1_init_regs;n=ARRAY_SIZE(s5kgw1_init_regs);break;
 case 2:regs=s5kgw1_mode2_regs;n=ARRAY_SIZE(s5kgw1_mode2_regs);break;
 case 4:regs=s5kgw1_mode4_regs;n=ARRAY_SIZE(s5kgw1_mode4_regs);break;
 default:return 3;
 }
 int ret=s5kgw1_write_table(&sensor,regs,n);
 printf("r %d calls %u\n",ret,calls);return 0;
}
'''
(P/'harness.c').write_text(prefix+reg+'\n#include "'+str(R/'s5kgw1-tables.h')+'"\n'+writer+main)
subprocess.run(['gcc','-std=gnu11','-Wall','-Wextra','-Werror','-O2','-fsanitize=undefined',str(P/'harness.c'),'-o',str(P/'harness')],check=True)
data=json.loads((host.PRIVATE.parent/'kernel270/gw1-sunny-direct-registers-private.json').read_text())
tests=0;transfers=0;delay_checks=0;failure_tests=0
for index,regs in [(0,data['init']),(2,data['modes'][2]),(4,data['modes'][4])]:
 for cap in [2,4,6,8]:
  expected=[];write_count=0
  for r in regs:
   if r['operation']=='WRITE':
    chunks=[b''.join(v.to_bytes(r['value_bytes'],'big') for v in r['values'])]
   else:
    assert r['operation']=='WRITE_BURST' and r['address']==0x6f12
    payload=b''.join(v.to_bytes(2,'big') for v in r['values'])
    chunks=[payload[n:n+cap] for n in range(0,len(payload),cap)]
   for payload in chunks:
    expected.append('w %04x %d %s'%(r['address'],len(payload),payload.hex()));write_count+=1
   if r['delays_us'][0]:expected.append('d '+str(r['delays_us'][0]));delay_checks+=1
  text=subprocess.check_output([str(P/'harness'),str(index),str(cap),'0'],text=True)
  assert text.splitlines()==expected+[f'r 0 calls {write_count}'],(index,cap)
  transfers+=write_count;tests+=1
  # Fail before/inside/after a burst and at the last write: no later transfer or delay.
  for fail in sorted({1,2,7,13,14,15,write_count//2,write_count-1,write_count}):
   if fail>write_count:continue
   prefix=[];n=0
   for line in expected:
    if line.startswith('w '):
     n+=1
     if n==fail:break
    prefix.append(line)
   text=subprocess.check_output([str(P/'harness'),str(index),str(cap),str(fail)],text=True)
   assert text.splitlines()==prefix+[f'r -5 calls {fail}'],(index,cap,fail)
   failure_tests+=1
report=dict(stage=272,actual_c_writer_executed=True,source_sha256=hashlib.sha256(source.encode()).hexdigest(),
 generated_tables_sha256=hashlib.sha256((R/'s5kgw1-tables.h').read_bytes()).hexdigest(),
 successful_table_runs=tests,independent_expected_transfers=transfers,delay_checks=delay_checks,
 fail_fast_cases=failure_tests,whole_words_big_endian=True,burst_port_repeated_every_chunk=True,
 eight_bit_flip_write_preserved=True,undefined_behavior_sanitizer=True,phone_unchanged=True,
 physical_i2c_and_cphy_still_unverified=True)
(R/'table-writer-test-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
