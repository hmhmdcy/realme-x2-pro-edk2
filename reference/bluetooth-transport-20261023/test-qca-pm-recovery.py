"""Actual QCA PM/IBS callbacks: verify forward progress after aborted suspend.

Kernel locks, timers, work delivery, SKBs and UART acceptance are modeled.
The serial clock vote and its two no-op helpers are the exact current source.
"""
from pathlib import Path
import difflib
import hashlib
import json
import subprocess
import sys

R = Path(__file__).resolve().parent
source = (R / 'source/hci_qca.c').read_text()


def extract(text, signature):
    start = text.index(signature)
    brace = text.index('{', start)
    level, end = 1, brace + 1
    while level:
        level += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end] + '\n'


baseline = extract(source, 'static int __maybe_unused qca_suspend(')
r1 = baseline.replace('''\t\tif (ret < 0) {
\t\t\tBT_ERR("Failed to send SLEEP to device");
\t\t\tbreak;
\t\t}''', '''\t\tif (ret != sizeof(cmd)) {
\t\t\tBT_ERR("Failed to send SLEEP to device");
\t\t\tif (ret >= 0)
\t\t\t\tret = -EIO;
\t\t\tbreak;
\t\t}''').replace('''\tif (ret == 0) {
\t\tret = -ETIMEDOUT;
\t\tgoto error;
\t}''', '''\tif (ret <= 0) {
\t\tif (!ret)
\t\t\tret = -ETIMEDOUT;
\t\tgoto error;
\t}''')
r1_source = source.replace(baseline, r1)
assert hashlib.sha256(r1_source.encode()).hexdigest() == '8f37fd639214e6c56f25ad4926579d4dd26aba8a228aac210a85adeebe2c242b'
r2 = r1.replace('\tbool tx_pending = false;', '\tbool tx_pending = false;\n\tbool ibs_quiesced = false;')
r2 = r2.replace('\tcancel_work_sync(&qca->ws_awake_rx);', '\tcancel_work_sync(&qca->ws_awake_rx);\n\tibs_quiesced = true;')
old_error = '''error:
\tclear_bit(QCA_SUSPENDING, &qca->flags);

\treturn ret;'''
new_error = '''error:
\tspin_lock_irqsave_nested(&qca->hci_ibs_lock,
\t\t\t\t flags, SINGLE_DEPTH_NESTING);
\tclear_bit(QCA_SUSPENDING, &qca->flags);

\t/* A failed suspend will not get a matching resume callback. Restore
\t * only IBS activity stopped above, using the current protocol state.
\t */
\tif (ibs_quiesced &&
\t    !test_bit(QCA_IBS_DISABLED, &qca->flags) &&
\t    !test_bit(QCA_SSR_TRIGGERED, &qca->flags) &&
\t    !test_bit(QCA_BT_OFF, &qca->flags)) {
\t\tswitch (qca->tx_ibs_state) {
\t\tcase HCI_IBS_TX_ASLEEP:
\t\t\tif (skb_queue_empty(&qca->tx_wait_q))
\t\t\t\tbreak;
\t\t\tqca->tx_ibs_state = HCI_IBS_TX_WAKING;
\t\t\tfallthrough;
\t\tcase HCI_IBS_TX_WAKING:
\t\t\tserial_clock_vote(HCI_IBS_TX_VOTE_CLOCK_ON, hu);
\t\t\tmod_timer(&qca->wake_retrans_timer, jiffies +
\t\t\t\t  msecs_to_jiffies(qca->wake_retrans));
\t\t\tbreak;
\t\tcase HCI_IBS_TX_AWAKE:
\t\t\tmod_timer(&qca->tx_idle_timer, jiffies +
\t\t\t\t  msecs_to_jiffies(qca->tx_idle_delay));
\t\t\tbreak;
\t\tdefault:
\t\t\tbreak;
\t\t}
\t}
\tspin_unlock_irqrestore(&qca->hci_ibs_lock, flags);

\treturn ret;'''
assert r2.count(old_error) == 1
r2 = r2.replace(old_error, new_error)
r2_source = source.replace(baseline, r2)
patches = {
    'qca-suspend-recovery-r2.patch': (source, r2_source),
    'qca-suspend-recovery-r1-to-r2.patch': (r1_source, r2_source),
}
for name, (old, new) in patches.items():
    (R / name).write_text(''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
        fromfile='a/drivers/bluetooth/hci_qca.c', tofile='b/drivers/bluetooth/hci_qca.c')))

prefix = r'''
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define __maybe_unused
typedef uint8_t u8;typedef uint64_t u64;
enum {QCA_SUSPENDING,QCA_ROM_FW,QCA_BT_OFF,QCA_SSR_TRIGGERED,QCA_IBS_DISABLED};
enum {HCI_IBS_TX_WAKING,HCI_IBS_TX_AWAKE,HCI_IBS_TX_ASLEEP};
enum {HCI_IBS_RX_ASLEEP,HCI_IBS_RX_AWAKE};
enum {HCI_IBS_VOTE_STATS_UPDATE,HCI_IBS_TX_VOTE_CLOCK_ON,HCI_IBS_TX_VOTE_CLOCK_OFF,HCI_IBS_RX_VOTE_CLOCK_ON,HCI_IBS_RX_VOTE_CLOCK_OFF};
#define HCI_IBS_SLEEP_IND 0xfe
#define HCI_IBS_WAKE_IND 0xfd
#define HCI_IBS_WAKE_ACK 0xfc
#define IBS_DISABLE_SSR_TIMEOUT 10
#define FW_DOWNLOAD_TIMEOUT 20
#define IBS_BTSOC_TX_IDLE_TIMEOUT 30
#define CMD_TRANS_TIMEOUT 40
#define TASK_UNINTERRUPTIBLE 0
#define SINGLE_DEPTH_NESTING 1
#define GFP_ATOMIC 0
#define BT_DBG(...) ((void)0)
#define BT_ERR(...) ((void)0)
#define bt_dev_err(...) ((void)0)
#define bt_dev_dbg(...) ((void)0)
#define fallthrough __attribute__((fallthrough))
struct sk_buff {struct sk_buff *next;unsigned len,start;u8 type,data[20];bool data_frame;};
struct sk_buff_head {struct sk_buff *head,*tail;unsigned count;};
struct timer_list {bool pending;unsigned long expires;};
struct work_struct {bool pending;};
struct tty_struct {int unused;};
struct hci_uart;
struct qca_data {
 unsigned long flags;int hci_ibs_lock,suspend_wait_q;void *workqueue;
 struct work_struct ws_awake_device,ws_awake_rx,ws_tx_vote_off,ws_rx_vote_off;
 struct timer_list wake_retrans_timer,tx_idle_timer;
 unsigned wake_retrans,tx_idle_delay,tx_ibs_state,rx_ibs_state;
 u64 ibs_sent_slps,ibs_sent_wakes,ibs_sent_wacks,ibs_recv_wakes,ibs_recv_slps,ibs_recv_wacks;
 bool tx_vote,rx_vote;u64 tx_votes_on,tx_votes_off,rx_votes_on,rx_votes_off;
 unsigned long vote_last_jif;u64 vote_off_ms,vote_on_ms,votes_on,votes_off;
 struct hci_uart *hu;struct sk_buff_head txq,tx_wait_q;
};
struct hci_uart {struct qca_data *priv;void *hdev;void *serdev;struct tty_struct *tty;};
struct qca_serdev {struct hci_uart serdev_hu;};
struct serdev_device {struct qca_serdev *data;};
struct device {struct serdev_device *sd;};
static struct serdev_device *to_serdev_device(struct device *d){return d->sd;}
static struct qca_serdev *serdev_device_get_drvdata(struct serdev_device *s){return s->data;}
static bool test_bit(unsigned n,const unsigned long *p){return !!(*p&(1UL<<n));}
static void set_bit(unsigned n,unsigned long *p){*p|=1UL<<n;}
static void clear_bit(unsigned n,unsigned long *p){*p&=~(1UL<<n);}
static unsigned long jiffies=100;
static unsigned long msecs_to_jiffies(unsigned long n){return n;}
static unsigned int jiffies_to_msecs(unsigned long n){return n;}
static unsigned depth,irq_disabled;static int after_unlock_event;
static struct qca_data q;static struct qca_serdev qs;static struct serdev_device sd;static struct device dev;
static void device_woke_up(struct hci_uart *);
static void device_want_to_sleep(struct hci_uart *);
static void take_lock(unsigned long *f){assert(!depth&&!irq_disabled);*f=irq_disabled;depth=irq_disabled=1;}
static void drop_lock(unsigned long f){
 assert(depth==1&&irq_disabled);depth=0;irq_disabled=f;
 int event=after_unlock_event;after_unlock_event=0;
 if(event==1)device_woke_up(q.hu);
 if(event==2)device_want_to_sleep(q.hu);
 if(event==3)set_bit(QCA_SSR_TRIGGERED,&q.flags);
}
#define spin_lock_irqsave_nested(p,f,n) do{(void)(p);(void)(n);take_lock(&(f));}while(0)
#define spin_lock_irqsave(p,f) do{(void)(p);take_lock(&(f));}while(0)
#define spin_unlock_irqrestore(p,f) do{(void)(p);drop_lock(f);}while(0)
#define container_of(p,t,m) ((t *)((unsigned char *)(p)-offsetof(t,m)))
#define timer_container_of(var,t,m) container_of(t,struct qca_data,m)
#define hci_skb_pkt_type(s) ((s)->type)
static unsigned allocated,freed,tx_frames,tx_wakes,tx_sleeps,tx_acks;
static struct sk_buff *bt_skb_alloc(unsigned n,int f){(void)f;assert(n<16);struct sk_buff *s=calloc(1,sizeof(*s));assert(s);s->start=1;allocated++;return s;}
static void kfree_skb(struct sk_buff *s){assert(s);freed++;free(s);}
#define dev_kfree_skb_irq kfree_skb
static u8 *skb_push(struct sk_buff *s,unsigned n){assert(n<=s->start);s->start-=n;s->len+=n;return s->data+s->start;}
static void skb_put_u8(struct sk_buff *s,u8 n){assert(s->start+s->len<20);s->data[s->start+s->len++]=n;}
static void skb_queue_tail(struct sk_buff_head *h,struct sk_buff *s){assert(!s->next);if(h->tail)h->tail->next=s;else h->head=s;h->tail=s;h->count++;}
static struct sk_buff *skb_dequeue(struct sk_buff_head *h){struct sk_buff *s=h->head;if(!s)return NULL;h->head=s->next;if(!h->head)h->tail=NULL;s->next=NULL;h->count--;return s;}
static bool skb_queue_empty(struct sk_buff_head *h){return !h->head;}
static void timer_delete(struct timer_list *t){assert(depth&&irq_disabled);t->pending=false;}
static void mod_timer(struct timer_list *t,unsigned long e){assert(depth&&irq_disabled);t->pending=true;t->expires=e;}
static bool queue_work(void *queue,struct work_struct *w){(void)queue;assert(depth&&irq_disabled);bool was=w->pending;w->pending=true;return !was;}
static bool cancel_work_sync(struct work_struct *w){assert(!depth&&!irq_disabled);bool was=w->pending;w->pending=false;return was;}
static void wake_up_interruptible(int *w){(void)w;assert(depth&&irq_disabled);}
static void hci_uart_tx_wakeup(struct hci_uart *hu){
 assert(!depth&&!irq_disabled);struct sk_buff *s;
 while((s=skb_dequeue(&hu->priv->txq))){
  if(s->data_frame)tx_frames++;
  else if(s->data[s->start]==HCI_IBS_WAKE_IND)tx_wakes++;
  else if(s->data[s->start]==HCI_IBS_SLEEP_IND)tx_sleeps++;
  else if(s->data[s->start]==HCI_IBS_WAKE_ACK)tx_acks++;
  else assert(false);
  kfree_skb(s);
 }
}
static int write_result,wait_result;static unsigned writes,waitsent;static bool clear_disable;
static void wait_on_bit_timeout(unsigned long *p,unsigned n,int state,unsigned long t){(void)state;assert(!depth&&!irq_disabled);assert(t==10||t==20);if(clear_disable)clear_bit(n,p);}
static void serdev_device_write_flush(void *p){(void)p;assert(depth&&irq_disabled);}
static int serdev_device_write_buf(void *p,const u8 *b,unsigned n){(void)p;assert(depth&&irq_disabled&&n==1&&*b==0xfe);writes++;return write_result;}
static void serdev_device_wait_until_sent(void *p,unsigned n){(void)p;assert(!depth&&!irq_disabled&&n==40);waitsent++;}
static int fake_wait(int *p,bool cond,unsigned t){(void)p;(void)cond;assert(!depth&&!irq_disabled&&t==30);return wait_result;}
#define wait_event_interruptible_timeout(q,cond,t) fake_wait(&(q),(cond),(t))
'''
common_signatures = [
    'static void __serial_clock_on(', 'static void __serial_clock_off(',
    'static void serial_clock_vote(', 'static int send_hci_ibs_cmd(',
    'static void hci_ibs_tx_idle_timeout(', 'static void hci_ibs_wake_retrans_timeout(',
    'static void device_want_to_wakeup(', 'static void device_want_to_sleep(',
    'static void device_woke_up(', 'static int qca_enqueue(',
]
callbacks = ''.join(extract(source, s) for s in common_signatures)
resume = extract(source, 'static int __maybe_unused qca_resume(')

tests = r'''
static unsigned cases,progress_failures,idle_failures,ack_failures,asleep_failures,ssr_failures;
static void drain(struct sk_buff_head *h){struct sk_buff *s;while((s=skb_dequeue(h)))kfree_skb(s);}
static void reset(unsigned state){
 assert(!depth&&!irq_disabled);drain(&q.txq);drain(&q.tx_wait_q);memset(&q,0,sizeof(q));memset(&qs,0,sizeof(qs));
 qs.serdev_hu.priv=&q;qs.serdev_hu.serdev=&sd;sd.data=&qs;dev.sd=&sd;q.hu=&qs.serdev_hu;
 q.tx_ibs_state=state;q.rx_ibs_state=HCI_IBS_RX_ASLEEP;q.wake_retrans=5;q.tx_idle_delay=20;
 q.tx_vote=state==HCI_IBS_TX_AWAKE;q.tx_idle_timer.pending=state==HCI_IBS_TX_AWAKE;
 q.wake_retrans_timer.pending=state==HCI_IBS_TX_WAKING;q.ws_awake_device.pending=state==HCI_IBS_TX_WAKING;
 write_result=1;wait_result=1;clear_disable=false;after_unlock_event=0;
 writes=waitsent=tx_frames=tx_wakes=tx_sleeps=tx_acks=0;cases++;
}
static void enqueue_frame(void){struct sk_buff *s=bt_skb_alloc(2,0);s->data_frame=true;s->type=2;skb_put_u8(s,0x55);assert(!qca_enqueue(q.hu,s));}
static void retransmit(void){if(q.wake_retrans_timer.pending){q.wake_retrans_timer.pending=false;hci_ibs_wake_retrans_timeout(&q.wake_retrans_timer);}}
static void idle(void){if(q.tx_idle_timer.pending){q.tx_idle_timer.pending=false;hci_ibs_tx_idle_timeout(&q.tx_idle_timer);}}
static void wake_ack(void){device_woke_up(q.hu);}
int main(void){
 // Pending wake work can be cancelled before it has voted the UART on.
 for(int result=-5;result<=2;result++){
  if(result==1)continue;
  reset(HCI_IBS_TX_WAKING);enqueue_frame();assert(q.tx_wait_q.count==1);write_result=result;
  int ret=qca_suspend(&dev);assert(ret==(result<0?result:-EIO));assert(!test_bit(QCA_SUSPENDING,&q.flags));
  bool armed=q.wake_retrans_timer.pending&&q.tx_vote;
  retransmit();bool sent=tx_wakes==1;wake_ack();
  if(!armed||!sent||tx_frames!=1||!skb_queue_empty(&q.tx_wait_q)||q.tx_ibs_state!=HCI_IBS_TX_AWAKE||q.wake_retrans_timer.pending)progress_failures++;
 }
 for(int result=-1;result<=0;result++){
  reset(HCI_IBS_TX_AWAKE);write_result=result;assert(qca_suspend(&dev)==(result?result:-EIO));
  bool armed=q.tx_idle_timer.pending;idle();
  if(!armed||q.tx_ibs_state!=HCI_IBS_TX_ASLEEP||!q.ws_tx_vote_off.pending)idle_failures++;
 }
 // ACK while SUSPENDING is explicitly ignored. Recovery must cause a new WAKE.
 reset(HCI_IBS_TX_WAKING);enqueue_frame();write_result=0;after_unlock_event=1;
 assert(qca_suspend(&dev)==-EIO);assert(q.ibs_recv_wacks==1&&q.tx_ibs_state==HCI_IBS_TX_WAKING);
 retransmit();wake_ack();if(tx_wakes!=1||tx_frames!=1||q.wake_retrans_timer.pending)ack_failures++;
 // ACK delivered after error recovery wins the same lock and removes the timer.
 reset(HCI_IBS_TX_WAKING);enqueue_frame();write_result=-EIO;assert(qca_suspend(&dev)==-EIO);
 wake_ack();unsigned wakes=tx_wakes;retransmit();if(tx_frames!=1||tx_wakes!=wakes||q.wake_retrans_timer.pending)ack_failures++;
 // Accepted SLEEP is preserved. Queued frames require a fresh wake, not a fabricated ACK.
 for(int wait=-512;wait<=0;wait+=512){
  reset(HCI_IBS_TX_WAKING);enqueue_frame();wait_result=wait;
  assert(qca_suspend(&dev)==(wait?wait:-ETIMEDOUT));
  bool waking=q.tx_ibs_state==HCI_IBS_TX_WAKING&&q.wake_retrans_timer.pending&&q.tx_vote;
  retransmit();wake_ack();if(!waking||tx_wakes!=1||tx_frames!=1)asleep_failures++;
  reset(HCI_IBS_TX_ASLEEP);wait_result=wait;assert(qca_suspend(&dev)==(wait?wait:-ETIMEDOUT));
  if(q.tx_ibs_state!=HCI_IBS_TX_ASLEEP||q.wake_retrans_timer.pending||q.tx_idle_timer.pending||q.tx_vote)asleep_failures++;
 }
 // RX SLEEP may arrive during the failed suspend; retain it and accept later WAKE.
 reset(HCI_IBS_TX_WAKING);enqueue_frame();q.rx_ibs_state=HCI_IBS_RX_AWAKE;write_result=0;after_unlock_event=2;
 assert(qca_suspend(&dev)==-EIO);assert(q.rx_ibs_state==HCI_IBS_RX_ASLEEP&&q.ibs_recv_slps==1);
 device_want_to_wakeup(q.hu);assert(q.ws_awake_rx.pending);
 retransmit();wake_ack();if(tx_frames!=1||tx_wakes!=1)progress_failures++;
 // A concurrent SSR must not be given a retransmit timer or a new clock vote.
 reset(HCI_IBS_TX_WAKING);write_result=0;after_unlock_event=3;assert(qca_suspend(&dev)==-EIO);
 if(q.wake_retrans_timer.pending||q.tx_vote)ssr_failures++;
 // Early FW timeout did not cancel either mechanism: do not manufacture recovery.
 reset(HCI_IBS_TX_WAKING);set_bit(QCA_IBS_DISABLED,&q.flags);
 assert(qca_suspend(&dev)==-ETIMEDOUT);assert(q.ws_awake_device.pending&&q.wake_retrans_timer.pending&&!q.tx_vote);
 // The successful path retains its original asleep state and resume semantics.
 reset(HCI_IBS_TX_AWAKE);assert(!qca_suspend(&dev));assert(q.tx_ibs_state==HCI_IBS_TX_ASLEEP);
 assert(!qca_resume(&dev));assert(!test_bit(QCA_SUSPENDING,&q.flags));enqueue_frame();assert(q.ws_awake_device.pending);
 drain(&q.txq);drain(&q.tx_wait_q);assert(allocated==freed);
 printf("{\"scenarios\":%u,\"waking_progress_failures\":%u,\"awake_idle_failures\":%u,\"async_ack_failures\":%u,\"accepted_sleep_failures\":%u,\"ssr_exclusion_failures\":%u,\"allocation_leaks\":%u}\n",cases,progress_failures,idle_failures,ack_failures,asleep_failures,ssr_failures,allocated-freed);
 return 0;
}
'''
out = Path('/mnt/e/edk2-samurai-out/bluetooth-transport-20261023/test-output')
out.mkdir(parents=True, exist_ok=True)
r2_file = out.parent / 'hci_qca-pm-r2.c'
r2_file.write_text(r2_source)
results = {}
for name, body in {'pm_recovery_r1': r1, 'pm_recovery_r2': r2}.items():
    c = out / (name + '.c')
    c.write_text(prefix + callbacks + body + resume + tests)
    binary = out / name
    cp = subprocess.run(['gcc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter',
        '-O1', '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', str(c), '-o', str(binary)], capture_output=True)
    (out / (name + '-build.log')).write_bytes(cp.stdout + cp.stderr)
    assert cp.returncode == 0, cp.stderr.decode()
    run = subprocess.run([str(binary)], capture_output=True)
    (out / (name + '-run.log')).write_bytes(run.stdout + run.stderr)
    assert run.returncode == 0 and not run.stderr, (run.stdout, run.stderr)
    results[name] = json.loads(run.stdout)
assert results['pm_recovery_r1']['waking_progress_failures'] > 0
for key, value in results['pm_recovery_r2'].items():
    if key != 'scenarios':
        assert value == 0, (key, value)
cp = subprocess.run([sys.executable, str(R / 'test-qca-suspend-contract.py'), '--r2', str(r2_file)],
                    capture_output=True)
(out / 'r2-return-contract.log').write_bytes(cp.stdout + cp.stderr)
assert cp.returncode == 0, cp.stderr.decode()
return_contract = json.loads((R / 'qca-suspend-contract-validation.json').read_text())
assert return_contract['results']['qca_suspend_r2']['contract_mismatches'] == 0
report = dict(results=results, asan_ubsan_passed=True,
    actual_suspend_resume_enqueue_timeout_ack_rx_and_clock_vote_extracted=True,
    r2_return_value_regression=return_contract['results']['qca_suspend_r2'],
    clocks_have_noop_helpers_in_this_fixed_source=True,
    kernel_apis_timers_irq_and_uart_delivery_modeled=True,
    handset_or_shared_source_not_changed=True, installed_or_loaded=False,
    source_qca_sha256=hashlib.sha256(source.encode()).hexdigest(),
    r2_source_sha256=hashlib.sha256(r2_source.encode()).hexdigest(),
    r2_patch_sha256=hashlib.sha256((R / 'qca-suspend-recovery-r2.patch').read_bytes()).hexdigest(),
    r1_to_r2_patch_sha256=hashlib.sha256((R / 'qca-suspend-recovery-r1-to-r2.patch').read_bytes()).hexdigest())
(R / 'qca-pm-recovery-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
