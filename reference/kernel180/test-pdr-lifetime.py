#!/usr/bin/env python3
"""Execute the complete current PDR C source with bounded transport/work adapters."""
from pathlib import Path
import hashlib
import json
import re
import subprocess

root = Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref = Path(__file__).resolve().parent
out = Path('/mnt/e/edk2-samurai-out/kernel180/pdr-host')
out.mkdir(parents=True, exist_ok=True)
source = (root / 'drivers/soc/qcom/pdr_interface.c').read_text()
strip_includes = lambda s: re.sub(r'^#include[^\n]*\n', '', s, flags=re.M)
protocol = strip_includes((root / 'include/linux/soc/qcom/pdr.h').read_text())
protocol += strip_includes((root / 'drivers/soc/qcom/pdr_internal.h').read_text())
actual = strip_includes(source)

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
#include <time.h>
typedef uint8_t u8; typedef uint16_t u16; typedef uint32_t u32; typedef uint64_t u64;
#define HZ 1
#define AF_QIPCRTR 42
#define QMI_SERVICE_ID_SERVREG_LOC 64
#define QMI_SERVICE_ID_SERVREG_NOTIF 65
#define QMI_RESULT_SUCCESS_V01 0
#define QMI_RESULT_FAILURE_V01 1
#define QMI_ERR_DISABLED_V01 2
#define QMI_INDICATION 4
#define WQ_HIGHPRI 1
#define EXPORT_SYMBOL_GPL(x)
#define MODULE_LICENSE(x)
#define MODULE_DESCRIPTION(x)
#define READ_ONCE(x) __atomic_load_n(&(x),__ATOMIC_ACQUIRE)
#define WRITE_ONCE(x,v) __atomic_store_n(&(x),(v),__ATOMIC_RELEASE)
#define ERR_PTR(x) ((void *)(intptr_t)(x))
#define IS_ERR_OR_NULL(p) (!(p) || (uintptr_t)(p)>(uintptr_t)-4096)
#define PTR_ERR(p) ((int)(intptr_t)(p))
#define container_of(p,t,m) ((t *)((char *)(p)-offsetof(t,m)))
#define __free(fn) __attribute__((cleanup(auto_free)))
#define return_ptr(p) return ({ __typeof__(p) result=(p); (p)=NULL; result; })
static _Atomic int error_count, allocations, allocation_calls;
static int allocation_failure;
static void *zalloc(size_t n) {
 int call=atomic_fetch_add(&allocation_calls,1)+1;
 if(call==allocation_failure) return NULL;
 void *p=calloc(1,n); assert(p); atomic_fetch_add(&allocations,1); return p;
}
static void kfree(void *p) { if(p){ atomic_fetch_sub(&allocations,1); free(p); } }
static void auto_free(void *p) { kfree(*(void **)p); }
#define kzalloc_obj(x) zalloc(sizeof(x))
#define pr_err(...) ((void)atomic_fetch_add(&error_count,1))
#define pr_info(...) ((void)0)
#define pr_debug(...) ((void)0)
static int strscpy(char *d,const char *s,size_t n) {
 size_t len=strlen(s); assert(len<n); memcpy(d,s,len+1); return (int)len;
}
struct list_head { struct list_head *next,*prev; };
#define INIT_LIST_HEAD(h) ((h)->next=(h)->prev=(h))
static void list_add_between(struct list_head *n,struct list_head *p,struct list_head *q) {
 n->next=q;n->prev=p;p->next=n;q->prev=n;
}
static void list_add(struct list_head *n,struct list_head *h){list_add_between(n,h,h->next);}
static void list_add_tail(struct list_head *n,struct list_head *h){list_add_between(n,h->prev,h);}
static void list_del(struct list_head *n){n->prev->next=n->next;n->next->prev=n->prev;}
static void list_move_tail(struct list_head *n,struct list_head *h){list_del(n);list_add_tail(n,h);}
static bool list_empty(struct list_head *h){return h->next==h;}
#define list_first_entry(h,t,m) container_of((h)->next,t,m)
#define list_for_each_entry(p,h,m) \
 for(p=container_of((h)->next,__typeof__(*p),m); &p->m!=(h); \
     p=container_of(p->m.next,__typeof__(*p),m))
#define list_for_each_entry_safe(p,t,h,m) \
 for(p=container_of((h)->next,__typeof__(*p),m),t=container_of(p->m.next,__typeof__(*p),m); \
     &p->m!=(h);p=t,t=container_of(t->m.next,__typeof__(*t),m))
struct mutex { pthread_mutex_t real; };
static void mutex_init(struct mutex *m) { assert(!pthread_mutex_init(&m->real,NULL)); }
static void mutex_lock(struct mutex *m) { assert(!pthread_mutex_lock(&m->real)); }
static void mutex_unlock(struct mutex *m) { assert(!pthread_mutex_unlock(&m->real)); }
#define lockdep_assert_held(m) ((void)0)
struct work_struct { void (*fn)(struct work_struct *); bool pending,running; };
struct workqueue_struct { int unused; };
static pthread_mutex_t work_lock=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t work_cond=PTHREAD_COND_INITIALIZER;
#define INIT_WORK(w,f) ((w)->fn=(f))
static bool queue_work(struct workqueue_struct *q,struct work_struct *w) {
 assert(q); assert(!pthread_mutex_lock(&work_lock));
 bool old=w->pending;w->pending=true;
 assert(!pthread_mutex_unlock(&work_lock));return !old;
}
static void schedule_work(struct work_struct *w) {
 assert(!pthread_mutex_lock(&work_lock));w->pending=true;
 assert(!pthread_mutex_unlock(&work_lock));
}
static struct workqueue_struct *create_singlethread_workqueue(const char *name) {
 return zalloc(sizeof(struct workqueue_struct));
}
static struct workqueue_struct *alloc_ordered_workqueue(const char *name,int flags) {
 return create_singlethread_workqueue(name);
}
static void cancel_work_sync(struct work_struct *w) {
 assert(!pthread_mutex_lock(&work_lock));w->pending=false;
 while(w->running) assert(!pthread_cond_wait(&work_cond,&work_lock));
 assert(!pthread_mutex_unlock(&work_lock));
}
static void destroy_workqueue(struct workqueue_struct *q) { kfree(q); }
static void run_work(struct work_struct *w) {
 assert(!pthread_mutex_lock(&work_lock));assert(!w->running);w->running=true;w->pending=false;
 assert(!pthread_mutex_unlock(&work_lock));
 w->fn(w);
 assert(!pthread_mutex_lock(&work_lock));w->running=false;
 assert(!pthread_cond_broadcast(&work_cond));assert(!pthread_mutex_unlock(&work_lock));
}
struct sockaddr_qrtr { unsigned sq_family,sq_node,sq_port; };
struct qmi_service { unsigned service,version,instance,node,port; };
struct qmi_response_type_v01 { int result,error; };
struct qmi_elem_info { int unused; };
struct qmi_handle;
struct completion { pthread_mutex_t lock;pthread_cond_t cond;bool done; };
static void complete(struct completion *c) {
 assert(!pthread_mutex_lock(&c->lock));c->done=true;
 assert(!pthread_cond_broadcast(&c->cond));assert(!pthread_mutex_unlock(&c->lock));
}
struct qmi_txn {
 struct qmi_handle *qmi; void *response; unsigned type;struct sockaddr_qrtr addr;
 struct mutex lock;struct completion completion;int result;pthread_t rx;bool has_rx;
};
struct qmi_ops {
 int (*new_server)(struct qmi_handle *,struct qmi_service *);
 void (*del_server)(struct qmi_handle *,struct qmi_service *);
};
struct qmi_msg_handler {
 int type,msg_id;const struct qmi_elem_info *ei;size_t decoded_size;
 void (*fn)(struct qmi_handle *,struct sockaddr_qrtr *,struct qmi_txn *,const void *);
};
struct qmi_handle { struct qmi_ops ops;bool initialized; };
static int qmi_handle_init(struct qmi_handle *,size_t,const struct qmi_ops *,const struct qmi_msg_handler *);
static void qmi_handle_release(struct qmi_handle *);
static int qmi_add_lookup(struct qmi_handle *,unsigned,unsigned,unsigned);
static int qmi_txn_init(struct qmi_handle *,struct qmi_txn *,const struct qmi_elem_info *,void *);
static int qmi_send_request(struct qmi_handle *,struct sockaddr_qrtr *,struct qmi_txn *,int,int,const struct qmi_elem_info *,void *);
static int qmi_txn_wait(struct qmi_txn *,unsigned long);
static void qmi_txn_cancel(struct qmi_txn *);
'''
ei_defs = '\n'.join('const struct qmi_elem_info ' + name + '[1];'
                    for name in re.findall(r'extern const struct qmi_elem_info (\w+)\[\];', protocol))

suffix = r'''
static struct pdr_handle *handle;
static struct pdr_service *service;
static int scenario,reg_requests,locator_requests,ack_count,states[128],nstate;
static struct sockaddr_qrtr ack_addr[32],reg_addr[32];
static bool status_reentrant;
static int qmi_init_count,qmi_init_failure,add_lookup_failure,send_failure,wait_failure;
static pthread_mutex_t gate_lock=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t gate_cond=PTHREAD_COND_INITIALIZER;
static bool gate_entered,gate_open;
static struct qmi_service old_peer={QMI_SERVICE_ID_SERVREG_NOTIF,1,1,7,100};
static struct qmi_service new_peer={QMI_SERVICE_ID_SERVREG_NOTIF,1,1,9,200};
static struct qmi_service locator_peer={QMI_SERVICE_ID_SERVREG_LOC,1,1,2,50};
static struct qmi_service new_locator={QMI_SERVICE_ID_SERVREG_LOC,1,1,3,60};
static void status_cb(int state,char *path,void *priv) {
 assert(!READ_ONCE(handle->stopping));assert(!strcmp(path,"msm/adsp/audio_pd"));
 assert(!pthread_mutex_trylock(&handle->list_lock.real));
 assert(!pthread_mutex_unlock(&handle->list_lock.real));
 assert(nstate<128);states[nstate++]=state;
 if(status_reentrant) {
  status_reentrant=false;
  struct pdr_service *extra=pdr_add_lookup(handle,"another/service","unused/domain");
  assert(!IS_ERR_OR_NULL(extra));
 }
}
static int qmi_handle_init(struct qmi_handle *q,size_t size,const struct qmi_ops *ops,
 const struct qmi_msg_handler *handlers) {
 qmi_init_count++;if(qmi_init_count==qmi_init_failure)return -EIO;
 q->ops=*ops;q->initialized=true;return 0;
}
static void qmi_handle_release(struct qmi_handle *q) {
 assert(q->initialized);
 if(handle) {
  assert(!handle->locator_work.running && !handle->notifier_work.running && !handle->indack_work.running);
  q->ops.del_server(q,q==&handle->locator_hdl?&locator_peer:&old_peer);
 }
 q->initialized=false;
}
static int qmi_add_lookup(struct qmi_handle *q,unsigned id,unsigned ver,unsigned inst) {
 assert(q->initialized);return add_lookup_failure?-EIO:0;
}
static int qmi_txn_init(struct qmi_handle *q,struct qmi_txn *t,const struct qmi_elem_info *ei,void *resp) {
 assert(q->initialized);memset(t,0,sizeof(*t));t->qmi=q;t->response=resp;
 mutex_init(&t->lock);assert(!pthread_mutex_init(&t->completion.lock,NULL));
 assert(!pthread_cond_init(&t->completion.cond,NULL));return 0;
}
static void indicate(struct sockaddr_qrtr addr,int state,int tid) {
 struct servreg_state_updated_ind ind={.curr_state=state,.transaction_id=tid};
 strcpy(ind.service_path,"msm/adsp/audio_pd");
 pdr_indication_cb(&handle->notifier_hdl,&addr,NULL,&ind);
}
static void *rx_response(void *arg) {
 struct qmi_txn *t=arg;
 if(t->type==SERVREG_REGISTER_LISTENER_REQ) {
  int current=scenario;scenario=0;
  struct qmi_service unrelated={QMI_SERVICE_ID_SERVREG_NOTIF,1,99,8,150};
  if(current==1)pdr_notifier_del_server(&handle->notifier_hdl,&unrelated);
  if(current==2)assert(!pdr_notifier_new_server(&handle->notifier_hdl,&unrelated));
  if(current==3) {
   pdr_notifier_del_server(&handle->notifier_hdl,&old_peer);
   run_work(&handle->indack_work);
  }
  if(current==4) {
   assert(!pdr_notifier_new_server(&handle->notifier_hdl,&new_peer));
   pdr_notifier_del_server(&handle->notifier_hdl,&old_peer);
   run_work(&handle->indack_work);
  }
  if(current==5) {
   indicate(t->addr,SERVREG_SERVICE_STATE_UP,11);
   run_work(&handle->indack_work);
  }
  if(current==6) {
   indicate(t->addr,SERVREG_SERVICE_STATE_DOWN,12);
   indicate(t->addr,SERVREG_SERVICE_STATE_UP,13);
   run_work(&handle->indack_work);
  }
  if(current==7) {
   assert(!pdr_notifier_new_server(&handle->notifier_hdl,&old_peer));
  }
  if(current==8) {
   assert(!pthread_mutex_lock(&gate_lock));gate_entered=true;
   assert(!pthread_cond_broadcast(&gate_cond));
   while(!gate_open)assert(!pthread_cond_wait(&gate_cond,&gate_lock));
   assert(!pthread_mutex_unlock(&gate_lock));
  }
  if(current==13) {
   pdr_notifier_del_server(&handle->notifier_hdl,&old_peer);
   run_work(&handle->indack_work);
   return NULL;
  }
  struct servreg_register_listener_resp *resp=t->response;
  resp->resp.result=QMI_RESULT_SUCCESS_V01;
  resp->curr_state_valid=current!=9;
  resp->curr_state=(current==5 || current==6)?SERVREG_SERVICE_STATE_DOWN:SERVREG_SERVICE_STATE_UP;
 } else if(t->type==SERVREG_GET_DOMAIN_LIST_REQ) {
  struct servreg_get_domain_list_resp *resp=t->response;
  resp->resp.result=0;resp->total_domains_valid=1;resp->total_domains=1;
  resp->domain_list_valid=1;resp->domain_list_len=1;
  strcpy(resp->domain_list[0].name,scenario==10?"wrong/domain":"msm/adsp/audio_pd");
  resp->domain_list[0].instance=1;
  if(scenario==11) {
   scenario=0;resp->domain_list[0].instance=999;
   assert(!pdr_locator_new_server(&handle->locator_hdl,&new_locator));
  }
 } else if(t->type==SERVREG_RESTART_PD_REQ) {
  struct servreg_restart_pd_resp *resp=t->response;
  resp->resp.result=scenario==12?QMI_RESULT_FAILURE_V01:QMI_RESULT_SUCCESS_V01;
  resp->resp.error=QMI_ERR_DISABLED_V01;
 } else assert(false);
 mutex_lock(&t->lock);complete(&t->completion);mutex_unlock(&t->lock);return NULL;
}
static int qmi_send_request(struct qmi_handle *q,struct sockaddr_qrtr *addr,struct qmi_txn *t,
 int type,int len,const struct qmi_elem_info *ei,void *req) {
 assert(q->initialized);t->type=type;t->addr=*addr;
 if(send_failure)return -EIO;
 if(type==SERVREG_SET_ACK_REQ) {
  assert(ack_count<32);ack_addr[ack_count++]=*addr;return 0;
 }
 if(type==SERVREG_REGISTER_LISTENER_REQ) {assert(reg_requests<32);reg_addr[reg_requests++]=*addr;}
 if(type==SERVREG_GET_DOMAIN_LIST_REQ)locator_requests++;
 if(!wait_failure){t->has_rx=true;assert(!pthread_create(&t->rx,NULL,rx_response,t));}
 return 0;
}
static void txn_done(struct qmi_txn *t) {
 if(t->has_rx)assert(!pthread_join(t->rx,NULL));
 assert(!pthread_cond_destroy(&t->completion.cond));
 assert(!pthread_mutex_destroy(&t->completion.lock));assert(!pthread_mutex_destroy(&t->lock.real));
}
static int qmi_txn_wait(struct qmi_txn *t,unsigned long timeout) {
 assert(timeout==5*HZ);
 struct timespec until;assert(!clock_gettime(CLOCK_REALTIME,&until));until.tv_nsec+=300000000;
 if(until.tv_nsec>=1000000000){until.tv_sec++;until.tv_nsec-=1000000000;}
 assert(!pthread_mutex_lock(&t->completion.lock));int ret=0;
 while(!t->completion.done && ret!=ETIMEDOUT) {
  ret=pthread_cond_timedwait(&t->completion.cond,&t->completion.lock,&until);assert(!ret || ret==ETIMEDOUT);
 }
 bool done=t->completion.done;assert(!pthread_mutex_unlock(&t->completion.lock));
 /* A blocked RX is intentionally left for the process timeout in lock mutants. */
 if(!done && t->has_rx)abort();
 int result=t->result;txn_done(t);return done?result:-ETIMEDOUT;
}
static void qmi_txn_cancel(struct qmi_txn *t) { txn_done(t); }
static void reset_counters(void) {
 assert(!atomic_load(&allocations));handle=NULL;service=NULL;scenario=0;
 reg_requests=locator_requests=ack_count=nstate=qmi_init_count=0;
 qmi_init_failure=allocation_failure=add_lookup_failure=send_failure=wait_failure=0;
 status_reentrant=gate_entered=gate_open=false;
 atomic_store(&error_count,0);atomic_store(&allocation_calls,0);
}
static void begin(bool located) {
 reset_counters();handle=pdr_handle_alloc(status_cb,NULL);assert(!IS_ERR_OR_NULL(handle));
 service=pdr_add_lookup(handle,"avs/audio","msm/adsp/audio_pd");assert(!IS_ERR_OR_NULL(service));
 if(located) {
  service->need_locator_lookup=false;service->instance=1;
  assert(!pdr_notifier_new_server(&handle->notifier_hdl,&old_peer));
 } else assert(!pdr_locator_new_server(&handle->locator_hdl,&locator_peer));
}
static void finish(void) {
 pdr_handle_release(handle);handle=NULL;service=NULL;assert(!atomic_load(&allocations));
}
static void expect_states(int n,const int *expected) {
 assert(nstate==n);for(int i=0;i<n;i++)assert(states[i]==expected[i]);
}
static void *run_notifier_thread(void *p){run_work(&handle->notifier_work);return NULL;}
static void *release_thread(void *p){pdr_handle_release(handle);return NULL;}
int main(void) {
 int cases=0;const int up[]={SERVREG_SERVICE_STATE_UP};
 const int down[]={SERVREG_SERVICE_STATE_DOWN};
 const int down_up[]={SERVREG_SERVICE_STATE_DOWN,SERVREG_SERVICE_STATE_UP};
 for(int s=0;s<=7;s++) {
  begin(true);scenario=s;status_reentrant=s==0;
  run_work(&handle->notifier_work);
  if(s==3)expect_states(1,down);
  else if(s==4 || s==6)expect_states(2,down_up);
  else expect_states(1,up);
  assert(!atomic_load(&error_count));
  if(s==4)assert(reg_requests==2 && reg_addr[1].sq_node==9 && service->service_connected);
  if(s==5 || s==6)assert(ack_count==(s==5?1:2) && ack_addr[0].sq_node==7);
  finish();cases++;
 }
 begin(true);scenario=13;run_work(&handle->notifier_work);expect_states(1,down);
 assert(!atomic_load(&error_count)&&!service->register_txn);finish();cases++;
 begin(true);scenario=9;run_work(&handle->notifier_work);expect_states(1,down);
 assert(atomic_load(&error_count)==1);finish();cases++;
 begin(true);wait_failure=1;run_work(&handle->notifier_work);expect_states(1,down);
 assert(atomic_load(&error_count)==1);finish();cases++;
 begin(true);send_failure=1;run_work(&handle->notifier_work);expect_states(1,down);finish();cases++;
 begin(true);run_work(&handle->notifier_work);nstate=0;
 indicate(service->addr,SERVREG_SERVICE_STATE_DOWN,22);
 assert(!pdr_notifier_new_server(&handle->notifier_hdl,&new_peer));
 run_work(&handle->indack_work);expect_states(1,down);
 assert(ack_count==1 && ack_addr[0].sq_node==7 && service->addr.sq_node==9);
 run_work(&handle->notifier_work);expect_states(2,down_up);
 indicate((struct sockaddr_qrtr){AF_QIPCRTR,7,100},SERVREG_SERVICE_STATE_DOWN,23);
 assert(list_empty(&handle->indack_list));run_work(&handle->indack_work);
 expect_states(2,down_up);assert(ack_count==1);finish();cases++;
 begin(true);pdr_notifier_del_server(&handle->notifier_hdl,&old_peer);
 pdr_notifier_del_server(&handle->notifier_hdl,&old_peer);
 assert(!pdr_notifier_new_server(&handle->notifier_hdl,&new_peer));
 pdr_notifier_del_server(&handle->notifier_hdl,&old_peer);
 run_work(&handle->notifier_work);expect_states(2,down_up);finish();cases++;
 begin(false);run_work(&handle->locator_work);assert(service->instance==1&&!service->need_locator_lookup);
 assert(!pdr_notifier_new_server(&handle->notifier_hdl,&old_peer));
 run_work(&handle->notifier_work);expect_states(1,up);finish();cases++;
 begin(false);scenario=10;run_work(&handle->locator_work);
 assert(locator_requests==1&&service->need_locator_lookup&&!service->lookup_failed&&nstate==0);
 scenario=0;run_work(&handle->locator_work);assert(locator_requests==2&&!service->need_locator_lookup);
 finish();cases++;
 begin(false);scenario=11;run_work(&handle->locator_work);
 assert(service->need_locator_lookup&&service->instance!=999);
 run_work(&handle->locator_work);assert(!service->need_locator_lookup&&service->instance==1);
 pdr_locator_del_server(&handle->locator_hdl,&locator_peer);assert(handle->locator_init_complete);
 finish();cases++;
 begin(false);send_failure=1;run_work(&handle->locator_work);
 assert(service->lookup_failed && !list_empty(&handle->retired) && nstate==1);
 assert(states[0]==SERVREG_LOCATOR_ERR);
 struct pdr_service *replacement=pdr_add_lookup(handle,"avs/audio","msm/adsp/audio_pd");
 assert(!IS_ERR_OR_NULL(replacement)&&replacement!=service);
 assert(pdr_restart_pd(handle,service)==-EINVAL);finish();cases++;
 begin(true);indicate(service->addr,SERVREG_SERVICE_STATE_DOWN,24);
 pdr_notify_lookup_failure(handle,service,-EIO);
 assert(service->lookup_failed);run_work(&handle->indack_work);
 assert(nstate==1&&states[0]==SERVREG_LOCATOR_ERR&&ack_count==1);finish();cases++;
 begin(true);assert(PTR_ERR(pdr_add_lookup(handle,"avs/audio","msm/adsp/audio_pd"))==-EALREADY);
 assert(pdr_restart_pd(handle,service)==0);scenario=12;
 assert(pdr_restart_pd(handle,service)==-EOPNOTSUPP);send_failure=1;
 assert(pdr_restart_pd(handle,service)==-EIO);send_failure=0;wait_failure=1;
 assert(pdr_restart_pd(handle,service)==-ETIMEDOUT);finish();cases++;
 begin(true);scenario=8;pthread_t notifier,releaser;
 assert(!pthread_create(&notifier,NULL,run_notifier_thread,NULL));
 assert(!pthread_mutex_lock(&gate_lock));while(!gate_entered)assert(!pthread_cond_wait(&gate_cond,&gate_lock));
 assert(!pthread_mutex_unlock(&gate_lock));assert(!pthread_create(&releaser,NULL,release_thread,NULL));
 struct timespec tick={0,1000000};int spins=0;
 while(!READ_ONCE(handle->stopping)){assert(spins++<1000);nanosleep(&tick,NULL);}
 assert(pdr_notifier_new_server(&handle->notifier_hdl,&new_peer)==-ESHUTDOWN);
 pdr_notifier_del_server(&handle->notifier_hdl,&old_peer);
 indicate((struct sockaddr_qrtr){AF_QIPCRTR,7,100},SERVREG_SERVICE_STATE_DOWN,25);
 assert(PTR_ERR(pdr_add_lookup(handle,"new","new"))==-ESHUTDOWN);
 assert(pdr_restart_pd(handle,service)==-ESHUTDOWN);
 assert(!pthread_mutex_lock(&gate_lock));gate_open=true;assert(!pthread_cond_broadcast(&gate_cond));
 assert(!pthread_mutex_unlock(&gate_lock));assert(!pthread_join(notifier,NULL));
 assert(!pthread_join(releaser,NULL));handle=NULL;assert(nstate==0&&!atomic_load(&allocations));cases++;
 for(int n=1;n<=3;n++) {
  reset_counters();allocation_failure=n;struct pdr_handle *failed=pdr_handle_alloc(status_cb,NULL);
  assert(IS_ERR_OR_NULL(failed)&&!atomic_load(&allocations));cases++;
 }
 for(int n=1;n<=2;n++) {
  reset_counters();qmi_init_failure=n;struct pdr_handle *failed=pdr_handle_alloc(status_cb,NULL);
  assert(IS_ERR_OR_NULL(failed)&&!atomic_load(&allocations));cases++;
 }
 reset_counters();add_lookup_failure=1;struct pdr_handle *failed=pdr_handle_alloc(status_cb,NULL);
 assert(IS_ERR_OR_NULL(failed)&&!atomic_load(&allocations));cases++;
 printf("{\"cases\":%d,\"all_passed\":true,\"actual_full_pdr_source\":true}\n",cases);
 return 0;
}
'''

code = prefix + protocol + ei_defs + actual + suffix
variants = {
    'current': code,
    'negative-generation': code.replace('pds->server_generation == generation && pds->state_sequence == sequence', 'true'),
    'negative-peer-delete': code.replace('!pds->service_connected || pds->addr.sq_node != svc->node ||\n\t\t\t    pds->addr.sq_port != svc->port', '!pds->service_connected'),
    'negative-ack-new-peer': code.replace('pdr_send_indack_msg(pdr, pds, &ind->addr, ind->transaction_id)', 'pdr_send_indack_msg(pdr, pds, &pds->addr, ind->transaction_id)'),
    'negative-free-retired': code.replace('list_move_tail(&pds->node, &pdr->retired);', 'list_del(&pds->node); kfree(pds);'),
    'negative-release-before-wait': code.replace('/* Keep QMI RX alive until every in-flight transaction has finished. */',
                                               'qmi_handle_release(&pdr->notifier_hdl);'),
    'negative-no-transaction-cancel': code.replace('txn->result = -ENETRESET;\n\tcomplete(&txn->completion);', '(void)txn;'),
}
results = {}
for name, text in variants.items():
    if name != 'current':
        assert text != code, name
    cpath, exe = out / (name + '.c'), out / name
    cpath.write_text(text)
    build = subprocess.run(['gcc', '-std=gnu11', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                            '-Wno-unused-parameter', '-Wno-sign-compare', '-Wno-unused-function',
                            '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-pthread',
                            str(cpath), '-o', str(exe)], capture_output=True, text=True)
    (out / (name + '-build-private.log')).write_text(build.stdout + build.stderr)
    assert build.returncode == 0 and not build.stderr, build.stderr
    try:
        result = subprocess.run([str(exe)], capture_output=True, text=True, timeout=12)
        (out / (name + '-run-private.log')).write_text(result.stdout + result.stderr)
        if name == 'current':
            assert result.returncode == 0 and not result.stderr, result.stderr
            results[name] = json.loads(result.stdout)
        else:
            assert result.returncode != 0, name
            results[name] = {'rejected': True, 'exit_code': result.returncode}
    except subprocess.TimeoutExpired:
        assert name != 'current'
        results[name] = {'rejected': True, 'bounded_timeout_seconds': 12}

report = {'stage': 180, 'actual_pdr_source_sha256': hashlib.sha256(source.encode()).hexdigest(),
          'actual_protocol_headers_used': True, 'transport_and_workqueue_are_host_adapters': True,
          'mock_wait_ms': 300, 'kernel_wait_seconds': 5, 'results': results,
          'all_passed': True, 'sanitizers': ['address', 'undefined']}
(ref / 'pdr-host-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
