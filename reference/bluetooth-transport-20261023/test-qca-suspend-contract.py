"""Fault-inject the extracted live-baseline QCA suspend/resume functions.

This checks serial return-value and lifecycle contracts, not handset PM timing.
"""
from pathlib import Path
import difflib
import hashlib
import json
import subprocess
import sys

R = Path(__file__).resolve().parent
source = (R / 'source/hci_qca.c').read_text()


def function(signature):
    start = source.index(signature)
    brace = source.index('{', start)
    level, end = 1, brace + 1
    while level:
        level += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end] + '\n'


suspend = function('static int __maybe_unused qca_suspend(')
resume = function('static int __maybe_unused qca_resume(')
old_write = '''\t\tif (ret < 0) {
\t\t\tBT_ERR("Failed to send SLEEP to device");
\t\t\tbreak;
\t\t}'''
new_write = '''\t\tif (ret != sizeof(cmd)) {
\t\t\tBT_ERR("Failed to send SLEEP to device");
\t\t\tif (ret >= 0)
\t\t\t\tret = -EIO;
\t\t\tbreak;
\t\t}'''
old_wait = '''\tif (ret == 0) {
\t\tret = -ETIMEDOUT;
\t\tgoto error;
\t}'''
new_wait = '''\tif (ret <= 0) {
\t\tif (!ret)
\t\t\tret = -ETIMEDOUT;
\t\tgoto error;
\t}'''
assert suspend.count(old_write) == 1 and suspend.count(old_wait) == 1
candidate = suspend.replace(old_write, new_write).replace(old_wait, new_wait)
patched = source.replace(suspend, candidate)
patch = ''.join(difflib.unified_diff(source.splitlines(True), patched.splitlines(True),
    fromfile='a/drivers/bluetooth/hci_qca.c', tofile='b/drivers/bluetooth/hci_qca.c'))
(R / 'qca-suspend-return-contract-candidate.patch').write_text(patch)

prefix = r'''
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define __maybe_unused
typedef uint8_t u8;
enum {QCA_SUSPENDING,QCA_ROM_FW,QCA_BT_OFF,QCA_SSR_TRIGGERED,QCA_IBS_DISABLED};
enum {HCI_IBS_TX_WAKING,HCI_IBS_TX_AWAKE,HCI_IBS_TX_ASLEEP};
enum {HCI_IBS_RX_ASLEEP=2,HCI_IBS_TX_VOTE_CLOCK_OFF=0,HCI_IBS_TX_VOTE_CLOCK_ON=1};
#define HCI_IBS_SLEEP_IND 0xfe
#define IBS_DISABLE_SSR_TIMEOUT 10
#define FW_DOWNLOAD_TIMEOUT 20
#define IBS_BTSOC_TX_IDLE_TIMEOUT 30
#define CMD_TRANS_TIMEOUT 40
#define TASK_UNINTERRUPTIBLE 0
#define SINGLE_DEPTH_NESTING 1
#define BT_ERR(...) ((void)0)
#define bt_dev_err(...) ((void)0)
#define fallthrough __attribute__((fallthrough))
struct qca_data {
 unsigned long flags;int hci_ibs_lock,ws_awake_device,ws_awake_rx;
 int wake_retrans_timer,tx_idle_timer,suspend_wait_q;
 unsigned tx_ibs_state,rx_ibs_state,ibs_sent_slps,tx_wait_q,wake_retrans,tx_idle_delay;
};
struct hci_uart {struct qca_data *priv;void *hdev;void *serdev;};
struct qca_serdev {struct hci_uart serdev_hu;};
struct serdev_device {struct qca_serdev *data;};
struct device {struct serdev_device *sd;};
static struct serdev_device *to_serdev_device(struct device *d){return d->sd;}
static struct qca_serdev *serdev_device_get_drvdata(struct serdev_device *s){return s->data;}
static bool test_bit(unsigned n,const unsigned long *p){return !!(*p&(1UL<<n));}
static void set_bit(unsigned n,unsigned long *p){*p|=1UL<<n;}
static void clear_bit(unsigned n,unsigned long *p){*p&=~(1UL<<n);}
static unsigned depth,irq_disabled;
static void take_lock(unsigned long *f){assert(!depth&&!irq_disabled);*f=irq_disabled;depth=irq_disabled=1;}
static void drop_lock(unsigned long f){assert(depth==1&&irq_disabled);depth=0;irq_disabled=f;}
#define spin_lock_irqsave_nested(p,f,n) do{(void)(p);(void)(n);take_lock(&(f));}while(0)
#define spin_unlock_irqrestore(p,f) do{(void)(p);drop_lock(f);}while(0)
static unsigned flushes,writes,waitsent,clockoff,cancels,irq_waits;
static int write_result,wait_result;static bool clear_disable;
static void wait_on_bit_timeout(unsigned long *p,unsigned n,int state,unsigned long t){
 (void)state;assert(!depth&&!irq_disabled);assert(t==10||t==20);if(clear_disable)clear_bit(n,p);
}
static void cancel_work_sync(int *p){(void)p;assert(!depth&&!irq_disabled);cancels++;}
static void timer_delete(int *p){assert(depth&&irq_disabled);*p=0;}
static void serdev_device_write_flush(void *p){(void)p;assert(depth&&irq_disabled);flushes++;}
static int serdev_device_write_buf(void *p,const u8 *b,unsigned n){
 (void)p;assert(depth&&irq_disabled&&n==1&&*b==0xfe);writes++;return write_result;
}
static void serdev_device_wait_until_sent(void *p,unsigned n){(void)p;assert(!depth&&!irq_disabled&&n==40);waitsent++;}
static void serial_clock_vote(int state,struct hci_uart *p){(void)p;assert(state==0||state==1);if(!state)clockoff++;}
static unsigned long jiffies __attribute__((unused))=100;
static inline unsigned long msecs_to_jiffies(unsigned long t){return t;}
static inline void mod_timer(int *p,unsigned long t){(void)t;assert(depth&&irq_disabled);*p=1;}
static inline bool skb_queue_empty(unsigned *p){return !*p;}
static int fake_wait(int *p,bool cond,unsigned t){(void)p;(void)cond;assert(!depth&&!irq_disabled&&t==30);irq_waits++;return wait_result;}
#define wait_event_interruptible_timeout(q,cond,t) fake_wait(&(q),(cond),(t))
'''
tests = r'''
static unsigned cases,mismatches,zero_or_short_writes,negative_waits;
static struct qca_data q;static struct qca_serdev qs;static struct serdev_device sd;static struct device dev;
static void reset(unsigned tx){
 assert(!depth&&!irq_disabled);memset(&q,0,sizeof(q));memset(&qs,0,sizeof(qs));
 qs.serdev_hu.priv=&q;qs.serdev_hu.serdev=&sd;sd.data=&qs;dev.sd=&sd;
 q.tx_ibs_state=tx;q.rx_ibs_state=HCI_IBS_RX_ASLEEP;q.wake_retrans_timer=q.tx_idle_timer=1;
 flushes=writes=waitsent=clockoff=cancels=irq_waits=0;write_result=1;wait_result=1;clear_disable=false;
}
static void expect(int ret,int expected){if(ret!=expected)mismatches++;cases++;assert(!depth&&!irq_disabled);}
int main(void){
 for(unsigned state=HCI_IBS_TX_WAKING;state<=HCI_IBS_TX_ASLEEP;state++){
  reset(state);expect(qca_suspend(&dev),0);assert(test_bit(QCA_SUSPENDING,&q.flags));
  assert(q.tx_ibs_state==HCI_IBS_TX_ASLEEP);assert(writes==(state!=HCI_IBS_TX_ASLEEP));
  assert(q.ibs_sent_slps==writes&&waitsent==writes&&clockoff==writes);assert(irq_waits==1&&cancels==2);
  expect(qca_resume(&dev),0);assert(!test_bit(QCA_SUSPENDING,&q.flags));
 }
 // Every serial return other than one means the SLEEP byte was not accepted.
 for(int result=-5;result<=2;result++){
  if(result==1)continue;
  reset(HCI_IBS_TX_AWAKE);write_result=result;expect(qca_suspend(&dev),result<0?result:-EIO);
  if(q.tx_ibs_state!=HCI_IBS_TX_AWAKE||q.ibs_sent_slps||waitsent||clockoff||irq_waits||test_bit(QCA_SUSPENDING,&q.flags)){
   mismatches++;if(result>=0)zero_or_short_writes++;
  }
 }
 const int wait_results[]={-512,-5,-4,-3,-2,-1,0}; // -ERESTARTSYS is the kernel's signal result.
 for(unsigned i=0;i<sizeof(wait_results)/sizeof(wait_results[0]);i++){
  int result=wait_results[i];
  reset(HCI_IBS_TX_ASLEEP);wait_result=result;expect(qca_suspend(&dev),result?result:-ETIMEDOUT);
  if(test_bit(QCA_SUSPENDING,&q.flags)){mismatches++;if(result<0)negative_waits++;}
 }
 reset(99);expect(qca_suspend(&dev),-EINVAL);assert(!test_bit(QCA_SUSPENDING,&q.flags));
 for(unsigned flag=QCA_ROM_FW;flag<=QCA_BT_OFF;flag++){
  reset(HCI_IBS_TX_AWAKE);set_bit(flag,&q.flags);expect(qca_suspend(&dev),0);
  assert(!writes&&!cancels&&!irq_waits);expect(qca_resume(&dev),0);assert(!test_bit(QCA_SUSPENDING,&q.flags));
 }
 for(unsigned ssr=0;ssr<2;ssr++)for(unsigned completes=0;completes<2;completes++){
  reset(HCI_IBS_TX_AWAKE);set_bit(QCA_IBS_DISABLED,&q.flags);if(ssr)set_bit(QCA_SSR_TRIGGERED,&q.flags);clear_disable=completes;
  expect(qca_suspend(&dev),completes?0:-ETIMEDOUT);
  assert(writes==completes&&test_bit(QCA_SUSPENDING,&q.flags)==completes);
  expect(qca_resume(&dev),0);assert(!test_bit(QCA_SUSPENDING,&q.flags));
 }
 printf("{\"cases\":%u,\"contract_mismatches\":%u,\"zero_or_short_write_lifecycle_violations\":%u,\"negative_wait_lifecycle_violations\":%u}\n",cases,mismatches,zero_or_short_writes,negative_waits);
 return 0;
}
'''
out = Path('/mnt/e/edk2-samurai-out/bluetooth-transport-20261023/test-output')
out.mkdir(parents=True, exist_ok=True)
results = {}
variants = {'qca_suspend_current': suspend, 'qca_suspend_candidate': candidate}
if len(sys.argv) == 3 and sys.argv[1] == '--r2':
    r2_text = Path(sys.argv[2]).read_text()
    start = r2_text.index('static int __maybe_unused qca_suspend(')
    brace = r2_text.index('{', start)
    level, end = 1, brace + 1
    while level:
        level += (r2_text[end] == '{') - (r2_text[end] == '}')
        end += 1
    variants['qca_suspend_r2'] = r2_text[start:end] + '\n'
for name, body in variants.items():
    c = out / (name + '.c')
    c.write_text(prefix + body + resume + tests)
    binary = out / name
    cp = subprocess.run(['gcc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-O1', '-g',
        '-fsanitize=address,undefined', '-fno-omit-frame-pointer', str(c), '-o', str(binary)], capture_output=True)
    (out / (name + '-build.log')).write_bytes(cp.stdout + cp.stderr)
    assert cp.returncode == 0, cp.stderr.decode()
    run = subprocess.run([str(binary)], capture_output=True)
    (out / (name + '-run.log')).write_bytes(run.stdout + run.stderr)
    assert run.returncode == 0 and not run.stderr, (run.stdout, run.stderr)
    results[name] = json.loads(run.stdout)
assert results['qca_suspend_current']['contract_mismatches'] > 0
assert results['qca_suspend_current']['zero_or_short_write_lifecycle_violations'] == 2
assert results['qca_suspend_current']['negative_wait_lifecycle_violations'] == 6
assert results['qca_suspend_candidate']['contract_mismatches'] == 0
if 'qca_suspend_r2' in results:
    assert results['qca_suspend_r2']['contract_mismatches'] == 0
report = dict(results=results, asan_ubsan_passed=True,
    actual_qca_suspend_and_resume_extracted=True, kernel_apis_and_return_faults_modeled=True,
    handset_or_shared_tree_not_changed=True, handset_failure_causality_not_claimed=True,
    source_qca_sha256=hashlib.sha256(source.encode()).hexdigest(),
    patch_sha256=hashlib.sha256(patch.encode()).hexdigest())
(R / 'qca-suspend-contract-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
