"""Run the actual QCA wrapper, pulse routine and H4 parser with thin host APIs."""
from pathlib import Path
import hashlib
import json
import subprocess

k = Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref = Path(__file__).resolve().parent
out = Path('/mnt/e/edk2-samurai-out/kernel185')
qca = (k / 'drivers/bluetooth/hci_qca.c').read_text()
h4 = (k / 'drivers/bluetooth/hci_h4.c').read_text()


def extract(source, signature):
    start = source.index(signature)
    pos = source.index('{', start)
    level = 1
    end = pos + 1
    while level:
        level += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


parser = extract(h4, 'struct sk_buff *h4_recv_buf(')
receive = extract(qca, 'static int qca_recv(struct hci_uart *hu,')
pulse = extract(qca, 'static int qca_send_power_pulse(')
prefix = r'''
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
typedef uint8_t u8;
typedef uint16_t u16;
typedef unsigned int uint;
typedef struct { int value; } atomic_t;
#define READ_ONCE(x) (x)
#define WRITE_ONCE(x,v) ((x)=(v))
#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))
#define min_t(t,a,b) ((t)(a)<(t)(b)?(t)(a):(t)(b))
#define IS_ERR(x) ((uintptr_t)(x)>=(uintptr_t)-4095)
#define PTR_ERR(x) ((int)(intptr_t)(x))
#define ERR_PTR(x) ((void *)(intptr_t)(x))
#define GFP_ATOMIC 0
#define HCI_UART_REGISTERED 1
#define QCA_POWER_PULSE 4
#define QCA_RX_POWER_OFF_PULSE 1
#define QCA_RX_POWER_ON_PULSE 2
#define QCA_WCN3990_POWERON_PULSE 0xfc
#define QCA_WCN3990_POWEROFF_PULSE 0xc0
#define CMD_TRANS_TIMEOUT 100
static int test_bit(int n, const unsigned long *p) { return !!(*p&(1UL<<n)); }
static void set_bit(int n,unsigned long *p) { *p|=1UL<<n; }
static void clear_bit(int n,unsigned long *p) { *p&=~(1UL<<n); }
static void atomic_add(int n,atomic_t *p) { p->value+=n; }
struct sk_buff { unsigned len,cap,expect; u8 type; u8 data[300]; };
struct hci_dev { int dummy; };
struct qca_data { struct sk_buff *rx_skb; unsigned long flags;
    unsigned rx_phase,requested_baudrate; atomic_t pulse_rx_nuls; };
struct hci_uart { void *priv; struct hci_dev *hdev; void *serdev;
    unsigned long flags; u8 alignment,padding; };
struct h4_recv_pkt { u8 type,hlen,loff,lsize; u16 maxlen;
    int (*recv)(struct hci_dev *,struct sk_buff *); };
static unsigned allocated,freed,frames,errors;
static int alloc_fail;
static unsigned frame_length;
static u8 frame_data[300];
static struct sk_buff *bt_skb_alloc(unsigned size,int flags) {
    (void)flags; if(alloc_fail)return NULL;
    struct sk_buff *p=calloc(1,sizeof(*p)); assert(p && size<=300);
    p->cap=size; allocated++; return p;
}
static void kfree_skb(struct sk_buff *p) { if(p){assert(!IS_ERR(p));freed++;free(p);} }
static void skb_put_data(struct sk_buff *p,const void *data,unsigned n) {
    assert(p->len+n<=p->cap); memcpy(p->data+p->len,data,n);p->len+=n;
}
static unsigned skb_tailroom(struct sk_buff *p) { return p->cap-p->len; }
#define hci_skb_pkt_type(p) ((p)->type)
#define hci_skb_expect(p) ((p)->expect)
static u16 get_unaligned_le16(const u8 *p) { return p[0]|((u16)p[1]<<8); }
static int event(struct hci_dev *d,struct sk_buff *p) {
    (void)d;frames++; frame_length=p->len;memcpy(frame_data,p->data,p->len);
    kfree_skb(p);return 0;
}
static const struct h4_recv_pkt qca_recv_pkts[]={
    {4,2,1,1,260,event},{2,4,2,2,260,event},{0xfc,0,0,0,0,event}
};
static void log_message(struct hci_dev *d,const char *fmt,...) {
    (void)d;char buffer[512];va_list ap;va_start(ap,fmt);
    vsnprintf(buffer,sizeof(buffer),fmt,ap);va_end(ap);
}
#define bt_dev_err(d,...) do { log_message(d,__VA_ARGS__);errors++; } while(0)
#define bt_dev_dbg(d,...) log_message(d,__VA_ARGS__)
static int qca_recv(struct hci_uart *,const void *,int);
static struct hci_uart *active;
static int write_ret,inject_write,inject_delay;
static unsigned flow_count,wait_count,on_sleeps,off_sleeps;
static bool flow_values[4];
static void serdev_device_write_flush(void *d) {
    (void)d; assert(test_bit(QCA_POWER_PULSE,&((struct qca_data *)active->priv)->flags));
}
static void hci_uart_set_flow_control(struct hci_uart *h,bool disabled) {
    assert(h==active && flow_count<4);flow_values[flow_count++]=disabled;
}
static int serdev_device_write_buf(void *d,const u8 *p,unsigned n) {
    (void)d; assert(n==1 && (*p==0xfc||*p==0xc0));
    if(inject_write) { u8 zero=0;assert(qca_recv(active,&zero,1)==1); }
    return write_ret;
}
static void serdev_device_wait_until_sent(void *d,int timeout) {
    (void)d;assert(timeout==100);wait_count++;
}
static void msleep(unsigned n) {
    assert(n==100);on_sleeps++;
    assert(test_bit(QCA_POWER_PULSE,&((struct qca_data *)active->priv)->flags));
    if(inject_delay){u8 z[2]={0,0};assert(qca_recv(active,z,2)==2);}
}
static void usleep_range(unsigned low,unsigned high) {
    assert(low==1000 && high==10000);off_sleeps++;
    assert(test_bit(QCA_POWER_PULSE,&((struct qca_data *)active->priv)->flags));
}
'''
tests = r'''
static unsigned cases;
static struct hci_dev dev;
static struct qca_data q;
static struct hci_uart hu;
static void reset(bool window) {
    if(q.rx_skb)kfree_skb(q.rx_skb);
    memset(&q,0,sizeof(q));memset(&hu,0,sizeof(hu));
    hu.priv=&q;hu.hdev=&dev;set_bit(HCI_UART_REGISTERED,&hu.flags);
    if(window)set_bit(QCA_POWER_PULSE,&q.flags);
    frames=errors=0;alloc_fail=0;active=&hu;
    write_ret=1;inject_write=inject_delay=0;
    flow_count=wait_count=on_sleeps=off_sleeps=0;
    memset(flow_values,0,sizeof(flow_values));cases++;
}
int main(void) {
    u8 zero=0,bad=0x99;
    u8 ok[]={4,0x0e,1,0};
    u8 pref[]={0,0,4,0x0e,1,0};
    reset(false);assert(qca_recv(&hu,&zero,1)==-EILSEQ && errors==1 && q.pulse_rx_nuls.value==0);
    reset(true);clear_bit(HCI_UART_REGISTERED,&hu.flags);assert(qca_recv(&hu,&zero,1)==-EUNATCH && q.pulse_rx_nuls.value==0);
    reset(true);assert(qca_recv(&hu,&zero,1)==1 && !q.rx_skb && !errors && q.pulse_rx_nuls.value==1);
    reset(true);assert(qca_recv(&hu,pref,sizeof(pref))==sizeof(pref) && frames==1 && q.pulse_rx_nuls.value==2 && frame_length==3 && frame_data[2]==0);
    reset(true);assert(qca_recv(&hu,ok,2)==2 && q.rx_skb);assert(qca_recv(&hu,ok+2,2)==2 && frames==1 && q.pulse_rx_nuls.value==0 && frame_data[2]==0);
    reset(true);assert(qca_recv(&hu,ok,3)==3 && q.rx_skb);assert(qca_recv(&hu,&zero,1)==1 && frames==1 && q.pulse_rx_nuls.value==0);
    reset(true);assert(qca_recv(&hu,&bad,1)==-EILSEQ && errors==1 && !q.rx_skb);
    reset(true);clear_bit(QCA_POWER_PULSE,&q.flags);assert(qca_recv(&hu,&zero,1)==-EILSEQ && errors==1);
    reset(true);alloc_fail=1;assert(qca_recv(&hu,pref,sizeof(pref))==-ENOMEM && errors==1 && q.pulse_rx_nuls.value==2);
    reset(true);hu.padding=2;assert(qca_recv(&hu,pref,sizeof(pref))==sizeof(pref) && frames==1 && q.pulse_rx_nuls.value==0);
    reset(true);assert(qca_recv(&hu,NULL,0)==0 && !q.rx_skb);
    u8 large[]={2,0,0,255,255};
    reset(true);assert(qca_recv(&hu,large,sizeof(large))==-EMSGSIZE && errors==1);
    reset(false);inject_write=inject_delay=1;
    assert(qca_send_power_pulse(&hu,true)==0 && flow_count==2 && flow_values[0] && !flow_values[1]);
    assert(q.pulse_rx_nuls.value==3 && wait_count==1 && on_sleeps==1 && !off_sleeps && !test_bit(QCA_POWER_PULSE,&q.flags));
    assert(qca_recv(&hu,&zero,1)==-EILSEQ);assert(qca_recv(&hu,ok,sizeof(ok))==sizeof(ok) && frames==1);
    reset(false);inject_write=1;assert(qca_send_power_pulse(&hu,false)==0 && q.pulse_rx_nuls.value==1 && wait_count==1 && off_sleeps==1 && !on_sleeps && !test_bit(QCA_POWER_PULSE,&q.flags));
    for(int ret=-8;ret<=2;ret++) {
        if(ret==1)continue;
        reset(false);write_ret=ret;
        assert(qca_send_power_pulse(&hu,true)==(ret<0?ret:-EIO));
        assert(flow_count==2 && flow_values[0] && !flow_values[1] && !wait_count && !on_sleeps && !off_sleeps && !test_bit(QCA_POWER_PULSE,&q.flags));
    }
    for(unsigned n=1;n<=1024;n++) {
        reset(true);unsigned zeros=n%7;unsigned bytes=4+zeros;
        u8 packet[12]={0};memcpy(packet+zeros,ok,4);packet[bytes-1]=(u8)n;
        assert(qca_recv(&hu,packet,(int)bytes)==(int)bytes && frames==1 && !errors && q.pulse_rx_nuls.value==(int)zeros && frame_data[2]==(u8)n);
    }
    reset(false);assert(allocated==freed);
    printf("PASS cases=%u allocations=%u frees=%u\n",cases,allocated,freed);
}
'''
source = prefix + parser + '\n' + receive + '\n' + pulse + '\n' + tests
file = out / 'qca-pulse-host-private.c'
file.write_text(source)
binary = out / 'qca-pulse-host-private.bin'
with (out / 'host-build-corrected-private.log').open('wb') as log:
    subprocess.run(['gcc', '-std=gnu11', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                    '-Wno-sign-compare', '-fsanitize=address,undefined', str(file), '-o', str(binary)],
                   stdout=log, stderr=subprocess.STDOUT, check=True)
result = subprocess.run([str(binary)], capture_output=True, check=True)
(out / 'host-runtime-private.log').write_bytes(result.stdout + result.stderr)
report = {'actual_qca_receive_and_power_pulse_extracted': True, 'actual_h4_parser_extracted': True,
          'asan_ubsan_passed': True, 'scenarios': result.stdout.decode().strip(),
          'source_sha256': hashlib.sha256(qca.encode()).hexdigest(),
          'h4_parser_source_sha256': hashlib.sha256(h4.encode()).hexdigest(),
          'partial_payload_padding_and_regular_mode_errors_preserved': True,
          'all_pulse_write_failures_restore_flow_and_flag': True, 'runtime_hardware_tested': False}
(ref / 'host-tests-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
