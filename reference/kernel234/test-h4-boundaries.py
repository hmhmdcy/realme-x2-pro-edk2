"""Replay the unchanged real H4 parser, including the ambiguous len-zero case."""
from pathlib import Path
import hashlib
import json
import subprocess

R = Path(__file__).resolve().parent
P = Path('/mnt/e/edk2-samurai-out/kernel234')
source = (P / 'hci_h4.c').read_text()
assert hashlib.sha256(source.encode()).hexdigest() == '841d77149606f61f36e6a9f1acf9035ec8c4add724da2878e48a417ff37374a2'
body = source[source.index('struct sk_buff *h4_recv_buf'):source.index('EXPORT_SYMBOL_GPL(h4_recv_buf);')]
header = (P / 'hci_uart.h').read_text()
define = header[header.index('#define H4_RECV_EVENT'):header.index('#define H4_RECV_ISO')]
prefix = r'''
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef uint8_t u8; typedef uint16_t u16; typedef unsigned int uint;
#define HCI_EVENT_PKT 4
#define HCI_EVENT_HDR_SIZE 2
#define HCI_MAX_EVENT_SIZE 260
#define GFP_ATOMIC 0
#define ERR_PTR(e) ((struct sk_buff *)(intptr_t)(e))
#define IS_ERR(p) ((uintptr_t)(p)>=(uintptr_t)-4095)
#define min_t(t,a,b) ((t)(a)<(t)(b)?(t)(a):(t)(b))
#define hci_skb_pkt_type(s) ((s)->type)
#define hci_skb_expect(s) ((s)->expect)
struct sk_buff { u8 data[260]; unsigned int len, capacity, type, expect; };
struct hci_dev { unsigned int completed; };
struct hci_uart { unsigned int alignment,padding; struct hci_dev *hdev; };
struct h4_recv_pkt { unsigned int type,hlen,loff,lsize,maxlen; int (*recv)(struct hci_dev *,struct sk_buff *); };
static unsigned int allocations;
static struct sk_buff *bt_skb_alloc(unsigned int capacity,int flags) { (void)flags; struct sk_buff *s=calloc(1,sizeof(*s)); assert(s); s->capacity=capacity; allocations++; return s; }
static void kfree_skb(struct sk_buff *s) { if(s){assert(allocations);allocations--;free(s);} }
static void skb_put_data(struct sk_buff *s,const void *p,unsigned int n) { assert(s->len+n<=s->capacity); memcpy(s->data+s->len,p,n);s->len+=n; }
static unsigned int skb_tailroom(struct sk_buff *s) { return s->capacity-s->len; }
static unsigned int get_unaligned_le16(const void *p) { const u8 *b=p; return b[0]|((unsigned int)b[1]<<8); }
static int receive(struct hci_dev *d,struct sk_buff *s) { d->completed++; kfree_skb(s);return 0; }
'''
main = r'''
int main(void) {
 const struct h4_recv_pkt table[]={{H4_RECV_EVENT,.recv=receive}};
 unsigned int cases=0;
 struct hci_dev d={0};struct hci_uart hu={.hdev=&d};struct sk_buff *s=NULL;
 const u8 type[]={4}, vendor[]={0xff,1,0}, packet[]={4,0xff,1,0};
 s=h4_recv_buf(&hu,s,type,1,table,1);
 assert(s&&!IS_ERR(s)&&s->len==0&&s->type==4&&s->expect==2);cases++;
 s=h4_recv_buf(&hu,s,vendor,3,table,1);
 assert(!s&&d.completed==1&&!allocations);cases++;
 s=h4_recv_buf(&hu,NULL,vendor,3,table,1);
 assert(IS_ERR(s)&&(intptr_t)s==-EILSEQ&&!allocations);cases++;
 for(unsigned int cut=1;cut<sizeof(packet);cut++){
  d.completed=0;hu.padding=0;
  s=h4_recv_buf(&hu,NULL,packet,(int)cut,table,1);assert(!IS_ERR(s));
  s=h4_recv_buf(&hu,s,packet+cut,(int)(sizeof(packet)-cut),table,1);
  assert(!s&&d.completed==1&&!allocations);cases++;
 }
 /* A chunk can begin with a valid H4 packet and fail at a later byte. */
 const u8 extra[]={4,0xff,1,0,0xff};d.completed=0;
 s=h4_recv_buf(&hu,NULL,extra,sizeof(extra),table,1);
 assert(IS_ERR(s)&&(intptr_t)s==-EILSEQ&&d.completed==1&&!allocations);cases++;
 /* Alignment padding consumes a byte; it is not another packet type. */
 const u8 padded[]={4,0x0e,0,0xff};hu.alignment=4;d.completed=0;
 s=h4_recv_buf(&hu,NULL,padded,sizeof(padded),table,1);
 assert(!s&&hu.padding==0&&d.completed==1&&!allocations);cases++;
 printf("{\"cases\":%u,\"all_passed\":true,\"allocations_remaining\":%u}\n",cases,allocations);
 return 0;
}
'''
out = P / 'h4-boundaries'
out.mkdir(mode=0o700)
c = out / 'replay.c'
c.write_text(prefix + define + body + main)
binary = out / 'replay'
compile = subprocess.run(['gcc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-g', '-O1',
                          '-fsanitize=address,undefined', '-fno-omit-frame-pointer', str(c), '-o', str(binary)],
                         capture_output=True)
(out / 'compile-private.log').write_bytes(compile.stdout + compile.stderr)
assert compile.returncode == 0
run = subprocess.run([str(binary)], capture_output=True)
(out / 'run-private.log').write_bytes(run.stdout + run.stderr)
assert run.returncode == 0 and not run.stderr
result = json.loads(run.stdout)
assert result['cases'] == 8 and result['all_passed'] and result['allocations_remaining'] == 0
result.update(stage=234, actual_h4_function_extracted=True, asan_ubsan_passed=True,
              partial_zero_does_not_imply_no_skb=True, chunk_head_not_error_offset=True,
              no_product_or_phone_change=True)
(R / 'h4-boundaries-validation.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
