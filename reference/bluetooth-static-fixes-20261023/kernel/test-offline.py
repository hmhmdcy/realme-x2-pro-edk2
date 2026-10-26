"""Small actual-function regressions; no imports of production/radio runners."""
from pathlib import Path
import ast
import hashlib
import json
import os
import shutil
import subprocess

R = Path(__file__).resolve().parent
REF = R.parents[1]
OUT = Path('/mnt/e/edk2-samurai-out/bluetooth-static-fixes-20261023/kernel')
OUT.mkdir(parents=True, exist_ok=True)
LOCK = json.loads((R / 'source-lock.json').read_text())


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def extract(text, signature):
    start = text.index(signature)
    brace = text.index('{', start)
    level, end = 1, brace + 1
    while level:
        level += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end] + '\n'


for name, info in LOCK['baseline'].items():
    assert digest(R / 'baseline' / name) == info['sha256']
for name, expected in LOCK['candidate_sha256'].items():
    assert digest(R / 'candidate' / name) == expected

# Apply both complete-base and PM-r2 deltas with zero fuzz, compare every byte.
patch_results = []
for previous, patch in [('r0', 'kernel-static-fixes-from-r0.patch'),
                        ('pm-r2', 'kernel-static-fixes-from-pm-r2.patch')]:
    work = OUT / ('patch-' + previous) / 'drivers/bluetooth'
    work.mkdir(parents=True, exist_ok=True)
    for name in ['hci_serdev.c', 'hci_qca.c']:
        source = R / 'baseline' / name
        if previous == 'pm-r2' and name == 'hci_qca.c':
            source = OUT.parents[1] / 'bluetooth-transport-20261023/hci_qca-pm-r2.c'
        shutil.copyfile(source, work / name)
    p = subprocess.run(['patch', '--batch', '--fuzz=0', '-p1', '-d', str(work.parents[1]),
                        '-i', str(R / patch)], capture_output=True, timeout=10)
    (OUT / (previous + '-patch.log')).write_bytes(p.stdout + p.stderr)
    assert p.returncode == 0, p.stderr.decode()
    assert all((work / name).read_bytes() == (R / 'candidate' / name).read_bytes()
               for name in LOCK['candidate_sha256'])
    patch_results.append(dict(base=previous, patch_sha256=digest(R / patch), zero_fuzz=True,
                              candidate_bytes_exact=True))


def compile_c(name, text):
    c = OUT / (name + '.c')
    binary = OUT / name
    c.write_text(text)
    command = ['gcc', '-std=gnu11', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
               '-Wno-unused-function', '-Wno-unused-parameter', '-pthread',
               '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
               '-fno-pie', '-no-pie', str(c), '-o', str(binary)]
    p = subprocess.run(command, capture_output=True, timeout=45)
    (OUT / (name + '-build.log')).write_bytes(p.stdout + p.stderr)
    assert p.returncode == 0, p.stderr.decode()
    return binary


def run(binary, args, expected_asan=False):
    env = dict(os.environ, ASAN_OPTIONS='detect_leaks=1:halt_on_error=1',
               UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
    p = subprocess.run([str(binary), *args], capture_output=True, timeout=15, env=env)
    log = OUT / (binary.name + '-' + ('-'.join(args) or 'run') + '.log')
    log.write_bytes(p.stdout + p.stderr)
    if expected_asan:
        assert p.returncode != 0 and b'heap-use-after-free' in p.stderr, p.stderr.decode()
        return dict(case=args[0], original_failure_reproduced='heap-use-after-free',
                    exit=p.returncode)
    assert p.returncode == 0 and not p.stderr, (p.returncode, p.stdout.decode(), p.stderr.decode())
    return json.loads(p.stdout)


serdev = {}
fixture = (R / 'test-serdev.c.in').read_text()
shared_tx = extract((REF / 'bluetooth-transport-20261023/source/hci_ldisc.c').read_text(),
                    'int hci_uart_tx_wakeup(')
ser_signatures = ['static inline void hci_uart_tx_complete(',
    'static inline struct sk_buff *hci_uart_dequeue(', 'static void hci_uart_write_work(',
    'static int hci_uart_flush(', 'static int hci_uart_close(',
    'static int hci_uart_send_frame(', 'static size_t hci_uart_receive_buf(',
    'void hci_uart_unregister_device(']
for version in ['baseline', 'candidate']:
    text = (R / version / 'hci_serdev.c').read_text()
    functions = shared_tx + ''.join(extract(text, s) for s in ser_signatures)
    binary = compile_c('serdev-' + version, '#define FIXED ' + str(int(version == 'candidate')) + '\n' +
                       fixture.replace('/* @ACTUAL_FUNCTIONS@ */', functions))
    cases = ['writer', 'rx', 'flush', 'nonpersistent', 'init_failed'] if version == 'candidate' else ['writer', 'flush']
    serdev[version] = [run(binary, [case], expected_asan=version == 'baseline' and case == 'writer')
                      for case in cases]

# Reuse only literal fixture strings from the frozen PM-r2 test. Do not import it:
# its top-level code generates old artifacts, which this task must leave intact.
old_test = REF / 'bluetooth-transport-20261023/test-qca-pm-recovery.py'
tree = ast.parse(old_test.read_text())
values = {}
for node in tree.body:
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        name = node.targets[0].id
        if name in ['prefix', 'tests', 'common_signatures']:
            values[name] = ast.literal_eval(node.value)
prefix = values['prefix'].replace('struct timer_list {bool pending;',
    'struct timer_list {bool shutdown;bool pending;')
prefix = prefix.replace('struct sk_buff_head txq,tx_wait_q;',
    'struct sk_buff_head txq,tx_wait_q,rx_memdump_q;struct sk_buff *rx_skb;')
prefix = prefix.replace('static unsigned allocated,freed,tx_frames,tx_wakes,tx_sleeps,tx_acks;',
    'static unsigned allocated,freed,tx_frames,tx_wakes,tx_sleeps,tx_acks,fail_alloc;static bool tx_enabled=true;')
prefix = prefix.replace('(void)f;assert(n<16);struct sk_buff *s=calloc',
    '(void)f;assert(n<16);if(fail_alloc){fail_alloc--;return NULL;}struct sk_buff *s=calloc')
prefix = prefix.replace('assert(s);freed++;free(s);', 'if(s){freed++;free(s);}')
prefix = prefix.replace('assert(depth&&irq_disabled);t->pending=true;t->expires=e;',
    'assert(depth&&irq_disabled);if(!t->shutdown){t->pending=true;t->expires=e;}')
prefix = prefix.replace('assert(!depth&&!irq_disabled);struct sk_buff *s;',
    'assert(!depth&&!irq_disabled);if(!tx_enabled)return;struct sk_buff *s;')
extra_declarations = r'''
static void qca_wq_awake_device(struct work_struct *);
static void timer_shutdown_sync(struct timer_list *t){assert(!depth&&!irq_disabled);t->pending=false;t->shutdown=true;}
static void destroy_workqueue(void *p){(void)p;assert(!depth&&!irq_disabled);if(q.ws_awake_device.pending){q.ws_awake_device.pending=false;qca_wq_awake_device(&q.ws_awake_device);}}
static void kfree(void *p){assert(p==&q);}
static void skb_queue_purge(struct sk_buff_head *h){struct sk_buff *s;while((s=skb_dequeue(h)))kfree_skb(s);}
static void qca_power_off(struct hci_uart *h){(void)h;assert(false);}
'''
oom_tests = r'''
 assert(!progress_failures&&!idle_failures&&!ack_failures&&!asleep_failures&&!ssr_failures);
 unsigned old_cases=cases;
 // One failed recovery WAKE has no previous WAKE/ACK to rescue progress.
 reset(HCI_IBS_TX_WAKING);enqueue_frame();write_result=0;assert(qca_suspend(&dev)==-EIO);
 unsigned before_wakes=q.ibs_sent_wakes;fail_alloc=1;retransmit();
 bool wake_rearmed=q.wake_retrans_timer.pending&&q.tx_ibs_state==HCI_IBS_TX_WAKING&&q.tx_wait_q.count==1&&q.ibs_sent_wakes==before_wakes;
 if(FIXED){assert(wake_rearmed);retransmit();wake_ack();assert(tx_frames==1&&tx_wakes==1&&!q.wake_retrans_timer.pending);}
 else assert(!wake_rearmed);
 // Repeated memory pressure remains paced; counters/state never claim acceptance.
 reset(HCI_IBS_TX_WAKING);enqueue_frame();fail_alloc=2;retransmit();
 if(FIXED){retransmit();assert(q.wake_retrans_timer.pending&&q.ibs_sent_wakes==0&&tx_wakes==0);retransmit();wake_ack();assert(tx_frames==1);}
 fail_alloc=0;
 // Idle retries preserve AWAKE/vote until allocation succeeds, then vote off.
 reset(HCI_IBS_TX_AWAKE);fail_alloc=1;idle();
 bool idle_rearmed=q.tx_idle_timer.pending&&q.tx_ibs_state==HCI_IBS_TX_AWAKE&&q.tx_vote&&!q.ws_tx_vote_off.pending&&q.ibs_sent_slps==0;
 if(FIXED){assert(idle_rearmed);idle();assert(q.tx_ibs_state==HCI_IBS_TX_ASLEEP&&q.ws_tx_vote_off.pending);qca_wq_serial_tx_clock_vote_off(&q.ws_tx_vote_off);assert(!q.tx_vote&&tx_sleeps==1);}
 else assert(!idle_rearmed);
 // ACK cancels a retry; a stale timer invocation cannot fabricate another WAKE.
 reset(HCI_IBS_TX_WAKING);enqueue_frame();fail_alloc=1;retransmit();wake_ack();unsigned accepted=tx_wakes;retransmit();assert(tx_wakes==accepted&&tx_frames==1&&!q.wake_retrans_timer.pending);
 // Timer shutdown remains final even if an expired handler sees allocation failure.
 reset(HCI_IBS_TX_AWAKE);timer_shutdown_sync(&q.tx_idle_timer);fail_alloc=1;hci_ibs_tx_idle_timeout(&q.tx_idle_timer);assert(!q.tx_idle_timer.pending);fail_alloc=0;
 // Serdev has stopped new RX/TX. Draining an already queued wake work can
 // allocate one final IBS skb, which close must purge after the drain.
 reset(HCI_IBS_TX_WAKING);tx_enabled=false;set_bit(QCA_BT_OFF,&q.flags);assert(!qca_close(q.hu));
 unsigned close_leaks=allocated-freed;
 if(FIXED)assert(!close_leaks);else{assert(close_leaks==1);drain(&q.txq);}
 tx_enabled=true;
 printf("{\"pm_r2_regression_scenarios\":%u,\"new_scenarios\":6,\"wake_oom_rearmed\":%s,\"idle_oom_rearmed\":%s,\"close_leaks\":%u,\"allocated_equals_freed\":%s}\n",old_cases,wake_rearmed?"true":"false",idle_rearmed?"true":"false",close_leaks,allocated==freed?"true":"false");
 return 0;
'''
qca_results = {}
for version in ['pm-r2', 'candidate']:
    path = OUT.parents[1] / 'bluetooth-transport-20261023/hci_qca-pm-r2.c' if version == 'pm-r2' else R / 'candidate/hci_qca.c'
    source = path.read_text()
    signatures = values['common_signatures'] + ['static void qca_wq_awake_device(',
        'static void qca_wq_serial_tx_clock_vote_off(', 'static int qca_close(',
        'static int __maybe_unused qca_suspend(', 'static int __maybe_unused qca_resume(']
    functions = ''.join(extract(source, s) for s in signatures)
    tests = values['tests']
    end = tests.index(' printf(')
    original_checks = tests[:end]
    binary = compile_c('qca-' + version, '#define FIXED ' + str(int(version == 'candidate')) + '\n' +
        prefix + extra_declarations + functions + original_checks + oom_tests + '}\n')
    qca_results[version] = run(binary, [])
    if version == 'candidate':
        assert all(qca_results[version][k] for k in ['wake_oom_rearmed', 'idle_oom_rearmed', 'allocated_equals_freed'])

result = dict(fixed_commit=LOCK['commit'], patches=patch_results, serdev=serdev, qca=qca_results,
    actual_functions_extracted=True, pthread_concurrency_and_kernel_api_models=True,
    asan_ubsan=True, handset_radio_ssh_winrt_access=False, kernel_objects_built=False,
    candidate_sha256=LOCK['candidate_sha256'], harness_sha256=digest(R / 'test-serdev.c.in'),
    test_runner_sha256=digest(Path(__file__)), reused_frozen_pm_test_sha256=digest(old_test),
    private_output=str(OUT), prior_outputs_unchanged=True)
(OUT / 'offline-validation-private.json').write_text(json.dumps(result, indent=2) + '\n')
(R / 'offline-validation.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
