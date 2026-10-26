"""Run complete production functions with scheduler/ADC/device boundaries modeled."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess

HERE = Path(__file__).resolve().parent
SRC = (HERE / "tcpm.c").read_text()


def function(source, name):
    m = re.search(r"^(?:static )?(?:int|void|bool) " + name + r"\([^;]*?\)\n\{", source, re.M)
    assert m, name
    end, depth = m.end(), 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[m.start():end] + "\n"


NAMES = ["tcpm_shutdown_5v_complete", "tcpm_shutdown_state_change", "tcpm_set_state",
         "tcpm_ams_start", "tcpm_pd_select_pdo", "tcpm_pd_build_request",
         "tcpm_pd_send_request", "tcpm_pd_send_aug_supply_request", "tcpm_set_current_limit",
         "tcpm_pd_ctrl_request", "tcpm_pps_activate", "tcpm_port_type_set",
         "tcpm_shutdown_contract_valid", "tcpm_prepare_sink_shutdown"]
functions = "\n".join(function(SRC, n) for n in NAMES)
states = re.findall(r"S\((\w+)\)", SRC[SRC.index("#define FOREACH_STATE"):SRC.index("#define FOREACH_AMS")])
controls = sorted(set(re.findall(r"\bPD_CTRL_\w+", functions)))
messages = sorted(set(re.findall(r"\bPD_MSG_\w+", functions)))
enums = ("enum tcpm_state {" + ",".join(states) + "};\n" +
         "enum pd_ctrl_msg_type {" + ",".join(controls) + "};\n" +
         "enum {" + ",".join(messages) + "};\n")
prefix = r'''
#include <assert.h>
#include <errno.h>
#include <pthread.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uint32_t u32;
typedef uint64_t u64;
enum pd_pdo_type {PDO_TYPE_FIXED,PDO_TYPE_BATT,PDO_TYPE_VAR,PDO_TYPE_APDO};
enum aug_req_type {PD_PPS,PD_SPR_AVS};
enum tcpm_transmit_type {TCPC_TX_SOP,TCPC_TX_SOP_PRIME,TCPC_TX_HARD_RESET};
enum typec_cc_status {TYPEC_CC_OPEN,TYPEC_CC_RD,TYPEC_CC_RP_DEF};
enum tcpm_ams {NONE_AMS,POWER_NEGOTIATION,HARD_RESET,SOFT_RESET_AMS,
 GET_SOURCE_CAPABILITIES,GET_SINK_CAPABILITIES,DATA_ROLE_SWAP,POWER_ROLE_SWAP,
 VCONN_SWAP,REVISION_INFORMATION,GETTING_SINK_EXTENDED_CAPABILITIES};
enum typec_port_type {TYPEC_PORT_SNK,TYPEC_PORT_SRC,TYPEC_PORT_DRP};
enum {TYPEC_PORT_UFP,TYPEC_PORT_DFP,TYPEC_PORT_DRD};
enum {TYPEC_SINK,TYPEC_SOURCE,TYPEC_DEVICE,TYPEC_HOST};
enum {POWER_SUPPLY_USB_TYPE_PD,POWER_SUPPLY_USB_TYPE_PD_PPS,POWER_SUPPLY_USB_TYPE_PD_SPR_AVS,
 POWER_SUPPLY_USB_TYPE_PD_PPS_SPR_AVS};
enum {SPR_AVS_UNKNOWN,SPR_AVS_NOT_SUPPORTED,SPR_AVS_SUPPORTED};
enum {VDM_STATE_ERR_BUSY,VDM_STATE_READY,VDM_STATE_DONE};
enum {VDM_DISCOVERY_UNKNOWN,TYPEC_PWR_MODE_PD,TYPEC_PWR_MODE_USB};
enum {PD_REV20=1,PD_REV30=2};
#define APDO_TYPE_PPS 0
#define APDO_TYPE_SPR_AVS 1
#define PD_DATA_REQUEST 2
#define PD_T_SINK_TX 16
#define PD_AUG_PSY_CTRL_TIMEOUT 10000
#define SINK_TX_OK 1
#define SINK_TX_NG 0
#define RDO_USB_COMM (1U << 25)
#define RDO_NO_SUSPEND (1U << 24)
#define RDO_CAP_MISMATCH (1U << 26)
#define RDO_FIXED(i,op,max,flags) (((i)<<28)|((op)/10<<10)|((max)/10)|(flags))
#define RDO_BATT(i,op,max,flags) (((i)<<28)|((op)/250<<10)|((max)/250)|(flags))
#define PDO_FIXED(mv,ma) (((mv)/50<<10)|((ma)/10))
#define pdo_type(p) ((enum pd_pdo_type)((p)>>30))
#define pdo_fixed_voltage(p) ((((p)>>10)&1023)*50)
#define pdo_max_voltage(p) ((((p)>>20)&1023)*50)
#define pdo_min_voltage(p) ((((p)>>10)&1023)*50)
#define pdo_max_current(p) (((p)&1023)*10)
#define pdo_max_power(p) (((p)&1023)*250)
#define pdo_apdo_type(p) (((p)>>28)&3)
#define min(x,y) ((x)<(y)?(x):(y))
#define min_power(x,y) min(pdo_max_power(x),pdo_max_power(y))
#define min_current(x,y) min(pdo_max_current(x),pdo_max_current(y))
#define cpu_to_le32(x) (x)
#define PD_HEADER_LE(t,p,d,r,m,n) (t)
#define pd_header_type_le(h) (h)
#define pd_header_rev_le(h) PD_REV20
#define tcpm_log(...) ((void)0)
#define EXPORT_SYMBOL_GPL(x)
#define fallthrough __attribute__((fallthrough))
#define TCPM_SHUTDOWN_MIN_UV 4750000
#define TCPM_SHUTDOWN_MAX_UV 5500000
#define TCPM_SHUTDOWN_SAMPLES 3
#define TCPM_SHUTDOWN_SAMPLE_MS 20
struct completion {int done;};
struct pd_message {int header;u32 payload[7];};
struct tcpc_dev {int (*get_vbus_voltage)(void *,int *);
 int (*set_current_limit)(struct tcpc_dev *,u32,u32);};
struct typec_port {void *data;};
struct tcpm_port {
 struct tcpc_dev *tcpc;
 pthread_mutex_t lock,swap_lock;
 bool shutdown_5v,shutdown_busy,shutdown_5v_pending,shutdown_5v_accepted;
 int shutdown_5v_status;u64 shutdown_sequence;
 struct completion shutdown_5v_complete,aug_supply_req_complete;
 bool registered,connected,vbus_present,explicit_contract,pd_capable,vdm_sm_running,
      state_machine_running,in_ams,aug_supply_req_pending;
 enum tcpm_state state,prev_state,delayed_state,upcoming_state;
 enum tcpm_ams ams;
 enum typec_port_type port_type;
 struct {int data;} typec_caps;
 struct {bool active,supported;u32 req_out_volt,req_op_curr,min_volt,max_volt,max_curr,
    req_min_volt,req_max_volt,req_max_curr;} pps_data;
 struct {bool active;int port_snk_status,port_partner_src_status;
    u32 port_snk_pdo_index,port_partner_src_pdo_index,req_out_volt_mv,req_op_curr_ma;} spr_avs_data;
 struct {int rev_major;} pd_rev;
 int pwr_role,data_role,negotiated_rev,negotiated_rev_prime,cc_req,cc1,cc2,vconn_role,
     polarity,vdm_state,vdm_discovery_state,swap_status,aug_supply_req_status,usb_type;
 bool vbus_source,sink_cap_done;
 u32 source_caps[7],snk_pdo[7],nr_source_caps,nr_snk_pdo,operating_snk_mw,
     supply_voltage,current_limit,req_supply_voltage,req_current_limit,message_id;
 unsigned int delay_ms;unsigned long delayed_runtime;void *psy;
};
static unsigned long jiffies;
static unsigned long msecs_to_jiffies(unsigned int n){return n;}
#define time_after_eq(a,b) ((long)((a)-(b))>=0)
#define time_before(a,b) ((long)((a)-(b))<0)
#define ktime_add(a,b) ((a)+(b))
#define ms_to_ktime(a) (a)
static unsigned long ktime_get(void){return jiffies;}
static void mutex_lock(pthread_mutex_t *p){assert(!pthread_mutex_lock(p));}
static void mutex_unlock(pthread_mutex_t *p){assert(!pthread_mutex_unlock(p));}
static void reinit_completion(struct completion *c){c->done=0;}
static void complete(struct completion *c){c->done=1;}
static void msleep(unsigned int n){jiffies+=n;}
static unsigned long wait_for_completion_timeout(struct completion *,unsigned long);
static int tcpm_pd_send_request(struct tcpm_port *);
static void tcpm_pd_ctrl_request(struct tcpm_port *,const struct pd_message *,enum tcpm_transmit_type);
static void tcpm_shutdown_5v_complete(struct tcpm_port *,int);
static void tcpm_set_state(struct tcpm_port *,enum tcpm_state,unsigned int);
static int tcpm_ams_start(struct tcpm_port *,enum tcpm_ams);
static int tcpm_pps_activate(struct tcpm_port *,bool);
static bool tcpm_ams_interruptible(struct tcpm_port *p){return p->ams==NONE_AMS;}
static bool tcpm_vdm_ams(struct tcpm_port *p){(void)p;return false;}
static bool sink_tx_ok=true;
static bool tcpm_sink_tx_ok(struct tcpm_port *p){(void)p;return sink_tx_ok;}
static int transmit_error,transmits,aug_builds,limit_error;
static u32 sent_rdo;
static int tcpm_pd_transmit(struct tcpm_port *p,enum tcpm_transmit_type type,const struct pd_message *m){
 (void)type;assert(p->shutdown_5v);transmits++;if(m)sent_rdo=m->payload[0];return transmit_error;}
static void tcpm_set_cc(struct tcpm_port *p,int v){(void)p;(void)v;}
static int tcpm_rp_cc(struct tcpm_port *p){(void)p;return 0;}
static void mod_tcpm_delayed_work(struct tcpm_port *p,unsigned int n){(void)p;(void)n;}
static void mod_vdm_delayed_work(struct tcpm_port *p,unsigned int n){(void)p;(void)n;}
static void tcpm_ams_finish(struct tcpm_port *p){p->ams=NONE_AMS;}
static void power_supply_changed(void *p){(void)p;}
static int tcpm_set_auto_vbus_discharge_threshold(struct tcpm_port *p,int a,bool b,u32 c){
 (void)p;(void)a;(void)b;(void)c;return 0;}
static int tcpm_pd_build_pps_request(struct tcpm_port *p,u32 *v){(void)p;(void)v;aug_builds++;return -EINVAL;}
static int tcpm_pd_build_spr_avs_request(struct tcpm_port *p,u32 *v){(void)p;(void)v;aug_builds++;return -EINVAL;}
static enum tcpm_state ready_state(struct tcpm_port *p){(void)p;return SNK_READY;}
static void tcpm_pd_handle_state(struct tcpm_port *p,enum tcpm_state s,enum tcpm_ams a,unsigned int n){
 (void)a;tcpm_set_state(p,s,n);}
static void tcpm_pd_handle_msg(struct tcpm_port *p,int m,enum tcpm_ams a){(void)p;(void)m;(void)a;}
static void tcpm_queue_message(struct tcpm_port *p,int m){(void)p;(void)m;}
static void *typec_get_drvdata(struct typec_port *p){return p->data;}
'''
suffix = r'''
enum scenario {SUCCESS,REJECTED,WAITED,NO_RESPONSE,ACCEPT_ONLY,PSRDY_ONLY,RESET,CABLE_MESSAGES};
static enum scenario scenario;
static struct tcpm_port port;
static struct tcpc_dev tcpc;
static int read_count,read_error,uvs[16],uv_count,change_at,overrun_at;
static bool test_mutator;
static void ctrl(int type){struct pd_message m={.header=type};tcpm_pd_ctrl_request(&port,&m,TCPC_TX_SOP);}
static unsigned long wait_for_completion_timeout(struct completion *c,unsigned long timeout){
 if(c==&port.aug_supply_req_complete){assert(0);}
 mutex_lock(&port.lock);
 assert(port.shutdown_5v&&port.shutdown_5v_pending);
 port.upcoming_state=INVALID_STATE;
 tcpm_set_state(&port,SNK_NEGOTIATE_CAPABILITIES,0);
 int r=tcpm_pd_send_request(&port);
 if(r)tcpm_shutdown_5v_complete(&port,r);
 else if(scenario==REJECTED)ctrl(PD_CTRL_REJECT);
 else if(scenario==WAITED)ctrl(PD_CTRL_WAIT);
 else if(scenario==RESET)tcpm_set_state(&port,HARD_RESET_START,0);
 else if(scenario==PSRDY_ONLY)ctrl(PD_CTRL_PS_RDY);
 else if(scenario==CABLE_MESSAGES){
  struct pd_message m={.header=PD_CTRL_ACCEPT};tcpm_pd_ctrl_request(&port,&m,TCPC_TX_SOP_PRIME);
  m.header=PD_CTRL_PS_RDY;tcpm_pd_ctrl_request(&port,&m,TCPC_TX_SOP_PRIME);
 }
 else if(scenario!=NO_RESPONSE){
  ctrl(PD_CTRL_ACCEPT);assert(port.shutdown_5v_accepted&&port.shutdown_5v_pending);
  if(scenario!=ACCEPT_ONLY){ctrl(PD_CTRL_PS_RDY);port.ams=NONE_AMS;}
 }
 if(port.state==SNK_READY)port.ams=NONE_AMS;
 mutex_unlock(&port.lock);
 if(c->done)return 1;
 jiffies+=timeout;return 0;
}
static int read_vbus(void *d,int *uv){
 assert(d==&tcpc);
 // A callback which re-enters TCPM must not deadlock on either mutex.
 assert(!pthread_mutex_trylock(&port.lock));mutex_unlock(&port.lock);
 assert(!pthread_mutex_trylock(&port.swap_lock));mutex_unlock(&port.swap_lock);
 read_count++;
 if(test_mutator){assert(tcpm_pps_activate(&port,true)==-ESHUTDOWN);
  struct typec_port t={.data=&port};assert(tcpm_port_type_set(&t,TYPEC_PORT_DRP)==-ESHUTDOWN);}
 if(change_at==read_count){mutex_lock(&port.lock);tcpm_set_state(&port,SNK_READY,0);mutex_unlock(&port.lock);}
 if(overrun_at==read_count)jiffies+=1000;
 *uv=uvs[min(read_count-1,uv_count-1)];return read_error;
}
static int set_limit(struct tcpc_dev *d,u32 ma,u32 mv){(void)d;(void)ma;(void)mv;return limit_error;}
static void init(bool pd){
 jiffies=1;transmit_error=transmits=aug_builds=limit_error=0;sent_rdo=0;sink_tx_ok=true;
 read_count=read_error=change_at=overrun_at=0;uv_count=1;uvs[0]=5000000;scenario=SUCCESS;test_mutator=true;
 tcpc=(struct tcpc_dev){.get_vbus_voltage=read_vbus};
 port=(struct tcpm_port){.tcpc=&tcpc,.registered=true,.connected=true,.vbus_present=true,
  .explicit_contract=pd,.pd_capable=pd,.pwr_role=TYPEC_SINK,.state=SNK_READY,.ams=NONE_AMS,
  .upcoming_state=INVALID_STATE,.port_type=TYPEC_PORT_SNK,.typec_caps.data=TYPEC_PORT_UFP,
  .nr_source_caps=3,.nr_snk_pdo=2,.operating_snk_mw=2500,
  .supply_voltage=pd?9000:5000,.current_limit=1000,.negotiated_rev=PD_REV20};
 port.source_caps[0]=PDO_FIXED(5000,3000);port.source_caps[1]=PDO_FIXED(9000,3000);
 port.source_caps[2]=3U<<30;port.snk_pdo[0]=PDO_FIXED(5000,1000);port.snk_pdo[1]=PDO_FIXED(9000,3000);
 assert(!pthread_mutex_init(&port.lock,NULL));assert(!pthread_mutex_init(&port.swap_lock,NULL));
}
static void done(void){assert(!pthread_mutex_destroy(&port.lock));assert(!pthread_mutex_destroy(&port.swap_lock));}
static void assert_sealed(void){
 assert(port.shutdown_5v&&!port.shutdown_busy&&!port.shutdown_5v_pending);
 assert(tcpm_pd_send_aug_supply_request(&port,PD_PPS)==-ESHUTDOWN);
 assert(tcpm_pd_send_aug_supply_request(&port,PD_SPR_AVS)==-ESHUTDOWN);assert(!aug_builds);
}
static int prepare(struct tcpm_port *p,unsigned int ms){
 return tcpm_prepare_sink_shutdown(p,ms,tcpc.get_vbus_voltage,&tcpc);
}
static void test_request_and_measurement(void){
 init(true);int sk=0,sr=0;
 assert(!tcpm_pd_select_pdo(&port,&sk,&sr)&&sr==1);
 u32 original[7];memcpy(original,port.source_caps,sizeof original);
 port.pps_data.active=true;port.pps_data.supported=true;
 assert(!prepare(&port,200));
 assert(transmits==1&&sent_rdo>>28==1&&((sent_rdo>>10)&1023)*10==1000);
 assert(read_count==3&&port.supply_voltage==5000&&port.shutdown_5v_accepted);
 assert(!port.pps_data.active&&!memcmp(original,port.source_caps,sizeof original));assert_sealed();done();
 init(false);assert(!prepare(&port,200));assert(!transmits&&read_count==3);assert_sealed();done();
}
static void test_protocol_failures(void){
 const enum scenario modes[]={REJECTED,WAITED,NO_RESPONSE,ACCEPT_ONLY,PSRDY_ONLY,RESET,CABLE_MESSAGES};
 const int errors[]={-EOPNOTSUPP,-EAGAIN,-ETIMEDOUT,-ETIMEDOUT,-EPROTO,-EPROTO,-ETIMEDOUT};
 for(unsigned i=0;i<sizeof modes/sizeof modes[0];i++){
  init(true);scenario=modes[i];assert(prepare(&port,100)==errors[i]);
  assert(!read_count);assert_sealed();done();
 }
 init(true);transmit_error=-EIO;assert(prepare(&port,100)==-EIO);assert(!read_count);assert_sealed();done();
 init(true);port.source_caps[0]=PDO_FIXED(9000,3000);assert(prepare(&port,100)==-EINVAL);
 assert(!transmits&&!read_count);assert_sealed();done();
 init(true);tcpc.set_current_limit=set_limit;limit_error=-EIO;
 assert(prepare(&port,100)==-EIO);assert(!read_count);assert_sealed();done();
}
static void test_adc_failures(void){
 init(true);uvs[0]=9000000;assert(prepare(&port,100)==-ETIMEDOUT);
 assert(port.supply_voltage==5000&&read_count>3);assert_sealed();done();
 init(true);read_error=-EIO;assert(prepare(&port,100)==-EIO);assert(read_count==1);assert_sealed();done();
 init(true);uv_count=5;uvs[0]=uvs[1]=uvs[3]=uvs[4]=5000000;uvs[2]=9000000;
 assert(!prepare(&port,200));assert(read_count==6);assert_sealed();done();
 init(true);change_at=2;assert(prepare(&port,100)==-EAGAIN);assert(read_count==2);assert_sealed();done();
 init(true);overrun_at=1;assert(prepare(&port,100)==-ETIMEDOUT);assert_sealed();done();
}
static void test_boundaries(void){
 init(true);tcpc.get_vbus_voltage=NULL;assert(prepare(&port,100)==-EOPNOTSUPP);assert(!port.shutdown_5v&&!transmits);done();
 init(true);port.registered=false;assert(prepare(&port,100)==-ENODEV);done();
 init(true);port.port_type=TYPEC_PORT_DRP;assert(prepare(&port,100)==-EOPNOTSUPP);done();
 init(true);port.connected=false;assert(prepare(&port,100)==-ENOTCONN);assert_sealed();done();
 init(true);port.shutdown_busy=true;assert(prepare(&port,100)==-EBUSY);done();
 init(true);assert(prepare(&port,0)==-EINVAL);assert(prepare(&port,10001)==-EINVAL);done();
 init(true);port.negotiated_rev=PD_REV30;sink_tx_ok=false;
 assert(prepare(&port,100)==-ETIMEDOUT);assert(!transmits&&!read_count);assert_sealed();done();
 init(true);scenario=REJECTED;assert(prepare(&port,100)==-EOPNOTSUPP);
 scenario=SUCCESS;assert(!prepare(&port,200));assert_sealed();done();
}
int main(void){test_request_and_measurement();puts("actual Request/Accept/PS_RDY + fresh ADC success");
 test_protocol_failures();puts("Reject/Wait/no response/no PS_RDY/reset/TX/PDO/current-limit failure");
 test_adc_failures();puts("cached5V with physical9V, ADC error, unstable samples, contract race, overrun");
 test_boundaries();puts("missing ADC/lifetime/role/busy/deadline/SinkTxNG/retry and sealed policy");return 0;}
'''
out = HERE / "tests"
out.mkdir(exist_ok=True)
(out / "actual-contract.c").write_text(enums + prefix + functions + suffix)
cmd = ["cc", "-std=gnu11", "-Wall", "-Wextra", "-Werror", "-Wno-unused-parameter",
       "-Wno-sign-compare", "-pthread", "-fsanitize=address,undefined", "-g",
       str(out / "actual-contract.c"), "-o", str(out / "actual-contract")]
test_env = {**os.environ, "TMPDIR": str(HERE / "tmp")}
built = subprocess.run(cmd, capture_output=True, text=True, env=test_env)
(out / "compile.log").write_text(built.stdout + built.stderr)
assert built.returncode == 0, built.stderr
run = subprocess.run([str(out / "actual-contract")], capture_output=True, text=True,
                     timeout=15, env={**test_env, "ASAN_OPTIONS": "detect_leaks=1:abort_on_error=1",
                                      "UBSAN_OPTIONS": "halt_on_error=1"})
result = dict(passed=run.returncode == 0, functions=NAMES, groups=run.stdout.splitlines(),
              returncode=run.returncode, stderr=run.stderr,
              source_sha256=hashlib.sha256(SRC.encode()).hexdigest(),
              functions_sha256=hashlib.sha256(functions.encode()).hexdigest(),
              compiler=cmd, compiler_tmpdir=str(HERE / "tmp"),
              scheduler_completion_ADC_device_boundaries_modeled=True,
              production_functions_complete=True, phone_accessed=False, installed=False)
(HERE / "test-contract-result.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, ensure_ascii=False))
raise SystemExit(run.returncode)
