"""Execute complete candidate C functions with only kernel/PSY boundaries mocked."""
from pathlib import Path
import hashlib,json,os,re,subprocess,tempfile
HERE=Path(__file__).resolve().parent
NAMES={
 'qcom_pmic_typec_port.c':['qcom_pmic_typec_port_get_current_limit','qcom_pmic_typec_port_get_usb_supply'],
 'tcpm.c':['tcpm_get_current_limit','tcpm_set_current_limit','tcpm_psy_external_power_changed','tcpm_unregister_port']}
def function(text,name):
    m=re.search(r'(?m)^(?:static )?(?:int|u32|void) '+name+r'\(',text)
    assert m,name
    start=text.index('{',m.start());depth=1;end=start+1
    while depth:
        depth+=(text[end]=='{')-(text[end]=='}');end+=1
    return text[m.start():end]+'\n'
chunks=[function((HERE/file).read_text(),name) for file,names in NAMES.items() for name in names]
prefix=r'''
#include <assert.h>
#include <errno.h>
#include <limits.h>
#include <pthread.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
typedef uint32_t u32;
enum typec_cc_status {TYPEC_CC_OPEN,TYPEC_CC_RA,TYPEC_CC_RD,TYPEC_CC_RP_DEF,TYPEC_CC_RP_1_5,TYPEC_CC_RP_3_0};
enum { SNK_READY=7, SNK_NEGOTIATE_CAPABILITIES, TYPEC_SINK=0, TYPEC_SOURCE=1 };
enum { POWER_SUPPLY_PROP_ONLINE,POWER_SUPPLY_PROP_CURRENT_MAX };
#define EPROBE_DEFER 517
#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))
#define min(a,b) ((a)<(b)?(a):(b))
#define tcpc_to_tcpm(p) ((struct pmic_typec *)((char *)(p)-offsetof(struct pmic_typec,tcpc)))
#define IS_ERR(p) ((uintptr_t)(p)>=(uintptr_t)-4095)
#define PTR_ERR(p) ((int)(intptr_t)(p))
#define ERR_PTR(e) ((void *)(intptr_t)(e))
#define tcpm_log(...) ((void)0)
struct device { bool property; };
union power_supply_propval { int intval; };
struct power_supply { void *data; };
struct tcpc_dev {int (*get_current_limit)(struct tcpc_dev *);int (*set_current_limit)(struct tcpc_dev *,u32,u32);};
struct pmic_typec_port {struct power_supply *usb_psy;};
struct pmic_typec {struct tcpc_dev tcpc;struct pmic_typec_port *pmic_typec_port;bool samurai_fixed_5v;};
struct tcpm_port {
 struct tcpc_dev *tcpc;struct power_supply *psy;pthread_mutex_t lock;
 bool registered,attached,vbus_present,pd_capable,explicit_contract,polarity;
 enum typec_cc_status cc1,cc2;int state,pwr_role;u32 current_limit,supply_voltage;
 void *wq,*fixed_batt,*port_altmode[2],*typec_port,*role_sw;
 int fixed_batt_cnt,vdm_discovery_timer,enable_frs_timer,vdm_state_machine_timer,state_machine_timer;
};
static int online,current_ua,online_error,current_error,reads,notices,ref_calls;
static struct power_supply *ref_result;
static bool gate_callback,callback_entered,release_callback;
static pthread_mutex_t gate_lock=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t gate_cond=PTHREAD_COND_INITIALIZER;
static void *power_supply_get_drvdata(struct power_supply *p){return p->data;}
static int power_supply_get_property(struct power_supply *p,int prop,union power_supply_propval *v){
 assert(p);reads++;
 if(gate_callback && prop==POWER_SUPPLY_PROP_CURRENT_MAX){
  pthread_mutex_lock(&gate_lock);callback_entered=true;pthread_cond_broadcast(&gate_cond);
  while(!release_callback)pthread_cond_wait(&gate_cond,&gate_lock);
  pthread_mutex_unlock(&gate_lock);
 }
 if(prop==POWER_SUPPLY_PROP_ONLINE){v->intval=online;return online_error;}
 assert(prop==POWER_SUPPLY_PROP_CURRENT_MAX);v->intval=current_ua;return current_error;
}
static bool device_property_present(struct device *d,const char *p){assert(!strcmp(p,"power-supplies"));return d->property;}
static struct power_supply *devm_power_supply_get_by_reference(struct device *d,const char *p){
 assert(d->property&&!strcmp(p,"power-supplies"));ref_calls++;return ref_result;
}
static void power_supply_changed(struct power_supply *p){assert(p);notices++;}
static void mutex_lock(pthread_mutex_t *p){assert(!pthread_mutex_lock(p));}
static void mutex_unlock(pthread_mutex_t *p){assert(!pthread_mutex_unlock(p));}
static struct tcpm_port *joining;
static void tcpm_psy_external_power_changed(struct power_supply *p);
static void kthread_destroy_worker(void *p){
 assert(p&&joining&&!joining->registered);
 int before=reads;tcpm_psy_external_power_changed(joining->psy);assert(reads==before);
}
static void hrtimer_cancel(int *p){(void)p;}
static void power_supply_put_system_batteries(void *p,int n){(void)p;(void)n;}
static void tcpm_reset_port(struct tcpm_port *p){assert(!p->registered);}
static void tcpm_port_unregister_pd(struct tcpm_port *p){assert(!p->registered);}
static void typec_unregister_altmode(void *p){(void)p;}
static void typec_unregister_port(void *p){(void)p;}
static void usb_role_switch_put(void *p){(void)p;}
static void tcpm_debugfs_exit(struct tcpm_port *p){assert(!p->registered);}
'''
suffix=r'''
static struct pmic_typec pm;static struct pmic_typec_port qp;
static struct power_supply usb,psy;static struct tcpm_port tp;
static void init(void){
 online=1;current_ua=500000;online_error=current_error=reads=notices=ref_calls=0;
 pm=(struct pmic_typec){.pmic_typec_port=&qp,.samurai_fixed_5v=true};
 qp.usb_psy=&usb;pm.tcpc.get_current_limit=qcom_pmic_typec_port_get_current_limit;
 ref_result=&usb;psy.data=&tp;
 tp=(struct tcpm_port){.tcpc=&pm.tcpc,.psy=&psy,.registered=true,.attached=true,
  .vbus_present=true,.state=SNK_READY,.pwr_role=TYPEC_SINK,.cc1=TYPEC_CC_RP_DEF,
  .current_limit=0,.supply_voltage=5000,.wq=&usb};
 assert(!pthread_mutex_init(&tp.lock,NULL));
}
static void done(void){assert(!pthread_mutex_destroy(&tp.lock));}
static void test_permissions(void){
 init();assert(qcom_pmic_typec_port_get_current_limit(&pm.tcpc)==500);
 current_ua=100000;assert(qcom_pmic_typec_port_get_current_limit(&pm.tcpc)==100);
 current_ua=2500;assert(qcom_pmic_typec_port_get_current_limit(&pm.tcpc)==2);
 current_ua=0;assert(qcom_pmic_typec_port_get_current_limit(&pm.tcpc)==0);
 current_ua=-1;assert(qcom_pmic_typec_port_get_current_limit(&pm.tcpc)==0);
 current_ua=3000000;assert(qcom_pmic_typec_port_get_current_limit(&pm.tcpc)==500);
 pm.samurai_fixed_5v=false;assert(qcom_pmic_typec_port_get_current_limit(&pm.tcpc)==3000);
 current_ua=INT_MAX;assert(qcom_pmic_typec_port_get_current_limit(&pm.tcpc)==INT_MAX/1000);
 online=0;assert(qcom_pmic_typec_port_get_current_limit(&pm.tcpc)==0);
 online=2;assert(qcom_pmic_typec_port_get_current_limit(&pm.tcpc)==0);
 online=1;online_error=-EIO;assert(qcom_pmic_typec_port_get_current_limit(&pm.tcpc)==0);
 online_error=0;current_error=-ENODATA;assert(qcom_pmic_typec_port_get_current_limit(&pm.tcpc)==0);done();
}
static void test_supply_binding(void){
 init();struct device d={0};pm.tcpc.get_current_limit=NULL;qp.usb_psy=NULL;
 assert(!qcom_pmic_typec_port_get_usb_supply(&d,&pm));assert(!ref_calls&&!pm.tcpc.get_current_limit);
 d.property=true;ref_result=NULL;assert(qcom_pmic_typec_port_get_usb_supply(&d,&pm)==-EPROBE_DEFER);
 for(int i=0;i<3;i++){int e=(int[]){-EPROBE_DEFER,-EIO,-ENOMEM}[i];ref_result=ERR_PTR(e);
  assert(qcom_pmic_typec_port_get_usb_supply(&d,&pm)==e);assert(!qp.usb_psy&&!pm.tcpc.get_current_limit);}
 ref_result=&usb;assert(!qcom_pmic_typec_port_get_usb_supply(&d,&pm));
 assert(qp.usb_psy==&usb&&pm.tcpc.get_current_limit==qcom_pmic_typec_port_get_current_limit);done();
}
static void test_native_transitions(void){
 init();tcpm_psy_external_power_changed(&psy);assert(tp.current_limit==500&&notices==1);
 tcpm_psy_external_power_changed(&psy);assert(notices==1);
 current_ua=100000;tcpm_psy_external_power_changed(&psy);assert(tp.current_limit==100&&notices==2);
 current_ua=0;tcpm_psy_external_power_changed(&psy);assert(tp.current_limit==0&&notices==3);
 current_ua=500000;tcpm_psy_external_power_changed(&psy);assert(tp.current_limit==500&&notices==4);
 current_error=-EIO;tcpm_psy_external_power_changed(&psy);assert(!tp.current_limit&&notices==5);
 assert(tp.supply_voltage==5000);done();
}
static void assert_ignored(void){int r=reads,n=notices;tcpm_psy_external_power_changed(&psy);assert(reads==r&&notices==n);}
static void test_contracts_and_states(void){
 init();tp.pd_capable=true;assert_ignored();tp.pd_capable=false;
 tp.explicit_contract=true;assert_ignored();tp.explicit_contract=false;
 tp.state=SNK_NEGOTIATE_CAPABILITIES;assert_ignored();tp.state=SNK_READY;
 tp.pwr_role=TYPEC_SOURCE;assert_ignored();tp.pwr_role=TYPEC_SINK;
 tp.attached=false;assert_ignored();tp.attached=true;tp.vbus_present=false;assert_ignored();tp.vbus_present=true;
 tp.registered=false;assert_ignored();tp.registered=true;
 pm.tcpc.get_current_limit=NULL;assert_ignored();pm.tcpc.get_current_limit=qcom_pmic_typec_port_get_current_limit;
 tp.cc1=TYPEC_CC_OPEN;assert_ignored();tp.cc1=TYPEC_CC_RP_3_0;assert_ignored();
 tp.cc2=TYPEC_CC_RP_DEF;tp.polarity=true;tcpm_psy_external_power_changed(&psy);assert(tp.current_limit==500);
 assert(tcpm_get_current_limit(&tp)==500);tp.polarity=false;
 assert(tcpm_get_current_limit(&tp)==3000);tp.cc1=TYPEC_CC_RP_1_5;assert(tcpm_get_current_limit(&tp)==1500);done();
}
static void *callback_thread(void *p){tcpm_psy_external_power_changed(p);return NULL;}
static void *unregister_thread(void *p){tcpm_unregister_port(p);return NULL;}
static void test_unregister_joins_callback(void){
 init();gate_callback=true;callback_entered=false;release_callback=false;joining=&tp;
 pthread_t a,b;assert(!pthread_create(&a,NULL,callback_thread,&psy));
 pthread_mutex_lock(&gate_lock);while(!callback_entered)pthread_cond_wait(&gate_cond,&gate_lock);pthread_mutex_unlock(&gate_lock);
 assert(!pthread_create(&b,NULL,unregister_thread,&tp));
 pthread_mutex_lock(&gate_lock);release_callback=true;pthread_cond_broadcast(&gate_cond);pthread_mutex_unlock(&gate_lock);
 assert(!pthread_join(a,NULL));assert(!pthread_join(b,NULL));
 assert(!tp.registered&&!tp.wq&&tp.current_limit==500);assert_ignored();gate_callback=false;done();
}
int main(void){test_permissions();test_supply_binding();test_native_transitions();test_contracts_and_states();test_unregister_joins_callback();puts("five groups passed");return 0;}
'''
with tempfile.TemporaryDirectory(prefix='tcpm-usb-budget-') as temp:
    p=Path(temp);(p/'test.c').write_text(prefix+'\n'.join(chunks)+suffix)
    # The unchanged kernel unregister loop uses int with ARRAY_SIZE, as in
    # the real kernel's warning profile. Do not rewrite that function for a test.
    argv=['cc','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-sign-compare','-pthread',
          '-fsanitize=address,undefined','-g',str(p/'test.c'),'-o',str(p/'test')]
    c=subprocess.run(argv,capture_output=True,text=True)
    assert c.returncode==0,c.stderr
    c=subprocess.run([str(p/'test')],capture_output=True,text=True,timeout=20,
        env={**os.environ,'ASAN_OPTIONS':'detect_leaks=1:abort_on_error=1','UBSAN_OPTIONS':'halt_on_error=1'})
    result={'passed':c.returncode==0,'groups':5,'complete_candidate_functions':NAMES,
            'source_sha256':{p:hashlib.sha256((HERE/p).read_bytes()).hexdigest() for p in NAMES},
            'compiler':'cc -Wall -Wextra -Werror -pthread -fsanitize=address,undefined',
            'stdout':c.stdout,'stderr':c.stderr,'returncode':c.returncode,
            'scope':'PSY/device/kernel lifecycle boundaries mocked; real pthread callback/unregister synchronization',
            'phone_accessed':False,'installed':False}
    (HERE/'test-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result));raise SystemExit(c.returncode)
