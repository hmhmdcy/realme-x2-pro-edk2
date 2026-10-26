from pathlib import Path
import json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;work=P/'bypass-iq-model';work.mkdir(exist_ok=True)
actual=(P/'camss-icp-a5-ipe.c.proposed').read_text().split('int camss_a5_ipe_encode_bypass_iq(',1)[1];actual='int camss_a5_ipe_encode_bypass_iq('+actual
prefix='''#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
typedef uint32_t u32;
#define CAMSS_A5_IPE_IQ_BYTES 2584
#define EXPORT_SYMBOL_GPL(x)
static void put_unaligned_le32(u32 v,void *p){memcpy(p,&v,4);}
'''
main='''
int main(void){unsigned char data[4160];
 for(unsigned n=0;n<2584;n++){memset(data,0xa5,sizeof(data));assert(camss_a5_ipe_encode_bypass_iq(data+32,n)==-EINVAL);for(unsigned i=0;i<sizeof(data);i++)assert(data[i]==0xa5);}
 assert(camss_a5_ipe_encode_bypass_iq(NULL,2584)==-EINVAL);
 for(unsigned n=2584;n<=4096;n+=1512){memset(data,0xa5,sizeof(data));assert(!camss_a5_ipe_encode_bypass_iq(data+32,n));for(unsigned i=0;i<sizeof(data);i++){unsigned p=i-32;unsigned expected=i<32||i>=32+2584?0xa5:p==52||p==68||p==244||p==260?1:0;assert(data[i]==expected);}}
 assert(fwrite(data+32,1,2584,stdout)==2584);return 0;}
'''
src=work/'probe.c';src.write_text(prefix+actual+main)
q=subprocess.run(['cc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(src),'-o',str(work/'probe')],capture_output=True);assert not q.returncode,q.stderr.decode()
q=subprocess.run([str(work/'probe')],capture_output=True);assert not q.returncode,q.stderr.decode();assert q.stdout==(P/'hal-default-ica-iq-private.bin').read_bytes()
report=dict(stage=382,actual_kernel_bypass_iq_encoder_body=True,byte_exact_target_hal_default_fragment_match=True,
 all_short_buffers_and_null_rejected_without_writes=True,oversized_buffer_tail_untouched=True,asan_ubsan=True,
 arbitrary_iq_modules_not_enabled=True,no_phone_operations=True,passed=True)
(HERE/'bypass-iq-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
