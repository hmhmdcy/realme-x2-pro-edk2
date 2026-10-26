"""Independent incremental review. Copy frozen bytes; never run author suites."""
from pathlib import Path
import hashlib
import json
import re
import subprocess

HERE = Path(__file__).resolve().parent
CANDIDATE = HERE.parents[1] / 'charging-session-20261023/eud-runtime-window-candidate'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
receipt = json.loads((CANDIDATE / 'candidate-test-result.json').read_text())
assert receipt['passed']
for name, digest in receipt['tested_files'].items():
    assert sha(CANDIDATE / name) == digest
originals = {p.name:sha(p) for p in CANDIDATE.iterdir() if p.is_file()}
(HERE / 'candidate-functions.inc').write_bytes((CANDIDATE / 'candidate-functions.inc').read_bytes())
source = (CANDIDATE / 'eud.c').read_text()
additional = []
for name in ['eud_console_device_lock', 'eud_console_device_unlock',
             'eud_console_write_thread', 'eud_console_write_atomic']:
    m = re.search(r'^static [\w\s*]+?\b'+name+r'\([^;]*?\)\n\{', source, re.M)
    assert m
    start = m.start()
    while source[start] == '\n': start += 1
    body = source[start:source.index('\n}',m.end())+2]
    additional.append(dict(name=name, line=source[:start].count('\n')+1,
                           sha256=hashlib.sha256(body.encode()).hexdigest(), body=body))
(HERE / 'nbcon-functions.inc').write_text('\n\n'.join(row['body'] for row in additional)+'\n')

fake = (CANDIDATE / 'fake-eud-os.h').read_text()
fake = fake.replace('#include <unistd.h>', '#include <unistd.h>\n#include <time.h>')
fake = fake.replace('static struct work_struct *test_current_work;', 'static __thread struct work_struct *test_current_work;')
anchor = 'static void uart_lock(struct uart_port *p, unsigned long *flags) {'
extra = r'''
static pthread_mutex_t review_lock=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t review_cond=PTHREAD_COND_INITIALIZER;
static bool review_paused,review_release,review_join_waiting,review_begin_done,review_tx_running;
static __thread bool review_writer,review_borrower,review_pause_once;
static void (*review_unlock_hook)(void),(*review_mod_hook)(void),(*review_enable_hook)(void);
static struct mutex *review_tx_mutex;
static struct work_struct *review_tx_work;
static bool *review_quiet;
static bool review_forbid_mmio;
static void review_notice_join(void) {
 assert(!pthread_mutex_lock(&review_lock));review_join_waiting=true;
 pthread_cond_broadcast(&review_cond);assert(!pthread_mutex_unlock(&review_lock));
}
struct nbcon_write_context {const char *outbuf;unsigned int len;};
static bool nbcon_enter_unsafe(struct nbcon_write_context *c){return true;}
static bool nbcon_exit_unsafe(struct nbcon_write_context *c){return true;}
static void cond_resched(void){}
static void migrate_disable(void){}
static void migrate_enable(void){}
'''
assert fake.count(anchor)==1
fake=fake.replace(anchor,extra+'\n'+anchor)
fake=fake.replace('port_depth--; assert(!pthread_mutex_unlock(&p->lock));',
                  'port_depth--; assert(!pthread_mutex_unlock(&p->lock)); if(review_unlock_hook)review_unlock_hook();')
fake=fake.replace('static void writel(u32 v, void *p) { mmio_writes++;',
                  'static void writel(u32 v, void *p) { assert(!review_forbid_mmio||!review_quiet||!*review_quiet); mmio_writes++;')
fake=fake.replace('static u32 readl(void *p) { u32 v; mmio_reads++;',
                  'static u32 readl(void *p) { u32 v; assert(!review_forbid_mmio||!review_quiet||!*review_quiet); mmio_reads++;')
fake=fake.replace('static void mutex_lock(struct mutex *p) { assert(!port_depth); assert(!pthread_mutex_lock(&p->lock)); }',
                  'static void mutex_lock(struct mutex *p) { assert(!port_depth); if(review_borrower&&p==review_tx_mutex)review_notice_join(); assert(!pthread_mutex_lock(&p->lock)); }')
old='static void cancel_work_sync(struct work_struct *p) { assert(!port_depth); p->pending = 0; cancels++; }'
new=r'''static void cancel_work_sync(struct work_struct *p) {
 assert(!port_depth);p->pending=0;cancels++;
 if(p==review_tx_work){
  assert(!pthread_mutex_lock(&review_lock));
  if(review_tx_running){review_join_waiting=true;pthread_cond_broadcast(&review_cond);}
  while(review_tx_running)pthread_cond_wait(&review_cond,&review_lock);
  assert(!pthread_mutex_unlock(&review_lock));
 }
}'''
assert fake.count(old)==1
fake=fake.replace(old,new)
fake=fake.replace('static void mod_delayed_work(void *q, struct delayed_work *p, unsigned int delay) {\n    p->work.pending = 1;',
                  'static void mod_delayed_work(void *q, struct delayed_work *p, unsigned int delay) {\n    if(review_mod_hook)review_mod_hook();\n    p->work.pending = 1;')
fake=fake.replace('static void enable_irq(int irq) { irq_enables++; }',
                  'static void enable_irq(int irq) { irq_enables++; if(review_enable_hook)review_enable_hook(); }')
(HERE / 'fake-eud-os.h').write_text(fake)
fixture = (CANDIDATE / 'test-candidate.c').read_text().split('int main(void) {',1)[0]
fixture = fixture.replace('#include "candidate-functions.inc"', '#include "candidate-functions.inc"\n#include "nbcon-functions.inc"')
fixture += r'''
static void reset_review(void){
 review_paused=review_release=review_join_waiting=review_begin_done=review_tx_running=false;
 review_writer=review_borrower=review_pause_once=false;
 review_unlock_hook=review_mod_hook=review_enable_hook=NULL;
 review_tx_mutex=&up.tx_mutex;review_tx_work=&up.tx_work;review_quiet=&up.window_quiet;
 review_forbid_mmio=true;
}
static void wait_for(bool *value){
 struct timespec deadline;assert(!clock_gettime(CLOCK_REALTIME,&deadline));deadline.tv_sec+=3;
 assert(!pthread_mutex_lock(&review_lock));
 while(!*value){int ret=pthread_cond_timedwait(&review_cond,&review_lock,&deadline);assert(!ret);}
 assert(!pthread_mutex_unlock(&review_lock));
}
static void pause_here(void){
 assert(!pthread_mutex_lock(&review_lock));review_paused=true;pthread_cond_broadcast(&review_cond);
 while(!review_release)pthread_cond_wait(&review_cond,&review_lock);
 assert(!pthread_mutex_unlock(&review_lock));
}
static void pause_writer_uart(void){if(review_writer&&!review_pause_once){review_pause_once=true;pause_here();}}
static void release_writer(void){
 assert(!pthread_mutex_lock(&review_lock));review_release=true;pthread_cond_broadcast(&review_cond);
 assert(!pthread_mutex_unlock(&review_lock));
}
static void *review_begin(void *unused){
 review_borrower=true;quiet();
 assert(!pthread_mutex_lock(&review_lock));review_begin_done=true;pthread_cond_broadcast(&review_cond);
 assert(!pthread_mutex_unlock(&review_lock));return NULL;
}
static void *review_tx(void *unused){
 review_writer=true;test_current_work=&up.tx_work;
 assert(!pthread_mutex_lock(&review_lock));review_tx_running=true;pthread_cond_broadcast(&review_cond);
 assert(!pthread_mutex_unlock(&review_lock));
 eud_tx_work(&up.tx_work);
 assert(!pthread_mutex_lock(&review_lock));review_tx_running=false;pthread_cond_broadcast(&review_cond);
 assert(!pthread_mutex_unlock(&review_lock));return NULL;
}
static void *review_console(void *unused){
 unsigned long flags;struct nbcon_write_context ctx={"ABCDEFGH",8};review_writer=true;
 eud_console_device_lock(NULL,&flags);eud_console_write_thread(NULL,&ctx);eud_console_device_unlock(NULL,flags);return NULL;
}
static void *review_legacy(void *unused){review_writer=true;eud_console_write_legacy(NULL,"log",3);return NULL;}
static u64 end_cookie;
static struct eud_com_window_result end_result;
static void *review_end(void *unused){assert(!eud_com_quiet_end(end_cookie,&end_result));return NULL;}

int main(void){
 unsigned int groups=0;pthread_t writer,borrower,remover;u64 cookie;
 clear();reset_review();enqueue();eud_shutdown(&up.port);
 assert(state.port.xmit_fifo.count==0&&up.port.icount.tx==4&&mmio_writes==6);
 struct nbcon_write_context ctx={"ABCD",4};unsigned long flags;
 eud_console_device_lock(NULL,&flags);eud_console_write_thread(NULL,&ctx);eud_console_device_unlock(NULL,flags);
 assert(mmio_writes==12&&!up.window_quiet);
 groups++;puts("default shutdown drain and actual nbcon thread remain active");

 clear();reset_review();memcpy(state.port.xmit_fifo.data,"ABCDEFGH",8);state.port.xmit_fifo.count=8;
 review_unlock_hook=pause_writer_uart;
 assert(!pthread_create(&writer,NULL,review_tx,NULL));wait_for(&review_paused);
 assert(!pthread_create(&borrower,NULL,review_begin,NULL));wait_for(&review_join_waiting);
 assert(up.window_quiet&&!review_begin_done);release_writer();
 pthread_join(writer,NULL);pthread_join(borrower,NULL);review_unlock_hook=NULL;
 assert(r.software_quiet&&up.port.icount.tx==4&&state.port.xmit_fifo.count==4&&!mmio_writes);
 cookie=r.cookie;assert(!eud_com_quiet_end(cookie,&r));eud_tx_work(&up.tx_work);
 assert(state.port.xmit_fifo.count==0&&mmio_writes==6);
 groups++;puts("begin joins an actual running TTY worker; undequeued bytes pause");

 clear();reset_review();review_unlock_hook=pause_writer_uart;
 assert(!pthread_create(&writer,NULL,review_console,NULL));wait_for(&review_paused);
 assert(mmio_writes==6);assert(!pthread_create(&borrower,NULL,review_begin,NULL));wait_for(&review_join_waiting);
 assert(up.window_quiet&&!review_begin_done);release_writer();
 pthread_join(writer,NULL);pthread_join(borrower,NULL);review_unlock_hook=NULL;
 assert(r.software_quiet&&mmio_writes==6);
 ctx=(struct nbcon_write_context){"atomic",6};eud_console_write_atomic(NULL,&ctx);assert(mmio_writes==6);
 assert(!eud_com_quiet_end(r.cookie,&r));
 groups++;puts("begin joins nbcon TX mutex; remaining thread and atomic FIFO access gate");

 clear();reset_review();registers[EUD_REG_INT_STATUS_1/sizeof(u32)]=EUD_INT_RX_PENDING;
 review_mod_hook=pause_here;assert(!pthread_create(&writer,NULL,review_legacy,NULL));wait_for(&review_paused);
 quiet();cookie=r.cookie;unsigned int reads=mmio_reads,writes=mmio_writes;
 assert(!up.rx_work.work.pending);release_writer();pthread_join(writer,NULL);review_mod_hook=NULL;
 assert(up.rx_work.work.pending&&up.window_quiet);
 up.rx_work.work.pending=0;eud_rx_work(&up.rx_work.work);
 assert(!up.rx_work.work.pending&&mmio_reads==reads&&mmio_writes==writes);
 assert(!eud_com_quiet_end(cookie,&r));
 groups++;puts("console kick after begin cancellation queues only inert quiet RX work");

 clear();reset_review();up.rx_irq_enabled=up.rx_irq_requested=true;quiet();end_cookie=r.cookie;
 review_enable_hook=pause_here;assert(!pthread_create(&borrower,NULL,review_end,NULL));wait_for(&review_paused);
 assert(!pthread_create(&remover,NULL,remove_thread,NULL));
 assert(pthread_mutex_trylock(&eud_window_lock.lock)==EBUSY);release_writer();
 pthread_join(borrower,NULL);pthread_join(remover,NULL);review_enable_hook=NULL;
 assert(end_result.restored&&!eud&&!eud_window_orphan&&ahb==0x77);
 assert(eud_com_quiet_end(end_cookie,&r)==-ENODEV&&!r.restored);
 clear();reset_review();quiet();cookie=r.cookie;assert(cookie!=end_cookie);
 assert(eud_com_quiet_end(end_cookie,&r)==-ESTALE&&up.window_quiet);
 assert(!eud_com_quiet_end(cookie,&r));
 groups++;puts("end and ordinary remove serialize; old tokens cannot restore rebound endpoint");
 printf("groups=%u\n",groups);return groups==5?0:1;
}
'''
(HERE / 'test-review.c').write_text(fixture)
flags=['-std=gnu11','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-unused-function',
       '-fsanitize=address,undefined','-fno-omit-frame-pointer','-pthread']
compile_result=subprocess.run(['gcc',*flags,str(HERE/'test-review.c'),'-o',str(HERE/'test-review')],capture_output=True,text=True)
run=subprocess.run([str(HERE/'test-review')],capture_output=True,text=True,timeout=20) if compile_result.returncode==0 else None
assert originals=={p.name:sha(p) for p in CANDIDATE.iterdir() if p.is_file()}
pd_path=HERE.parents[1]/'charging-management-20261023/pd-controls-r8-result.json'
pd_receipt=HERE.parent/'apsd-lifecycle/pd-controls-r8-correlation/result.json'
result=dict(passed=compile_result.returncode==0 and run is not None and run.returncode==0 and not run.stderr,
    scope='incremental independent actual-function review with fake OS/MMIO/IRQ/work and pthread boundaries',
    compile_returncode=compile_result.returncode,compile_stderr=compile_result.stderr,
    runtime_returncode=run.returncode if run else None,runtime_stdout=run.stdout if run else '',runtime_stderr=run.stderr if run else '',
    flags=flags,source_candidate_sha256=sha(CANDIDATE/'eud.c'),source_patch_sha256=sha(CANDIDATE/'0001-eud-optional-software-window.patch'),
    original_receipt_sha256=sha(CANDIDATE/'candidate-test-result.json'),additional_actual_functions=[{k:v for k,v in row.items() if k!='body'} for row in additional],
    files={n:sha(HERE/n) for n in ['review.py','candidate-functions.inc','nbcon-functions.inc','fake-eud-os.h','test-review.c']},
    original_suites_rerun=False,author_files_unchanged=True,phone_accessed=False,ssh_executed=False,sdk_invoked=False,
    pd_current_sha256=sha(pd_path),pd_bound_sha256=json.loads(pd_receipt.read_text())['snapshot_sha256'],
    pd_hash_matches=sha(pd_path)==json.loads(pd_receipt.read_text())['snapshot_sha256'],pd_observation_regenerated=False)
(HERE/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
raise SystemExit(0 if result['passed'] else 1)
