enum tcpm_state {INVALID_STATE,TOGGLING,CHECK_CONTAMINANT,SRC_UNATTACHED,SRC_ATTACH_WAIT,SRC_ATTACHED,SRC_STARTUP,SRC_SEND_CAPABILITIES,SRC_SEND_CAPABILITIES_TIMEOUT,SRC_NEGOTIATE_CAPABILITIES,SRC_TRANSITION_SUPPLY,SRC_READY,SRC_WAIT_NEW_CAPABILITIES,SNK_UNATTACHED,SNK_ATTACH_WAIT,SNK_DEBOUNCED,SNK_ATTACHED,SNK_STARTUP,SNK_DISCOVERY,SNK_DISCOVERY_DEBOUNCE,SNK_DISCOVERY_DEBOUNCE_DONE,SNK_WAIT_CAPABILITIES,SNK_WAIT_CAPABILITIES_TIMEOUT,SNK_NEGOTIATE_CAPABILITIES,SNK_NEGOTIATE_PPS_CAPABILITIES,SNK_NEGOTIATE_SPR_AVS_CAPABILITIES,SNK_TRANSITION_SINK,SNK_TRANSITION_SINK_VBUS,SNK_READY,ACC_UNATTACHED,DEBUG_ACC_ATTACHED,DEBUG_ACC_DEBOUNCE,AUDIO_ACC_ATTACHED,AUDIO_ACC_DEBOUNCE,HARD_RESET_SEND,HARD_RESET_START,SRC_HARD_RESET_VBUS_OFF,SRC_HARD_RESET_VBUS_ON,SNK_HARD_RESET_SINK_OFF,SNK_HARD_RESET_WAIT_VBUS,SNK_HARD_RESET_SINK_ON,SOFT_RESET,SRC_SOFT_RESET_WAIT_SNK_TX,SNK_SOFT_RESET,SOFT_RESET_SEND,DR_SWAP_ACCEPT,DR_SWAP_SEND,DR_SWAP_SEND_TIMEOUT,DR_SWAP_CANCEL,DR_SWAP_CHANGE_DR,PR_SWAP_ACCEPT,PR_SWAP_SEND,PR_SWAP_SEND_TIMEOUT,PR_SWAP_CANCEL,PR_SWAP_START,PR_SWAP_SRC_SNK_TRANSITION_OFF,PR_SWAP_SRC_SNK_SOURCE_OFF,PR_SWAP_SRC_SNK_SOURCE_OFF_CC_DEBOUNCED,PR_SWAP_SRC_SNK_SINK_ON,PR_SWAP_SNK_SRC_SINK_OFF,PR_SWAP_SNK_SRC_SOURCE_ON,PR_SWAP_SNK_SRC_SOURCE_ON_VBUS_RAMPED_UP,VCONN_SWAP_ACCEPT,VCONN_SWAP_SEND,VCONN_SWAP_SEND_TIMEOUT,VCONN_SWAP_CANCEL,VCONN_SWAP_START,VCONN_SWAP_WAIT_FOR_VCONN,VCONN_SWAP_TURN_ON_VCONN,VCONN_SWAP_TURN_OFF_VCONN,VCONN_SWAP_SEND_SOFT_RESET,FR_SWAP_SEND,FR_SWAP_SEND_TIMEOUT,FR_SWAP_SNK_SRC_TRANSITION_TO_OFF,FR_SWAP_SNK_SRC_NEW_SINK_READY,FR_SWAP_SNK_SRC_SOURCE_VBUS_APPLIED,FR_SWAP_CANCEL,SNK_TRY,SNK_TRY_WAIT,SNK_TRY_WAIT_DEBOUNCE,SNK_TRY_WAIT_DEBOUNCE_CHECK_VBUS,SRC_TRYWAIT,SRC_TRYWAIT_DEBOUNCE,SRC_TRYWAIT_UNATTACHED,SRC_TRY,SRC_TRY_WAIT,SRC_TRY_DEBOUNCE,SNK_TRYWAIT,SNK_TRYWAIT_DEBOUNCE,SNK_TRYWAIT_VBUS,BIST_RX,GET_STATUS_SEND,GET_STATUS_SEND_TIMEOUT,GET_PPS_STATUS_SEND,GET_PPS_STATUS_SEND_TIMEOUT,GET_SINK_CAP,GET_SINK_CAP_TIMEOUT,ERROR_RECOVERY,PORT_RESET,PORT_RESET_WAIT_OFF,AMS_START,CHUNK_NOT_SUPP,SRC_VDM_IDENTITY_REQUEST};
enum pd_ctrl_msg_type {PD_CTRL_ACCEPT,PD_CTRL_DR_SWAP,PD_CTRL_FR_SWAP,PD_CTRL_GET_COUNTRY_CODES,PD_CTRL_GET_PPS_STATUS,PD_CTRL_GET_REVISION,PD_CTRL_GET_SINK_CAP,PD_CTRL_GET_SINK_CAP_EXT,PD_CTRL_GET_SOURCE_CAP,PD_CTRL_GET_SOURCE_CAP_EXT,PD_CTRL_GET_STATUS,PD_CTRL_GOOD_CRC,PD_CTRL_GOTO_MIN,PD_CTRL_NOT_SUPP,PD_CTRL_PING,PD_CTRL_PR_SWAP,PD_CTRL_PS_RDY,PD_CTRL_REJECT,PD_CTRL_SOFT_RESET,PD_CTRL_VCONN_SWAP,PD_CTRL_WAIT};
enum {PD_MSG_CTRL_NOT_SUPP,PD_MSG_CTRL_REJECT,PD_MSG_CTRL_WAIT,PD_MSG_DATA_REV,PD_MSG_DATA_SINK_CAP,PD_MSG_DATA_SOURCE_CAP,PD_MSG_EXT_SINK_CAP_EXT};

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
static void tcpm_shutdown_5v_complete(struct tcpm_port *port, int status)
{
	if (!port->shutdown_5v_pending)
		return;
	port->shutdown_5v_status = status;
	port->shutdown_5v_pending = false;
	complete(&port->shutdown_5v_complete);
}

static void tcpm_shutdown_state_change(struct tcpm_port *port, enum tcpm_state state)
{
	port->shutdown_sequence++;
	if (state != AMS_START && state != SNK_NEGOTIATE_CAPABILITIES &&
	    state != SNK_TRANSITION_SINK && state != SNK_TRANSITION_SINK_VBUS &&
	    state != SNK_READY)
		tcpm_shutdown_5v_complete(port, -EPROTO);
}

static void tcpm_set_state(struct tcpm_port *port, enum tcpm_state state,
			   unsigned int delay_ms)
{
	if (delay_ms) {
		tcpm_log(port, "pending state change %s -> %s @ %u ms [%s %s]",
			 tcpm_states[port->state], tcpm_states[state], delay_ms,
			 pd_rev[port->negotiated_rev], tcpm_ams_str[port->ams]);
		port->delayed_state = state;
		mod_tcpm_delayed_work(port, delay_ms);
		port->delayed_runtime = ktime_add(ktime_get(), ms_to_ktime(delay_ms));
		port->delay_ms = delay_ms;
	} else {
		tcpm_log(port, "state change %s -> %s [%s %s]",
			 tcpm_states[port->state], tcpm_states[state],
			 pd_rev[port->negotiated_rev], tcpm_ams_str[port->ams]);
		port->delayed_state = INVALID_STATE;
		port->prev_state = port->state;
		tcpm_shutdown_state_change(port, state);
		port->state = state;
		/*
		 * Don't re-queue the state machine work item if we're currently
		 * in the state machine and we're immediately changing states.
		 * tcpm_state_machine_work() will continue running the state
		 * machine.
		 */
		if (!port->state_machine_running)
			mod_tcpm_delayed_work(port, 0);
	}
}

static int tcpm_ams_start(struct tcpm_port *port, enum tcpm_ams ams)
{
	int ret = 0;

	tcpm_log(port, "AMS %s start", tcpm_ams_str[ams]);

	if (!tcpm_ams_interruptible(port) &&
	    !(ams == HARD_RESET || ams == SOFT_RESET_AMS)) {
		port->upcoming_state = INVALID_STATE;
		tcpm_log(port, "AMS %s not interruptible, aborting",
			 tcpm_ams_str[port->ams]);
		return -EAGAIN;
	}

	if (port->pwr_role == TYPEC_SOURCE) {
		enum typec_cc_status cc_req = port->cc_req;

		port->ams = ams;

		if (ams == HARD_RESET) {
			tcpm_set_cc(port, tcpm_rp_cc(port));
			tcpm_pd_transmit(port, TCPC_TX_HARD_RESET, NULL);
			tcpm_set_state(port, HARD_RESET_START, 0);
			return ret;
		} else if (ams == SOFT_RESET_AMS) {
			if (!port->explicit_contract)
				tcpm_set_cc(port, tcpm_rp_cc(port));
			tcpm_set_state(port, SOFT_RESET_SEND, 0);
			return ret;
		} else if (tcpm_vdm_ams(port)) {
			/* tSinkTx is enforced in vdm_run_state_machine */
			if (port->negotiated_rev >= PD_REV30)
				tcpm_set_cc(port, SINK_TX_NG);
			return ret;
		}

		if (port->negotiated_rev >= PD_REV30)
			tcpm_set_cc(port, SINK_TX_NG);

		switch (port->state) {
		case SRC_READY:
		case SRC_STARTUP:
		case SRC_SOFT_RESET_WAIT_SNK_TX:
		case SOFT_RESET:
		case SOFT_RESET_SEND:
			if (port->negotiated_rev >= PD_REV30)
				tcpm_set_state(port, AMS_START,
					       cc_req == SINK_TX_OK ?
					       PD_T_SINK_TX : 0);
			else
				tcpm_set_state(port, AMS_START, 0);
			break;
		default:
			if (port->negotiated_rev >= PD_REV30)
				tcpm_set_state(port, SRC_READY,
					       cc_req == SINK_TX_OK ?
					       PD_T_SINK_TX : 0);
			else
				tcpm_set_state(port, SRC_READY, 0);
			break;
		}
	} else {
		if (port->negotiated_rev >= PD_REV30 &&
		    !tcpm_sink_tx_ok(port) &&
		    ams != SOFT_RESET_AMS &&
		    ams != HARD_RESET) {
			port->upcoming_state = INVALID_STATE;
			tcpm_log(port, "Sink TX No Go");
			return -EAGAIN;
		}

		port->ams = ams;

		if (ams == HARD_RESET) {
			tcpm_pd_transmit(port, TCPC_TX_HARD_RESET, NULL);
			tcpm_set_state(port, HARD_RESET_START, 0);
			return ret;
		} else if (tcpm_vdm_ams(port)) {
			return ret;
		}

		if (port->state == SNK_READY ||
		    port->state == SNK_SOFT_RESET)
			tcpm_set_state(port, AMS_START, 0);
		else
			tcpm_set_state(port, SNK_READY, 0);
	}

	return ret;
}

static int tcpm_pd_select_pdo(struct tcpm_port *port, int *sink_pdo,
			      int *src_pdo)
{
	unsigned int i, j, max_src_mv = 0, min_src_mv = 0, max_mw = 0,
		     max_mv = 0, src_mw = 0, src_ma = 0, max_snk_mv = 0,
		     min_snk_mv = 0;
	int ret = -EINVAL;

	port->pps_data.supported = false;
	port->usb_type = POWER_SUPPLY_USB_TYPE_PD;
	power_supply_changed(port->psy);

	/*
	 * Select the source PDO providing the most power which has a
	 * matchig sink cap.
	 */
	for (i = 0; i < port->nr_source_caps; i++) {
		u32 pdo = port->source_caps[i];
		enum pd_pdo_type type = pdo_type(pdo);

		if (port->shutdown_5v &&
		    (type != PDO_TYPE_FIXED || pdo_fixed_voltage(pdo) != 5000))
			continue;

		switch (type) {
		case PDO_TYPE_FIXED:
			max_src_mv = pdo_fixed_voltage(pdo);
			min_src_mv = max_src_mv;
			break;
		case PDO_TYPE_BATT:
		case PDO_TYPE_VAR:
			max_src_mv = pdo_max_voltage(pdo);
			min_src_mv = pdo_min_voltage(pdo);
			break;
		case PDO_TYPE_APDO:
			if (pdo_apdo_type(pdo) == APDO_TYPE_PPS) {
				port->pps_data.supported = true;
			} else if (pdo_apdo_type(pdo) == APDO_TYPE_SPR_AVS) {
				port->spr_avs_data.port_partner_src_status = SPR_AVS_SUPPORTED;
				port->spr_avs_data.port_partner_src_pdo_index = i;
			}
			continue;
		default:
			tcpm_log(port, "Invalid source PDO type, ignoring");
			continue;
		}

		switch (type) {
		case PDO_TYPE_FIXED:
		case PDO_TYPE_VAR:
			src_ma = pdo_max_current(pdo);
			src_mw = src_ma * min_src_mv / 1000;
			break;
		case PDO_TYPE_BATT:
			src_mw = pdo_max_power(pdo);
			break;
		case PDO_TYPE_APDO:
			continue;
		default:
			tcpm_log(port, "Invalid source PDO type, ignoring");
			continue;
		}

		for (j = 0; j < port->nr_snk_pdo; j++) {
			pdo = port->snk_pdo[j];

			switch (pdo_type(pdo)) {
			case PDO_TYPE_FIXED:
				max_snk_mv = pdo_fixed_voltage(pdo);
				min_snk_mv = max_snk_mv;
				break;
			case PDO_TYPE_BATT:
			case PDO_TYPE_VAR:
				max_snk_mv = pdo_max_voltage(pdo);
				min_snk_mv = pdo_min_voltage(pdo);
				break;
			case PDO_TYPE_APDO:
				if (pdo_apdo_type(pdo) == APDO_TYPE_SPR_AVS) {
					port->spr_avs_data.port_snk_status = SPR_AVS_SUPPORTED;
					port->spr_avs_data.port_snk_pdo_index = j;
				}
				continue;
			default:
				tcpm_log(port, "Invalid sink PDO type, ignoring");
				continue;
			}

			if (max_src_mv <= max_snk_mv &&
				min_src_mv >= min_snk_mv) {
				/* Prefer higher voltages if available */
				if ((src_mw == max_mw && min_src_mv > max_mv) ||
							src_mw > max_mw) {
					*src_pdo = i;
					*sink_pdo = j;
					max_mw = src_mw;
					max_mv = min_src_mv;
					ret = 0;
				}
			}
		}
	}

	if (port->spr_avs_data.port_snk_status == SPR_AVS_UNKNOWN)
		port->spr_avs_data.port_snk_status = SPR_AVS_NOT_SUPPORTED;

	if (port->spr_avs_data.port_partner_src_status == SPR_AVS_UNKNOWN)
		port->spr_avs_data.port_partner_src_status = SPR_AVS_NOT_SUPPORTED;

	if (port->pps_data.supported &&
	    port->spr_avs_data.port_partner_src_status == SPR_AVS_SUPPORTED)
		port->usb_type = POWER_SUPPLY_USB_TYPE_PD_PPS_SPR_AVS;
	else if (port->pps_data.supported)
		port->usb_type = POWER_SUPPLY_USB_TYPE_PD_PPS;
	else if (port->spr_avs_data.port_partner_src_status == SPR_AVS_SUPPORTED)
		port->usb_type = POWER_SUPPLY_USB_TYPE_PD_SPR_AVS;

	if (port->usb_type != POWER_SUPPLY_USB_TYPE_PD)
		power_supply_changed(port->psy);

	return ret;
}

static int tcpm_pd_build_request(struct tcpm_port *port, u32 *rdo)
{
	unsigned int mv, ma, mw, flags;
	unsigned int max_ma, max_mw;
	enum pd_pdo_type type;
	u32 pdo, matching_snk_pdo;
	int src_pdo_index = 0;
	int snk_pdo_index = 0;
	int ret;

	ret = tcpm_pd_select_pdo(port, &snk_pdo_index, &src_pdo_index);
	if (ret < 0)
		return ret;

	pdo = port->source_caps[src_pdo_index];
	matching_snk_pdo = port->snk_pdo[snk_pdo_index];
	type = pdo_type(pdo);

	switch (type) {
	case PDO_TYPE_FIXED:
		mv = pdo_fixed_voltage(pdo);
		break;
	case PDO_TYPE_BATT:
	case PDO_TYPE_VAR:
		mv = pdo_min_voltage(pdo);
		break;
	default:
		tcpm_log(port, "Invalid PDO selected!");
		return -EINVAL;
	}

	/* Select maximum available current within the sink pdo's limit */
	if (type == PDO_TYPE_BATT) {
		mw = min_power(pdo, matching_snk_pdo);
		ma = 1000 * mw / mv;
	} else {
		ma = min_current(pdo, matching_snk_pdo);
		mw = ma * mv / 1000;
	}

	flags = RDO_USB_COMM | RDO_NO_SUSPEND;

	/* Set mismatch bit if offered power is less than operating power */
	max_ma = ma;
	max_mw = mw;
	if (mw < port->operating_snk_mw) {
		flags |= RDO_CAP_MISMATCH;
		if (type == PDO_TYPE_BATT &&
		    (pdo_max_power(matching_snk_pdo) > pdo_max_power(pdo)))
			max_mw = pdo_max_power(matching_snk_pdo);
		else if (pdo_max_current(matching_snk_pdo) >
			 pdo_max_current(pdo))
			max_ma = pdo_max_current(matching_snk_pdo);
	}

	tcpm_log(port, "cc=%d cc1=%d cc2=%d vbus=%d vconn=%s polarity=%d",
		 port->cc_req, port->cc1, port->cc2, port->vbus_source,
		 port->vconn_role == TYPEC_SOURCE ? "source" : "sink",
		 port->polarity);

	if (type == PDO_TYPE_BATT) {
		*rdo = RDO_BATT(src_pdo_index + 1, mw, max_mw, flags);

		tcpm_log(port, "Requesting PDO %d: %u mV, %u mW%s",
			 src_pdo_index, mv, mw,
			 flags & RDO_CAP_MISMATCH ? " [mismatch]" : "");
	} else {
		*rdo = RDO_FIXED(src_pdo_index + 1, ma, max_ma, flags);

		tcpm_log(port, "Requesting PDO %d: %u mV, %u mA%s",
			 src_pdo_index, mv, ma,
			 flags & RDO_CAP_MISMATCH ? " [mismatch]" : "");
	}

	port->req_current_limit = ma;
	port->req_supply_voltage = mv;

	return 0;
}

static int tcpm_pd_send_request(struct tcpm_port *port)
{
	struct pd_message msg;
	int ret;
	u32 rdo;

	ret = tcpm_pd_build_request(port, &rdo);
	if (ret < 0)
		return ret;

	/*
	 * Relax the threshold as voltage will be adjusted after Accept Message plus tSrcTransition.
	 * It is safer to modify the threshold here.
	 */
	tcpm_set_auto_vbus_discharge_threshold(port, TYPEC_PWR_MODE_USB, false, 0);

	memset(&msg, 0, sizeof(msg));
	msg.header = PD_HEADER_LE(PD_DATA_REQUEST,
				  port->pwr_role,
				  port->data_role,
				  port->negotiated_rev,
				  port->message_id, 1);
	msg.payload[0] = cpu_to_le32(rdo);

	return tcpm_pd_transmit(port, TCPC_TX_SOP, &msg);
}

static int tcpm_pd_send_aug_supply_request(struct tcpm_port *port,
					   enum aug_req_type type)
{
	struct pd_message msg;
	int ret;
	u32 rdo;

	if (port->shutdown_5v)
		return -ESHUTDOWN;

	if (type == PD_PPS) {
		ret = tcpm_pd_build_pps_request(port, &rdo);
	} else if (type == PD_SPR_AVS) {
		ret = tcpm_pd_build_spr_avs_request(port, &rdo);
	} else {
		tcpm_log(port, "Invalid aug_req_type %d", type);
		ret = -EOPNOTSUPP;
	}
	if (ret < 0)
		return ret;

	/* Relax the threshold as voltage will be adjusted right after Accept Message. */
	tcpm_set_auto_vbus_discharge_threshold(port, TYPEC_PWR_MODE_USB, false, 0);

	memset(&msg, 0, sizeof(msg));
	msg.header = PD_HEADER_LE(PD_DATA_REQUEST,
				  port->pwr_role,
				  port->data_role,
				  port->negotiated_rev,
				  port->message_id, 1);
	msg.payload[0] = cpu_to_le32(rdo);

	return tcpm_pd_transmit(port, TCPC_TX_SOP, &msg);
}

static int tcpm_set_current_limit(struct tcpm_port *port, u32 max_ma, u32 mv)
{
	int ret = -EOPNOTSUPP;

	tcpm_log(port, "Setting voltage/current limit %u mV %u mA", mv, max_ma);

	port->supply_voltage = mv;
	port->current_limit = max_ma;
	power_supply_changed(port->psy);

	if (port->tcpc->set_current_limit)
		ret = port->tcpc->set_current_limit(port->tcpc, max_ma, mv);

	return ret;
}

static void tcpm_pd_ctrl_request(struct tcpm_port *port,
				 const struct pd_message *msg,
				 enum tcpm_transmit_type rx_sop_type)
{
	enum pd_ctrl_msg_type type = pd_header_type_le(msg->header);
	enum tcpm_state next_state;
	unsigned int rev = pd_header_rev_le(msg->header);
	int ret;

	/*
	 * Stop VDM state machine if interrupted by other Messages while NOT_SUPP is allowed in
	 * VDM AMS if waiting for VDM responses and will be handled later.
	 */
	if (tcpm_vdm_ams(port) && type != PD_CTRL_NOT_SUPP && type != PD_CTRL_GOOD_CRC) {
		port->vdm_state = VDM_STATE_ERR_BUSY;
		tcpm_ams_finish(port);
		mod_vdm_delayed_work(port, 0);
	}

	switch (type) {
	case PD_CTRL_GOOD_CRC:
	case PD_CTRL_PING:
		break;
	case PD_CTRL_GET_SOURCE_CAP:
		tcpm_pd_handle_msg(port, PD_MSG_DATA_SOURCE_CAP, GET_SOURCE_CAPABILITIES);
		break;
	case PD_CTRL_GET_SINK_CAP:
		tcpm_pd_handle_msg(port, PD_MSG_DATA_SINK_CAP, GET_SINK_CAPABILITIES);
		break;
	case PD_CTRL_GOTO_MIN:
		break;
	case PD_CTRL_PS_RDY:
		switch (port->state) {
		case SNK_TRANSITION_SINK:
			if (port->vbus_present) {
				ret = tcpm_set_current_limit(port,
						       port->req_current_limit,
						       port->req_supply_voltage);
				port->explicit_contract = true;
				tcpm_set_auto_vbus_discharge_threshold(port,
								       TYPEC_PWR_MODE_PD,
								       port->pps_data.active,
								       port->supply_voltage);
				tcpm_set_state(port, SNK_READY, 0);
				if (rx_sop_type == TCPC_TX_SOP && port->shutdown_5v_accepted &&
				    port->req_supply_voltage == 5000)
					tcpm_shutdown_5v_complete(port,
						port->tcpc->set_current_limit ? ret : 0);
			} else {
				/*
				 * Seen after power swap. Keep waiting for VBUS
				 * in a transitional state.
				 */
				tcpm_set_state(port,
					       SNK_TRANSITION_SINK_VBUS, 0);
			}
			break;
		case PR_SWAP_SRC_SNK_SOURCE_OFF_CC_DEBOUNCED:
			tcpm_set_state(port, PR_SWAP_SRC_SNK_SINK_ON, 0);
			break;
		case PR_SWAP_SNK_SRC_SINK_OFF:
			tcpm_set_state(port, PR_SWAP_SNK_SRC_SOURCE_ON, 0);
			break;
		case VCONN_SWAP_WAIT_FOR_VCONN:
			tcpm_set_state(port, VCONN_SWAP_TURN_OFF_VCONN, 0);
			break;
		case FR_SWAP_SNK_SRC_TRANSITION_TO_OFF:
			tcpm_set_state(port, FR_SWAP_SNK_SRC_NEW_SINK_READY, 0);
			break;
		default:
			tcpm_pd_handle_state(port,
					     port->pwr_role == TYPEC_SOURCE ?
					     SRC_SOFT_RESET_WAIT_SNK_TX :
					     SNK_SOFT_RESET,
					     NONE_AMS, 0);
			break;
		}
		break;
	case PD_CTRL_REJECT:
	case PD_CTRL_WAIT:
	case PD_CTRL_NOT_SUPP:
		switch (port->state) {
		case SNK_NEGOTIATE_CAPABILITIES:
			if (rx_sop_type == TCPC_TX_SOP)
				tcpm_shutdown_5v_complete(port, type == PD_CTRL_WAIT ?
							  -EAGAIN : -EOPNOTSUPP);
			/* USB PD specification, Figure 8-43 */
			if (port->explicit_contract)
				next_state = SNK_READY;
			else
				next_state = SNK_WAIT_CAPABILITIES;

			/* Threshold was relaxed before sending Request. Restore it back. */
			tcpm_set_auto_vbus_discharge_threshold(port, TYPEC_PWR_MODE_PD,
							       port->pps_data.active,
							       port->supply_voltage);
			tcpm_set_state(port, next_state, 0);
			break;
		case SNK_NEGOTIATE_PPS_CAPABILITIES:
			/* Revert data back from any requested PPS updates */
			port->pps_data.req_out_volt = port->supply_voltage;
			port->pps_data.req_op_curr = port->current_limit;
			port->aug_supply_req_status = (type == PD_CTRL_WAIT ?
					    -EAGAIN : -EOPNOTSUPP);

			/* Threshold was relaxed before sending Request. Restore it back. */
			tcpm_set_auto_vbus_discharge_threshold(port, TYPEC_PWR_MODE_PD,
							       port->pps_data.active,
							       port->supply_voltage);

			tcpm_set_state(port, SNK_READY, 0);
			break;
		case SNK_NEGOTIATE_SPR_AVS_CAPABILITIES:
			/* Revert data back from any requested SPR AVS updates */
			port->spr_avs_data.req_out_volt_mv = port->supply_voltage;
			port->spr_avs_data.req_op_curr_ma = port->current_limit;
			port->aug_supply_req_status = (type == PD_CTRL_WAIT ?
					      -EAGAIN : -EOPNOTSUPP);

			/* Threshold was relaxed before sending Request. Restore it back. */
			tcpm_set_auto_vbus_discharge_threshold(port, TYPEC_PWR_MODE_PD,
							       port->spr_avs_data.active,
							       port->supply_voltage);

			tcpm_set_state(port, SNK_READY, 0);
			break;
		case DR_SWAP_SEND:
			port->swap_status = (type == PD_CTRL_WAIT ?
					     -EAGAIN : -EOPNOTSUPP);
			tcpm_set_state(port, DR_SWAP_CANCEL, 0);
			break;
		case PR_SWAP_SEND:
			port->swap_status = (type == PD_CTRL_WAIT ?
					     -EAGAIN : -EOPNOTSUPP);
			tcpm_set_state(port, PR_SWAP_CANCEL, 0);
			break;
		case VCONN_SWAP_SEND:
			port->swap_status = (type == PD_CTRL_WAIT ?
					     -EAGAIN : -EOPNOTSUPP);
			tcpm_set_state(port, VCONN_SWAP_CANCEL, 0);
			break;
		case FR_SWAP_SEND:
			tcpm_set_state(port, FR_SWAP_CANCEL, 0);
			break;
		case GET_SINK_CAP:
			port->sink_cap_done = true;
			tcpm_set_state(port, ready_state(port), 0);
			break;
		/*
		 * Some port partners do not support GET_STATUS, avoid soft reset the link to
		 * prevent redundant power re-negotiation
		 */
		case GET_STATUS_SEND:
			tcpm_set_state(port, ready_state(port), 0);
			break;
		case SRC_READY:
		case SNK_READY:
			if (port->vdm_state > VDM_STATE_READY) {
				port->vdm_state = VDM_STATE_DONE;
				if (tcpm_vdm_ams(port))
					tcpm_ams_finish(port);
				mod_vdm_delayed_work(port, 0);
				break;
			}
			fallthrough;
		default:
			tcpm_pd_handle_state(port,
					     port->pwr_role == TYPEC_SOURCE ?
					     SRC_SOFT_RESET_WAIT_SNK_TX :
					     SNK_SOFT_RESET,
					     NONE_AMS, 0);
			break;
		}
		break;
	case PD_CTRL_ACCEPT:
		switch (port->state) {
		case SNK_NEGOTIATE_CAPABILITIES:
			if (rx_sop_type == TCPC_TX_SOP && port->shutdown_5v_pending &&
			    port->req_supply_voltage == 5000)
				port->shutdown_5v_accepted = true;
			port->pps_data.active = false;
			port->spr_avs_data.active = false;
			tcpm_set_state(port, SNK_TRANSITION_SINK, 0);
			break;
		case SNK_NEGOTIATE_PPS_CAPABILITIES:
			port->pps_data.active = true;
			port->pps_data.min_volt = port->pps_data.req_min_volt;
			port->pps_data.max_volt = port->pps_data.req_max_volt;
			port->pps_data.max_curr = port->pps_data.req_max_curr;
			port->req_supply_voltage = port->pps_data.req_out_volt;
			port->req_current_limit = port->pps_data.req_op_curr;
			power_supply_changed(port->psy);
			tcpm_set_state(port, SNK_TRANSITION_SINK, 0);
			break;
		case SNK_NEGOTIATE_SPR_AVS_CAPABILITIES:
			port->spr_avs_data.active = true;
			port->req_supply_voltage = port->spr_avs_data.req_out_volt_mv;
			port->req_current_limit = port->spr_avs_data.req_op_curr_ma;
			power_supply_changed(port->psy);
			tcpm_set_state(port, SNK_TRANSITION_SINK, 0);
			break;
		case SOFT_RESET_SEND:
			if (port->ams == SOFT_RESET_AMS)
				tcpm_ams_finish(port);
			/*
			 * SOP' Soft Reset is done after Vconn Swap,
			 * which returns to ready state
			 */
			if (rx_sop_type == TCPC_TX_SOP_PRIME) {
				if (rev < port->negotiated_rev_prime)
					port->negotiated_rev_prime = rev;
				tcpm_set_state(port, ready_state(port), 0);
				break;
			}
			if (port->pwr_role == TYPEC_SOURCE) {
				port->upcoming_state = SRC_SEND_CAPABILITIES;
				tcpm_ams_start(port, POWER_NEGOTIATION);
			} else {
				tcpm_set_state(port, SNK_WAIT_CAPABILITIES, 0);
			}
			break;
		case DR_SWAP_SEND:
			tcpm_set_state(port, DR_SWAP_CHANGE_DR, 0);
			break;
		case PR_SWAP_SEND:
			tcpm_set_state(port, PR_SWAP_START, 0);
			break;
		case VCONN_SWAP_SEND:
			tcpm_set_state(port, VCONN_SWAP_START, 0);
			break;
		case FR_SWAP_SEND:
			tcpm_set_state(port, FR_SWAP_SNK_SRC_TRANSITION_TO_OFF, 0);
			break;
		default:
			tcpm_pd_handle_state(port,
					     port->pwr_role == TYPEC_SOURCE ?
					     SRC_SOFT_RESET_WAIT_SNK_TX :
					     SNK_SOFT_RESET,
					     NONE_AMS, 0);
			break;
		}
		break;
	case PD_CTRL_SOFT_RESET:
		port->ams = SOFT_RESET_AMS;
		tcpm_set_state(port, SOFT_RESET, 0);
		break;
	case PD_CTRL_DR_SWAP:
		/*
		 * XXX
		 * 6.3.9: If an alternate mode is active, a request to swap
		 * alternate modes shall trigger a port reset.
		 */
		if (port->typec_caps.data != TYPEC_PORT_DRD) {
			tcpm_pd_handle_msg(port,
					   port->negotiated_rev < PD_REV30 ?
					   PD_MSG_CTRL_REJECT :
					   PD_MSG_CTRL_NOT_SUPP,
					   NONE_AMS);
		} else {
			if (port->vdm_discovery_state == VDM_DISCOVERY_UNKNOWN &&
			    port->negotiated_rev < PD_REV30) {
				tcpm_queue_message(port, PD_MSG_CTRL_WAIT);
				break;
			}

			tcpm_pd_handle_state(port, DR_SWAP_ACCEPT, DATA_ROLE_SWAP, 0);
		}
		break;
	case PD_CTRL_PR_SWAP:
		if (port->port_type != TYPEC_PORT_DRP) {
			tcpm_pd_handle_msg(port,
					   port->negotiated_rev < PD_REV30 ?
					   PD_MSG_CTRL_REJECT :
					   PD_MSG_CTRL_NOT_SUPP,
					   NONE_AMS);
		} else {
			if (port->vdm_discovery_state == VDM_DISCOVERY_UNKNOWN &&
			    port->negotiated_rev < PD_REV30) {
				tcpm_queue_message(port, PD_MSG_CTRL_WAIT);
				break;
			}

			tcpm_pd_handle_state(port, PR_SWAP_ACCEPT, POWER_ROLE_SWAP, 0);
		}
		break;
	case PD_CTRL_VCONN_SWAP:
		if (port->vdm_discovery_state == VDM_DISCOVERY_UNKNOWN &&
		    port->negotiated_rev < PD_REV30) {
			tcpm_queue_message(port, PD_MSG_CTRL_WAIT);
			break;
		}

		tcpm_pd_handle_state(port, VCONN_SWAP_ACCEPT, VCONN_SWAP, 0);
		break;
	case PD_CTRL_GET_SOURCE_CAP_EXT:
	case PD_CTRL_GET_STATUS:
	case PD_CTRL_FR_SWAP:
	case PD_CTRL_GET_PPS_STATUS:
	case PD_CTRL_GET_COUNTRY_CODES:
		/* Currently not supported */
		tcpm_pd_handle_msg(port,
				   port->negotiated_rev < PD_REV30 ?
				   PD_MSG_CTRL_REJECT :
				   PD_MSG_CTRL_NOT_SUPP,
				   NONE_AMS);
		break;
	case PD_CTRL_GET_REVISION:
		if (port->negotiated_rev >= PD_REV30 && port->pd_rev.rev_major)
			tcpm_pd_handle_msg(port, PD_MSG_DATA_REV,
					   REVISION_INFORMATION);
		else
			tcpm_pd_handle_msg(port,
					   port->negotiated_rev < PD_REV30 ?
					   PD_MSG_CTRL_REJECT :
					   PD_MSG_CTRL_NOT_SUPP,
					   NONE_AMS);
		break;
	case PD_CTRL_GET_SINK_CAP_EXT:
		/* This is an unsupported message if port type is SRC */
		if (port->negotiated_rev >= PD_REV30 &&
		    port->port_type != TYPEC_PORT_SRC)
			tcpm_pd_handle_msg(port, PD_MSG_EXT_SINK_CAP_EXT,
					   GETTING_SINK_EXTENDED_CAPABILITIES);
		else
			tcpm_pd_handle_msg(port,
					   port->negotiated_rev < PD_REV30 ?
					   PD_MSG_CTRL_REJECT :
					   PD_MSG_CTRL_NOT_SUPP,
					   NONE_AMS);
		break;
	default:
		tcpm_pd_handle_msg(port,
				   port->negotiated_rev < PD_REV30 ?
				   PD_MSG_CTRL_REJECT :
				   PD_MSG_CTRL_NOT_SUPP,
				   NONE_AMS);
		tcpm_log(port, "Unrecognized ctrl message type %#x", type);
		break;
	}
}

static int tcpm_pps_activate(struct tcpm_port *port, bool activate)
{
	int ret = 0;

	mutex_lock(&port->swap_lock);
	mutex_lock(&port->lock);
	if (port->shutdown_5v) {
		ret = -ESHUTDOWN;
		goto port_unlock;
	}


	if (!port->pps_data.supported) {
		ret = -EOPNOTSUPP;
		goto port_unlock;
	}

	/* Trying to deactivate PPS when already deactivated so just bail */
	if (!port->pps_data.active && !activate)
		goto port_unlock;

	if (port->state != SNK_READY) {
		ret = -EAGAIN;
		goto port_unlock;
	}

	if (activate)
		port->upcoming_state = SNK_NEGOTIATE_PPS_CAPABILITIES;
	else
		port->upcoming_state = SNK_NEGOTIATE_CAPABILITIES;
	ret = tcpm_ams_start(port, POWER_NEGOTIATION);
	if (ret == -EAGAIN) {
		port->upcoming_state = INVALID_STATE;
		goto port_unlock;
	}

	reinit_completion(&port->aug_supply_req_complete);
	port->aug_supply_req_status = 0;
	port->aug_supply_req_pending = true;

	/* Trigger PPS request or move back to standard PDO contract */
	if (activate) {
		port->pps_data.req_out_volt = port->supply_voltage;
		port->pps_data.req_op_curr = port->current_limit;
	}
	mutex_unlock(&port->lock);

	if (!wait_for_completion_timeout(&port->aug_supply_req_complete,
					 msecs_to_jiffies(PD_AUG_PSY_CTRL_TIMEOUT)))
		ret = -ETIMEDOUT;
	else
		ret = port->aug_supply_req_status;

	goto swap_unlock;

port_unlock:
	mutex_unlock(&port->lock);
swap_unlock:
	mutex_unlock(&port->swap_lock);

	return ret;
}

static int tcpm_port_type_set(struct typec_port *p, enum typec_port_type type)
{
	struct tcpm_port *port = typec_get_drvdata(p);

	mutex_lock(&port->lock);
	if (port->shutdown_5v) {
		mutex_unlock(&port->lock);
		return -ESHUTDOWN;
	}

	if (type == port->port_type)
		goto port_unlock;

	port->port_type = type;

	if (!port->connected) {
		tcpm_set_state(port, PORT_RESET, 0);
	} else if (type == TYPEC_PORT_SNK) {
		if (!(port->pwr_role == TYPEC_SINK &&
		      port->data_role == TYPEC_DEVICE))
			tcpm_set_state(port, PORT_RESET, 0);
	} else if (type == TYPEC_PORT_SRC) {
		if (!(port->pwr_role == TYPEC_SOURCE &&
		      port->data_role == TYPEC_HOST))
			tcpm_set_state(port, PORT_RESET, 0);
	}

port_unlock:
	mutex_unlock(&port->lock);
	return 0;
}

static bool tcpm_shutdown_contract_valid(struct tcpm_port *port)
{
	return port->registered && port->connected && port->vbus_present &&
		port->pwr_role == TYPEC_SINK && port->state == SNK_READY &&
		port->upcoming_state == INVALID_STATE &&
		!port->pps_data.active && !port->spr_avs_data.active &&
		port->supply_voltage == 5000 &&
		(!port->pd_capable || port->explicit_contract);
}

int tcpm_prepare_sink_shutdown(struct tcpm_port *port, unsigned int timeout_ms,
			       int (*read_vbus_uv)(void *context, int *uv), void *context)
{
	unsigned long deadline, remaining;
	u64 sequence;
	unsigned int samples = 0;
	int ret, uv;
	bool request = false;

	if (!timeout_ms || timeout_ms > 10000)
		return -EINVAL;
	deadline = jiffies + msecs_to_jiffies(timeout_ms);
	mutex_lock(&port->swap_lock);
	mutex_lock(&port->lock);
	if (!port->registered) {
		ret = -ENODEV;
		goto unlock;
	}
	if (!read_vbus_uv) {
		ret = -EOPNOTSUPP;
		goto unlock;
	}
	if (port->port_type != TYPEC_PORT_SNK ||
	    port->typec_caps.data != TYPEC_PORT_UFP) {
		ret = -EOPNOTSUPP;
		goto unlock;
	}
	if (port->shutdown_busy) {
		ret = -EBUSY;
		goto unlock;
	}
	/* Seal before waiting, not after completion. Retain this on every failure. */
	port->shutdown_5v = true;
	port->shutdown_busy = true;
	mutex_unlock(&port->lock);

	/* Give an existing AMS its normal finite time to finish. Do not reset it. */
	for (;;) {
		mutex_lock(&port->lock);
		if (!port->registered || !port->connected || !port->vbus_present ||
		    port->pwr_role != TYPEC_SINK) {
			ret = -ENOTCONN;
			goto finish_locked;
		}
		if (port->state == SNK_READY && port->ams == NONE_AMS &&
		    port->upcoming_state == INVALID_STATE && !port->vdm_sm_running) {
			if (!port->pd_capable)
				break;
			if (!port->explicit_contract) {
				ret = -EPROTO;
				goto finish_locked;
			}
			/* Always obtain a fresh fixed-5V Accept + PS_RDY, even if cached at 5V. */
			reinit_completion(&port->shutdown_5v_complete);
			port->shutdown_5v_accepted = false;
			port->shutdown_5v_pending = true;
			port->shutdown_5v_status = -EINPROGRESS;
			port->upcoming_state = SNK_NEGOTIATE_CAPABILITIES;
			ret = tcpm_ams_start(port, POWER_NEGOTIATION);
			if (!ret) {
				request = true;
				break;
			}
			port->shutdown_5v_pending = false;
			port->upcoming_state = INVALID_STATE;
			if (ret != -EAGAIN)
				goto finish_locked;
		}
		mutex_unlock(&port->lock);
		if (time_after_eq(jiffies, deadline)) {
			ret = -ETIMEDOUT;
			goto finish;
		}
		msleep(TCPM_SHUTDOWN_SAMPLE_MS);
	}
	mutex_unlock(&port->lock);
	if (request) {
		remaining = time_before(jiffies, deadline) ? deadline - jiffies : 0;
		if (!remaining || !wait_for_completion_timeout(&port->shutdown_5v_complete,
							     remaining)) {
			ret = -ETIMEDOUT;
			goto finish;
		}
		mutex_lock(&port->lock);
		ret = port->shutdown_5v_status;
		mutex_unlock(&port->lock);
		if (ret)
			goto finish;
	}

	/* No TCPM mutex is held across a provider call, including swap_lock. */
	mutex_unlock(&port->swap_lock);
	mutex_lock(&port->lock);
	sequence = port->shutdown_sequence;
	mutex_unlock(&port->lock);
	for (;;) {
		mutex_lock(&port->lock);
		ret = tcpm_shutdown_contract_valid(port) &&
		      port->shutdown_sequence == sequence ? 0 : -EAGAIN;
		mutex_unlock(&port->lock);
		if (ret)
			break;
		if (time_after_eq(jiffies, deadline)) {
			ret = -ETIMEDOUT;
			break;
		}
		ret = read_vbus_uv(context, &uv);
		if (ret)
			break;
		mutex_lock(&port->lock);
		if (!tcpm_shutdown_contract_valid(port) ||
		    port->shutdown_sequence != sequence)
			ret = -EAGAIN;
		mutex_unlock(&port->lock);
		if (ret)
			break;
		if (time_after_eq(jiffies, deadline)) {
			ret = -ETIMEDOUT;
			break;
		}
		if (uv >= TCPM_SHUTDOWN_MIN_UV && uv <= TCPM_SHUTDOWN_MAX_UV)
			samples++;
		else
			samples = 0;
		if (samples == TCPM_SHUTDOWN_SAMPLES)
			break;
		msleep(TCPM_SHUTDOWN_SAMPLE_MS);
	}
	mutex_lock(&port->swap_lock);
	mutex_lock(&port->lock);
	if (!ret && (!tcpm_shutdown_contract_valid(port) ||
		     port->shutdown_sequence != sequence))
		ret = -EAGAIN;
	goto finish_locked;
finish:
	mutex_lock(&port->lock);
finish_locked:
	port->shutdown_5v_pending = false;
	port->shutdown_busy = false;
unlock:
	mutex_unlock(&port->lock);
	mutex_unlock(&port->swap_lock);
	return ret;
}

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
