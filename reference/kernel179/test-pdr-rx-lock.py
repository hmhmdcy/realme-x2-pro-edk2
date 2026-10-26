#!/usr/bin/env python3
"""Reproduce notifier lock contention using actual PDR and QMI RX functions.

The unlock variant is a causal negative control, not a kernel patch: it lacks
the lifetime and generation handling required for a deployable fix.
"""
from pathlib import Path
import hashlib
import json
import re
import subprocess

ROOT = Path('/home/cy122/pmos-samurai-kernel136/kernel')
OUT = Path('/mnt/e/edk2-samurai-out/kernel179/pdr-rx-lock')
PUBLIC = Path(__file__).resolve().parent
OUT.mkdir(parents=True, exist_ok=True)


def extract(source, name):
    match = re.search(r'^(?:static )?(?:int|void) ' + name + r'\(', source, re.M)
    assert match, name
    start = source.index('{', match.start())
    depth, end = 1, start + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[match.start():end]


pdr = (ROOT / 'drivers/soc/qcom/pdr_interface.c').read_text()
qmi = (ROOT / 'drivers/soc/qcom/qmi_interface.c').read_text()
pdr_names = ['pdr_register_listener', 'pdr_notifier_work',
             'pdr_notifier_new_server', 'pdr_notifier_del_server']
qmi_names = ['qmi_txn_wait', 'qmi_txn_cancel', 'qmi_data_ready_work']
functions = {n: extract(pdr if n in pdr_names else qmi, n)
             for n in pdr_names + qmi_names}

prefix = r'''
#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <errno.h>
#include <pthread.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <time.h>
typedef uint16_t u16;
#define HZ 1
#define AF_QIPCRTR 42
#define QRTR_PORT_CTRL 0xffffffffu
#define MSG_DONTWAIT 1
#define SERVREG_REGISTER_LISTENER_REQ 0x20
#define SERVREG_REGISTER_LISTENER_REQ_LEN 80
#define QMI_RESULT_SUCCESS_V01 0
#define SERVREG_SERVICE_STATE_DOWN 0
#define SERVREG_SERVICE_STATE_UP 1
#define container_of(p,t,m) ((t *)((char *)(p)-offsetof(t,m)))
#define pr_err(...) (++error_count)
static int error_count;
struct list_head { struct list_head *next, *prev; };
static void list_init(struct list_head *h) { h->next=h->prev=h; }
static void list_add(struct list_head *n, struct list_head *h) {
 n->next=h->next; n->prev=h; h->next->prev=n; h->next=n;
}
#define list_for_each_entry(p,h,m) \
 for(p=container_of((h)->next,__typeof__(*p),m); &p->m!=(h); \
     p=container_of(p->m.next,__typeof__(*p),m))
struct mutex { pthread_mutex_t real; };
static struct mutex *tracked_list_lock;
static _Atomic int rx_thread_started, control_blocked;
static _Thread_local bool in_rx;
static void mutex_init(struct mutex *m) { assert(!pthread_mutex_init(&m->real, NULL)); }
static void mutex_lock(struct mutex *m) {
 if(in_rx && m==tracked_list_lock) {
  int ret=pthread_mutex_trylock(&m->real);
  if(!ret) return;
  assert(ret==EBUSY); atomic_fetch_add(&control_blocked, 1);
 }
 assert(!pthread_mutex_lock(&m->real));
}
static void mutex_unlock(struct mutex *m) { assert(!pthread_mutex_unlock(&m->real)); }
struct work_struct { int unused; };
struct sockaddr_qrtr { unsigned sq_family, sq_node, sq_port; };
struct qmi_service { unsigned service, instance, node, port; };
struct completion { pthread_mutex_t lock; pthread_cond_t cond; int done; };
struct qmi_handle;
struct qmi_txn {
 struct qmi_handle *qmi; struct completion completion; struct mutex lock;
 int id, result; void *response;
};
struct qmi_ops {
 void (*msg_handler)(struct qmi_handle *,struct sockaddr_qrtr *,void *,ssize_t);
};
struct socket { int unused; };
struct qmi_handle {
 struct work_struct work; struct qmi_ops ops; struct sockaddr_qrtr sq;
 struct mutex sock_lock, txn_lock; struct socket *sock;
 char *recv_buf; size_t recv_buf_size; struct qmi_txn *txns;
};
struct pdr_service {
 char service_name[65],service_path[65]; struct sockaddr_qrtr addr;
 unsigned instance,service; int state;
 bool need_notifier_register,need_notifier_remove,need_locator_lookup,service_connected;
 struct list_head node;
};
struct pdr_handle {
 struct qmi_handle notifier_hdl; struct list_head lookups;
 struct mutex list_lock,status_lock; struct work_struct notifier_work;
 void *notifier_wq; void (*status)(int,char *,void *); void *priv;
};
struct servreg_register_listener_resp {
 struct { int result, error; } resp; int curr_state;
};
struct servreg_register_listener_req { bool enable; char service_path[65]; };
struct msghdr { void *msg_name; size_t msg_namelen; };
struct kvec { void *iov_base; size_t iov_len; };
static char servreg_register_listener_resp_ei[1],servreg_register_listener_req_ei[1];
int qmi_txn_wait(struct qmi_txn *,unsigned long);
void qmi_txn_cancel(struct qmi_txn *);
static pthread_mutex_t packet_lock=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t packet_cond=PTHREAD_COND_INITIALIZER;
static bool request_sent;
static int scenario, packet_index, late_replies, replies, callbacks, final_state;
static struct qmi_handle *current_qmi;
static int strscpy(char *d,const char *s,size_t n) {
 size_t len=strlen(s); assert(len<n); memcpy(d,s,len+1); return (int)len;
}
static void idr_remove(struct qmi_txn **slot,int id) { assert(id==1); *slot=NULL; }
static int wait_for_completion_timeout(struct completion *c,unsigned long timeout) {
 assert(timeout==5*HZ);
 struct timespec until; assert(!clock_gettime(CLOCK_REALTIME,&until));
 until.tv_nsec+=200000000;
 if(until.tv_nsec>=1000000000) { until.tv_sec++; until.tv_nsec-=1000000000; }
 assert(!pthread_mutex_lock(&c->lock));
 int ret=0;
 while(!c->done && ret!=ETIMEDOUT) {
  ret=pthread_cond_timedwait(&c->cond,&c->lock,&until);
  assert(ret==0 || ret==ETIMEDOUT);
 }
 int done=c->done;
 assert(!pthread_mutex_unlock(&c->lock)); return done;
}
static int qmi_txn_init(struct qmi_handle *q,struct qmi_txn *t,void *ei,void *resp) {
 memset(t,0,sizeof(*t)); t->qmi=q; t->id=1; t->response=resp;
 mutex_init(&t->lock);
 assert(!pthread_mutex_init(&t->completion.lock,NULL));
 assert(!pthread_cond_init(&t->completion.cond,NULL));
 mutex_lock(&q->txn_lock); assert(!q->txns); q->txns=t; mutex_unlock(&q->txn_lock);
 return 0;
}
static int qmi_send_request(struct qmi_handle *q,struct sockaddr_qrtr *addr,
 struct qmi_txn *t,int type,int len,void *ei,void *req) {
 assert(type==SERVREG_REGISTER_LISTENER_REQ);
 assert(addr->sq_node==7 && addr->sq_port==100);
 assert(!pthread_mutex_lock(&packet_lock));
 request_sent=true; assert(!pthread_cond_broadcast(&packet_cond));
 assert(!pthread_mutex_unlock(&packet_lock)); return 0;
}
static void queue_work(void *wq,struct work_struct *work) {}
static ssize_t kernel_recvmsg(struct socket *s,struct msghdr *msg,struct kvec *iv,
 int n,size_t len,int flags) {
 assert(!pthread_mutex_lock(&packet_lock));
 while(!request_sent) assert(!pthread_cond_wait(&packet_cond,&packet_lock));
 int index=packet_index++;
 assert(!pthread_mutex_unlock(&packet_lock));
 struct sockaddr_qrtr *sq=msg->msg_name;
 if(index==0 && scenario!=0) {
  *sq=(struct sockaddr_qrtr){AF_QIPCRTR,1,QRTR_PORT_CTRL};
  *(char *)iv->iov_base=(char)scenario; return 1;
 }
 if(index==(scenario==0 ? 0 : 1)) {
  *sq=(struct sockaddr_qrtr){AF_QIPCRTR,7,100};
  *(char *)iv->iov_base='R'; return 1;
 }
 return -EAGAIN;
}
static void qmi_handle_net_reset(struct qmi_handle *q) { assert(false); }
static void qmi_recv_ctrl_pkt(struct qmi_handle *,void *,ssize_t);
static void qmi_handle_message(struct qmi_handle *q,struct sockaddr_qrtr *sq,
 void *buf,ssize_t len) {
 assert(*(char *)buf=='R');
 mutex_lock(&q->txn_lock);
 struct qmi_txn *t=q->txns;
 if(!t) { late_replies++; mutex_unlock(&q->txn_lock); return; }
 mutex_lock(&t->lock);
 struct servreg_register_listener_resp *resp=t->response;
 resp->resp.result=QMI_RESULT_SUCCESS_V01; resp->curr_state=SERVREG_SERVICE_STATE_UP;
 replies++;
 assert(!pthread_mutex_lock(&t->completion.lock));
 t->completion.done=1; assert(!pthread_cond_broadcast(&t->completion.cond));
 assert(!pthread_mutex_unlock(&t->completion.lock));
 mutex_unlock(&t->lock); mutex_unlock(&q->txn_lock);
}
'''

suffix = r'''
static void qmi_recv_ctrl_pkt(struct qmi_handle *q,void *buf,ssize_t len) {
 struct qmi_service svc={.service=999,.instance=99,.node=8,.port=101};
 char type=*(char *)buf;
 if(type==1) pdr_notifier_del_server(q,&svc);
 else if(type==2) assert(!pdr_notifier_new_server(q,&svc));
 else { assert(type==3); svc.service=1; svc.instance=1; svc.node=7; svc.port=100;
        pdr_notifier_del_server(q,&svc); }
}
static void status(int state,char *path,void *priv) {
 assert(!strcmp(path,"msm/adsp/audio_pd")); callbacks++; final_state=state;
}
static void *rx_worker(void *arg) {
 in_rx=true; atomic_store(&rx_thread_started,1);
 qmi_data_ready_work(&current_qmi->work); return NULL;
}
int main(int argc,char **argv) {
 assert(argc==3); scenario=atoi(argv[1]); int expected_timeout=atoi(argv[2]);
 struct pdr_handle h={0}; struct pdr_service s={0}; struct socket sock;
 char buf[64];
 mutex_init(&h.list_lock); mutex_init(&h.status_lock);
 mutex_init(&h.notifier_hdl.sock_lock); mutex_init(&h.notifier_hdl.txn_lock);
 tracked_list_lock=&h.list_lock;
 list_init(&h.lookups); list_add(&s.node,&h.lookups);
 strcpy(s.service_path,"msm/adsp/audio_pd"); s.service=1; s.instance=1;
 s.addr=(struct sockaddr_qrtr){AF_QIPCRTR,7,100};
 s.service_connected=true; s.need_notifier_register=true;
 h.status=status; h.notifier_hdl.sock=&sock; h.notifier_hdl.sq.sq_node=1;
 h.notifier_hdl.recv_buf=buf; h.notifier_hdl.recv_buf_size=sizeof(buf);
 current_qmi=&h.notifier_hdl;
 pthread_t rx; assert(!pthread_create(&rx,NULL,rx_worker,NULL));
 pdr_notifier_work(&h.notifier_work);
 assert(!pthread_join(rx,NULL));
 assert(callbacks==1);
 if(expected_timeout) {
  assert(error_count==1 && final_state==SERVREG_SERVICE_STATE_DOWN);
  assert(replies==0 && late_replies==1 && atomic_load(&control_blocked)==1);
 } else {
  assert(error_count==0 && final_state==SERVREG_SERVICE_STATE_UP);
  assert(replies==1 && late_replies==0 && atomic_load(&control_blocked)==0);
 }
 printf("{\"scenario\":%d,\"register_timed_out\":%s,\"callback_state\":%d,"
        "\"rx_blocked_on_list_lock\":%d,\"late_reply_dropped\":%d}\n",
        scenario,error_count?"true":"false",final_state,
        atomic_load(&control_blocked),late_replies);
 return 0;
}
'''

results = []
for variant in ('baseline', 'unlock-causal-control'):
    bodies = dict(functions)
    if variant != 'baseline':
        old = '\t\t\tret = pdr_register_listener(pdr, pds, true);'
        assert bodies['pdr_notifier_work'].count(old) == 1
        bodies['pdr_notifier_work'] = bodies['pdr_notifier_work'].replace(
            old, '\t\t\tmutex_unlock(&pdr->list_lock);\n' + old +
            '\n\t\t\tmutex_lock(&pdr->list_lock);')
    path = OUT / (variant + '.c')
    path.write_text(prefix + '\n' + '\n\n'.join(bodies.values()) + suffix)
    exe = OUT / variant
    compile_result = subprocess.run([
        'gcc', '-std=gnu11', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
        '-Wno-unused-parameter', '-fsanitize=address,undefined',
        '-fno-omit-frame-pointer', '-pthread', str(path), '-o', str(exe)
    ], capture_output=True, text=True, check=False)
    (OUT / (variant + '-build.log')).write_text(compile_result.stdout + compile_result.stderr)
    assert compile_result.returncode == 0, compile_result.stderr
    assert not compile_result.stderr, compile_result.stderr
    scenarios = (0, 1, 2, 3) if variant == 'baseline' else (0, 1, 2)
    for scenario in scenarios:
        expected = int(variant == 'baseline' and scenario != 0)
        result = subprocess.run([str(exe), str(scenario), str(expected)],
                                capture_output=True, text=True, timeout=5)
        (OUT / f'{variant}-{scenario}.log').write_text(result.stdout + result.stderr)
        assert result.returncode == 0, result.stderr
        assert not result.stderr, result.stderr
        row = json.loads(result.stdout)
        row['variant'] = variant
        results.append(row)

report = {
    'stage': 179,
    'kernel_source_modified': False,
    'kernel_build_or_deployment_performed': False,
    'actual_functions': {name: hashlib.sha256(body.encode()).hexdigest()
                         for name, body in functions.items()},
    'source_files': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                     for path in (ROOT / 'drivers/soc/qcom/pdr_interface.c',
                                  ROOT / 'drivers/soc/qcom/qmi_interface.c')},
    'compiler': 'gcc with AddressSanitizer and UndefinedBehaviorSanitizer',
    'mock_wait_ms': 200,
    'kernel_wait_seconds': 5,
    'scenarios': results,
    'causal_control_is_not_a_deployable_fix': True,
    'phone_failure_causality_not_directly_measured': True,
    'conclusion': 'Actual RX/PDR functions reproduce list_lock blocking control handling before a valid response; releasing the wait-side lock removes the unrelated-control timeout.',
}
(PUBLIC / 'pdr-rx-lock-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'scenarios': len(results), 'actual_baseline_timeouts': 3,
                  'causal_controls_passed': True, 'kernel_changed': False}))
