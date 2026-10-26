/* Kernel/OF/MMIO/work boundaries only; actual whole owner and PD functions
 * are inserted below, never a second model of the bridge algorithm. */
/* PD_BOUNDARY */
typedef uint64_t u64;
typedef uint8_t u8;
#ifndef EPROBE_DEFER
#define EPROBE_DEFER 517
#endif
static bool config_client=true,config_builtin=true;
#define CONFIG_USB_DWC3_SAMURAI_APSD_PD5V_CLIENT 1
#define CONFIG_TYPEC_QCOM_PMIC 2
#define CONFIG_USB_DWC3_SAMURAI_APSD_OWNER 3
#define IS_ENABLED(x) ((x)==CONFIG_USB_DWC3_SAMURAI_APSD_PD5V_CLIENT?config_client:true)
#define IS_BUILTIN(x) (config_builtin)
#define EXPORT_SYMBOL_GPL(x)
#define READ_ONCE(x) (x)
#define NOTIFY_OK 0
#define PSY_EVENT_PROP_CHANGED 1
#define DWC3_GCTL_PRTCAP_DEVICE 2
#define msecs_to_jiffies(n) (n)
typedef int spinlock_t;
#define spin_lock_irqsave(l,f) do{(void)(l);(f)=0;}while(0)
#define spin_unlock_irqrestore(l,f) do{(void)(l);(void)(f);}while(0)
static void spin_lock_init(spinlock_t *p){*p=0;}
static bool kref_get_unless_zero(struct kref *r){if(!r->refs)return false;r->refs++;return true;}
struct platform_device {struct device dev;};
struct work_struct {void (*fn)(struct work_struct *);};
struct delayed_work {struct work_struct work;bool pending;};
#define to_delayed_work(w) container_of(w,struct delayed_work,work)
#define INIT_DELAYED_WORK(w,f) do{(w)->work.fn=(f);(w)->pending=false;}while(0)
static int system_wq,queued,joins,notifiers;
static void (*join_hook)(void);
static void mod_delayed_work(int q,struct delayed_work *w,unsigned long delay)
{(void)q;(void)delay;queued++;w->pending=true;}
static void cancel_delayed_work_sync(struct delayed_work *w)
{joins++;if(join_hook)join_hook();w->pending=false;}
struct notifier_block {int (*notifier_call)(struct notifier_block*,unsigned long,void*);};
struct power_supply_desc {const char *name;};
struct power_supply {const struct power_supply_desc *desc;};
static int power_supply_reg_notifier(struct notifier_block *p){(void)p;notifiers++;return 0;}
static void power_supply_unreg_notifier(struct notifier_block *p){(void)p;notifiers--;}
static int device_property_read_bool(struct device *d,const char *p)
{return !strcmp(p,"samurai,apsd-owner")?d->optin:d->bridge;}
static int pm_runtime_get_if_active(struct device *d){if(d->suspended)return 0;d->pm_refs++;return 1;}
static void pm_runtime_put(struct device *d){assert(d->pm_refs>0);d->pm_refs--;}
static struct regmap *dev_get_regmap(struct device *d,const char *name){(void)name;return d?d->map:NULL;}
static struct platform_device tcpc;
static bool phandle_present=true,platform_present=true;
static struct platform_device *of_find_device_by_node(struct device_node *n)
{assert(n==tcpc.dev.of_node);if(!platform_present)return NULL;get_device(&tcpc.dev);return &tcpc;}
/* ACTUAL_HEADERS */
/* WINDOW_TYPES */
struct phy {int unused;};
struct dwc3 {
 struct device *dev;struct phy *usb2_generic_phy[1];void *gadget_driver;
};
static int analog_calls,APSD_writes,restore_error;
int eud_com_quiet_begin(struct eud_com_window_result *r){analog_calls++;r->cookie=1;return 0;}
int eud_com_quiet_end(u64 c,struct eud_com_window_result *r){(void)c;r->restored=true;return 0;}
int dwc3_gadget_window_begin(struct dwc3 *d,struct dwc3_gadget_window_result *r)
{(void)d;analog_calls++;r->cookie=2;r->halted=true;return 0;}
int dwc3_gadget_window_cancel(struct dwc3 *d,u64 c,struct dwc3_gadget_window_result *r)
{(void)d;(void)c;(void)r;return 0;}
int dwc3_gadget_window_end(struct dwc3 *d,u64 c,struct dwc3_gadget_window_result *r)
{(void)d;(void)c;(void)r;return 0;}
int qcom_snps_hsphy_window_begin(struct phy *p,struct qcom_snps_hsphy_window_result *r)
{(void)p;analog_calls++;r->cookie=3;r->high_z=true;return 0;}
int qcom_snps_hsphy_window_end(struct phy *p,u64 c,struct qcom_snps_hsphy_window_result *r)
{(void)p;(void)c;(void)r;return restore_error;}
/* ACTUAL_PD */
/* ACTUAL_OWNER */
static struct device host,source,pmic;
static struct dwc3 dwc;
static struct samurai_pd5v *pd;
static u64 serial;
static int source_error;
static bool unbind_on_pd_unlock;
static bool revoke_after_acquire;
static int abort_at;
static bool replace_after_status;
static void context_unlock_hook(struct mutex *m)
{
 if(unbind_on_pd_unlock && pd && m==&pd->lock){
  unbind_on_pd_unlock=false;
  dwc3_apsd_owner_unbind(&dwc);
 }
 if(revoke_after_acquire && pd && pd->leased && m==&pd->lock){
  revoke_after_acquire=false;
  /* Cut at the real PM quiesce publication boundary. Its join cannot
   * finish until this running worker returns; invoke that tail below. */
  pd->blocked=true;pd->generation++;
 }
 if(abort_at==2 && pd && m==&pd->lock && !pd->leased){abort_at=0;bound_owner->abort=true;}
 if(abort_at==3 && pd && m==&pd->lock && pd->leased){abort_at=0;bound_owner->abort=true;}
 if(replace_after_status && pd && m==&pd->lock && !pd->leased){
  replace_after_status=false;struct samurai_pd5v *old=pd;
  samurai_pd5v_destroy(old);pd=samurai_pd5v_create(&tcpc.dev,&map);assert(!IS_ERR(pd));
 }
}
static int source_sample(void *ctx,struct samurai_apsd_bus_sample *s)
{
 assert(ctx==&source);if(source_error)return source_error;
 const unsigned int addr[]={0x1307,0x1308,0x1310,0x1506,0x1509,0x150b,0x150d};
 for(unsigned int i=0;i<7;i++)s->raw[i]=map.raw[addr[i]];
 s->present=!!(map.raw[0x1310]&0x10);s->serial=++serial;return 0;
}
static int no_rerun(void *ctx,u64 epoch){(void)ctx;(void)epoch;APSD_writes++;assert(!"1341 is prohibited");return -EOPNOTSUPP;}
static const struct samurai_apsd_bus_ops bus={source_sample,no_rerun};
static void wire(bool on)
{
 map.raw[0x1307]=on?0x11:0;map.raw[0x1308]=on?1:0;
 map.raw[0x1310]=on?0x10:0;map.raw[0x1506]=on?8:0;
 map.raw[0x1509]=on?0x23:0;map.raw[0x150b]=on?0x29:0;map.raw[0x150d]=on?6:0;
 map.raw[0x150a]=on?0x20:0x40;
}
static void setup(bool bridge)
{
 assert(!bound_owner&&!bus_dev&&!pd5v_bound&&!module_refs&&!rail.refs&&!notifiers);
 memset(&host,0,sizeof(host));memset(&source,0,sizeof(source));memset(&pmic,0,sizeof(pmic));
 memset(&tcpc,0,sizeof(tcpc));memset(&dwc,0,sizeof(dwc));memset(&map,0,sizeof(map));memset(&rail,0,sizeof(rail));
 memset(&protocol_history,0,sizeof(protocol_history));pd_history_binding=0;pd_history_prepared=false;
 going=reads=writes=fail_read_at=fail_write_at=write_took_effect=mismatch_readback=attach_after_write=slow_read_at=power_enable_error=attach_on_power=free_count=0;
 serial=0;clock_ms=1000;source_error=analog_calls=APSD_writes=restore_error=queued=joins=0;
 config_client=config_builtin=phandle_present=platform_present=true;join_hook=NULL;unbind_on_pd_unlock=revoke_after_acquire=replace_after_status=false;abort_at=0;
 host.optin=true;host.bridge=bridge;host.of_node=&phy_node;source.parent=tcpc.dev.parent=&pmic;
 pmic.map=&map;tcpc.dev.of_node=&other_node;dwc.dev=&host;dwc.gadget_driver=&host;
 map.raw[0x1544]=2;map.raw[0x1362]=0x18;
 map.raw[0x174e]=0x88;map.raw[0x1744]=0x23;map.raw[0x174c]=0x21;map.raw[0x1746]=1;wire(false);
 pd=samurai_pd5v_create(&tcpc.dev,&map);assert(!IS_ERR(pd));
 dwc3_apsd_owner_bind(&dwc);assert(bound_owner);
 assert(!samurai_apsd_bus_register(&source,&bus,&source));
}
static void tick(void){clock_ms+=1000;bound_owner->work.pending=false;owner_work(&bound_owner->work.work);}
static void teardown(void)
{
 if(bound_owner)dwc3_apsd_owner_unbind(&dwc);
 samurai_apsd_bus_unregister(&source,&source);samurai_pd5v_destroy(pd);pd=NULL;
 assert(!bound_owner&&!bus_dev&&!pd5v_bound&&!module_refs&&!notifiers&&!rail.refs&&!tcpc.dev.refs&&!host.pm_refs);
 assert(!APSD_writes&&!analog_calls);
}
static void prepared(void){tick();assert(pd->initialized&&bound_owner->pd_prepared&&bound_owner->pd_lease.owner);assert(writes==4);}
int main(void)
{
 setup(false);wire(true);tick();assert(!reads&&!writes&&!bound_owner->pd_lease.owner);assert(bound_owner->once.phase==SAMURAI_APSD_READY);teardown();
 setup(true);config_builtin=false;tick();assert(bound_owner->primary_error==-EOPNOTSUPP&&!reads&&!writes);teardown();
 setup(true);config_client=false;tick();assert(bound_owner->primary_error==-EOPNOTSUPP&&!reads&&!writes);teardown();puts("1 default and builtin/config gates give zero PD/analog/APSD I/O");
 setup(true);wire(true);tick();assert(bound_owner->pd_phase==OWNER_PD_WAIT_FIRST_OFF&&!bound_owner->once.epoch&&!reads&&!writes);
 wire(false);prepared();u64 binding=pd->binding_id;assert(bound_owner->pd_phase==OWNER_PD_WAIT_ATTACH&&bound_owner->ref.refs==2);
 wire(true);tick();assert(bound_owner->once.phase==SAMURAI_APSD_READY&&bound_owner->once.epoch==1&&bound_owner->pd_phase==OWNER_PD_SINK_EPOCH);
 assert(bound_owner->primary_error==-EOPNOTSUPP&&!bound_owner->once.attempted&&writes==4&&pd->binding_id==binding);teardown();puts("2 real off acquire precedes new sink epoch; remaining gate forbids every command/window");
 setup(true);source.parent=&host;tick();assert(bound_owner->pd_error==-EXDEV&&!reads&&!writes);teardown();
 setup(true);pmic.map=NULL;tick();assert(bound_owner->pd_error==-EXDEV&&!reads&&!writes);teardown();
 setup(true);phandle_present=false;tick();assert(bound_owner->pd_phase==OWNER_PD_FAILED&&!reads&&!writes);teardown();
 setup(true);platform_present=false;tick();assert(bound_owner->work.pending&&!reads&&!writes);platform_present=true;prepared();teardown();puts("3 actual parent/regmap/phandle and deferred binding are checked before PD I/O");
 setup(true);samurai_pd5v_destroy(pd);pd=NULL;wire(true);tick();assert(bound_owner->pd_phase==OWNER_PD_WAIT_BINDING&&bound_owner->work.pending&&!writes);
 pd=samurai_pd5v_create(&tcpc.dev,&map);assert(!IS_ERR(pd));tick();assert(bound_owner->pd_phase==OWNER_PD_WAIT_FIRST_OFF&&!writes);wire(false);prepared();teardown();
 setup(true);prepared();wire(true);map.raw[0x1506]=1;tick();assert(!bound_owner->once.epoch&&bound_owner->pd_lease.owner);map.raw[0x1506]=8;tick();u64 epoch=bound_owner->once.epoch;
 bound_owner->once.attempted=1;bound_owner->once.phase=SAMURAI_APSD_CANCELLED;
 wire(false);tick();assert(bound_owner->once.phase==SAMURAI_APSD_DETACHED);wire(true);tick();assert(bound_owner->once.epoch==epoch+1&&!bound_owner->once.attempted&&writes==4);teardown();puts("4 strict sink qualification and true detach reset are distinct from PD control history");
 setup(true);prepared();wire(true);tick();epoch=bound_owner->once.epoch;bound_owner->once.attempted=1;bound_owner->once.phase=SAMURAI_APSD_CANCELLED;
 assert(!dwc3_apsd_owner_pause(&dwc,DWC3_APSD_SYSTEM));assert(!pd->leased&&bound_owner->ref.refs==1&&bound_owner->pd_prepared);
 assert(!samurai_pd5v_quiesce(pd));samurai_pd5v_complete(pd);dwc3_apsd_owner_resume(&dwc,DWC3_APSD_SYSTEM);tick();
 assert(bound_owner->once.epoch==epoch&&bound_owner->once.attempted&&bound_owner->pd_lease.owner&&writes==4);teardown();puts("5 PM release/reacquire preserves actual control and physical attempt histories");
 setup(true);prepared();wire(true);tick();epoch=bound_owner->once.epoch;
 assert(!samurai_pd5v_quiesce(pd));assert(pd->blocked&&!pd->leased&&bound_owner->ref.refs==1&&bound_owner->work.pending);
 int n=reads;tick();assert(reads==n&&!pd->leased);samurai_pd5v_complete(pd);tick();
 assert(pd->leased&&bound_owner->once.epoch==epoch&&writes==4);teardown();puts("6 real PD quiesce invokes actual client join/release; complete only revalidates");
 setup(true);revoke_after_acquire=true;tick();assert(pd->blocked&&pd->leased&&bound_owner->pd_phase==OWNER_PD_WAIT_BINDING&&!pd->error);
 assert(!samurai_pd5v_quiesce(pd));samurai_pd5v_complete(pd);tick();assert(bound_owner->pd_phase==OWNER_PD_WAIT_ATTACH&&pd->leased&&writes==4);teardown();
 setup(true);prepared();wire(true);tick();epoch=bound_owner->once.epoch;bound_owner->once.attempted=1;bound_owner->once.phase=SAMURAI_APSD_CANCELLED;
 dwc3_apsd_owner_unbind(&dwc);assert(!pd->leased&&!bound_owner);dwc3_apsd_owner_bind(&dwc);tick();
 assert(bound_owner->pd_prepared&&bound_owner->once.epoch==epoch&&bound_owner->once.attempted&&writes==4);
 binding=pd->binding_id;dwc3_apsd_owner_unbind(&dwc);samurai_pd5v_destroy(pd);pd=samurai_pd5v_create(&tcpc.dev,&map);assert(!IS_ERR(pd)&&pd->binding_id>binding);
 dwc3_apsd_owner_bind(&dwc);tick();assert(bound_owner->pd_phase==OWNER_PD_WAIT_FIRST_OFF&&bound_owner->once.epoch==epoch&&bound_owner->once.attempted&&writes==4);
 wire(false);tick();assert(pd->initialized&&writes==8);wire(true);tick();assert(bound_owner->once.epoch==epoch+1&&!bound_owner->once.attempted);teardown();puts("7 UDC rebind cannot rearm; replaced PD binding requires another real off");
 setup(true);prepared();wire(true);tick();epoch=bound_owner->once.epoch;bound_owner->once.attempted=1;bound_owner->once.phase=SAMURAI_APSD_CANCELLED;
 samurai_apsd_bus_unregister(&source,&source);assert(!pd->leased&&!bound_owner->bus&&!bound_owner->work.pending);serial=0;
 assert(!samurai_apsd_bus_register(&source,&bus,&source));tick();assert(bound_owner->once.epoch==epoch&&bound_owner->once.attempted);
 wire(false);tick();wire(true);tick();assert(bound_owner->once.epoch==epoch+1&&!bound_owner->once.attempted);teardown();puts("8 backend withdrawal joins/releases; new serial cannot bypass physical history");
 setup(true);fail_write_at=2;write_took_effect=1;tick();assert(bound_owner->pd_phase==OWNER_PD_FAILED&&pd->error==-ETIMEDOUT&&writes==2&&!pd->leased&&bound_owner->ref.refs==1);
 fail_write_at=0;samurai_pd5v_complete(pd);wire(true);tick();wire(false);tick();assert(writes==2&&bound_owner->pd_error==-ETIMEDOUT);teardown();puts("9 partial/unknown control failure is retained, not retried after resume or detach");
 setup(true);prepared();unbind_on_pd_unlock=true;assert(!samurai_pd5v_quiesce(pd));assert(!bound_owner&&!pd->leased&&!notifiers&&tcpc.dev.refs==1);teardown();puts("10 real quiesce pin survives concurrent DWC unbind and frees owner only after callback put");
 setup(true);prepared();bound_owner->blocked|=DWC3_APSD_SYSTEM;assert(!samurai_pd5v_quiesce(pd));assert(bound_owner->blocked==DWC3_APSD_SYSTEM&&!bound_owner->work.pending);teardown();puts("11 PD callback cannot clear another PM fence or enqueue after join");
 setup(true);struct samurai_pd5v_status st={0};int nread=reads,nwrite=writes;assert(!qcom_pmic_typec_5v_status(&tcpc.dev,&source,&st)&&st.binding_id&&!st.initialized&&!st.error);
 assert(qcom_pmic_typec_5v_status(&host,&source,&st)==-ENODEV);assert(qcom_pmic_typec_5v_status(NULL,&source,&st)==-EINVAL);
 pd->blocked=true;pd->error=-EOWNERDEAD;assert(!qcom_pmic_typec_5v_status(&tcpc.dev,&source,&st)&&st.blocked&&st.error==-EOWNERDEAD);assert(reads==nread&&writes==nwrite);pd->error=0;pd->blocked=false;teardown();puts("12 new actual metadata API is zero I/O, bound and error-preserving");
 setup(true);dwc3_apsd_owner_unbind(&dwc);samurai_apsd_bus_unregister(&source,&source);samurai_pd5v_destroy(pd);pd=NULL;
 u64 saved_serial=pd5v_binding_serial;pd5v_binding_serial=~0ULL;pd=samurai_pd5v_create(&tcpc.dev,&map);assert(IS_ERR(pd)&&PTR_ERR(pd)==-EOVERFLOW&&!pd5v_bound&&!tcpc.dev.refs&&!writes&&!reads);pd=NULL;pd5v_binding_serial=saved_serial;
 setup(true);abort_at=2;tick();assert(!reads&&!writes&&!pd->leased&&bound_owner->primary_error==-ECANCELED);teardown();
 setup(true);abort_at=3;tick();assert(pd->initialized&&pd->leased&&bound_owner->pd_prepared&&bound_owner->primary_error==-ECANCELED&&writes==4);
 assert(!dwc3_apsd_owner_pause(&dwc,DWC3_APSD_SYSTEM));assert(!pd->leased&&bound_owner->pd_prepared);teardown();puts("13 cancellation before acquire gives zero PD I/O; a joined in-flight success retains its off history and releases");
 setup(true);replace_after_status=true;tick();assert(pd->initialized&&!pd->leased&&!bound_owner->pd_prepared&&bound_owner->pd_error==-ESTALE&&writes==4);
 tick();assert(pd->leased&&bound_owner->pd_prepared&&writes==4);wire(true);tick();assert(bound_owner->once.epoch==1&&writes==4);teardown();puts("14 actual remove/reprobe between metadata and acquire cannot inherit the old binding history");
 return 0;
}
