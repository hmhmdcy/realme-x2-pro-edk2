/* Only kernel/device/PM/MMIO edges. Driver window/provider bodies follow. */
#define dev_warn(...) ((void)0)
#define lockdep_assert_held(m) assert((m)->held)
#define BIT(n) (1U << (n))
#define GENMASK(h,l) (((~0U)<<(l))&((~0U)>>(31-(h))))
#define __iomem
typedef int32_t s32;
struct regulator_bulk_data {int unused;};
struct phy_override_seq {bool need_update;u8 offset,value,mask;};
enum phy_mode {PHY_MODE_INVALID,PHY_MODE_USB_HOST,PHY_MODE_USB_DEVICE};
struct phy_ops {int unused;};
struct phy {struct mutex mutex;struct device dev;const struct phy_ops*ops;int init_count;};
static void mutex_destroy(struct mutex*m){assert(!m->held);}
struct completion {bool done;};
static void init_completion(struct completion*c){c->done=false;}
static void complete_all(struct completion*c){c->done=true;}
static void wait_for_completion(struct completion*c){assert(c->done);}
struct list_head {struct list_head *next,*prev;};
#define LIST_HEAD(n) struct list_head n={&n,&n}
static void INIT_LIST_HEAD(struct list_head*n){n->next=n->prev=n;}
static void list_add_tail(struct list_head*n,struct list_head*h){n->prev=h->prev;n->next=h;h->prev->next=n;h->prev=n;}
static void list_del_init(struct list_head*n){n->prev->next=n->next;n->next->prev=n->prev;INIT_LIST_HEAD(n);}
#define list_for_each_entry(p,h,m) for(struct list_head*_n=(h)->next;_n!=(h)&&((p)=container_of(_n,__typeof__(*(p)),m),true);_n=_n->next)
/* ACTUAL_PHY_TYPES */
static struct qcom_snps_hsphy phy_shadow;
static struct phy phy_hw;
static struct platform_device phy_platform;
static u32 phy_regs[64];
static int phy_reads,phy_writes,drop_phy_write,dwc_ends,dwc_cancels,eud_ends;
static bool phy_storage_live,unbind_on_phy_unlock;
static void*phy_get_drvdata(struct phy*p){assert(phy_storage_live);return p->dev.driverdata;}
static void*dev_get_drvdata(struct device*d){return d->driverdata;}
static u32 readl_relaxed(void*p){assert(phy_storage_live);size_t i=((uintptr_t)p-(uintptr_t)phy_regs)/4;assert(i<64);phy_reads++;return phy_regs[i];}
static void writel_relaxed(u32 v,void*p){assert(phy_storage_live);size_t i=((uintptr_t)p-(uintptr_t)phy_regs)/4;assert(i<64);phy_writes++;if(phy_writes!=drop_phy_write)phy_regs[i]=v;}
static void pm_runtime_put_noidle(struct device*d){assert(!phy_hw.mutex.held);assert(d->pm_refs>0);d->pm_refs--;}
static void pm_runtime_mark_last_busy(struct device*d){assert(!phy_hw.mutex.held);}
static void pm_runtime_put_autosuspend(struct device*d){pm_runtime_put_noidle(d);}
static int devm_add_action_or_reset(struct device*d,void(*f)(void*),void*data){d->cleanup=f;d->cleanup_data=data;return 0;}
/* ACTUAL_PHY_FUNCTIONS */
static void publish_phy(void){
 memset(&phy_shadow,0,sizeof(phy_shadow));memset(&phy_hw,0,sizeof(phy_hw));memset(&phy_platform,0,sizeof(phy_platform));memset(phy_regs,0,sizeof(phy_regs));
 phy_storage_live=true;phy_shadow.dev=&phy_platform.dev;phy_shadow.phy=&phy_hw;phy_shadow.base=phy_regs;phy_shadow.phy_initialized=true;phy_shadow.mode=PHY_MODE_USB_DEVICE;
 phy_hw.dev.driverdata=&phy_shadow;phy_platform.dev.driverdata=&phy_shadow;phy_hw.ops=&qcom_snps_hsphy_gen_ops;phy_hw.init_count=1;
 phy_regs[0x64/4]=0xa4;phy_regs[0x3c/4]=0xf0;phy_regs[0x94/4]=0xa2;
 assert(!qcom_hsphy_window_publish(&phy_shadow));
}
static void release_phy(void){
 if(phy_platform.dev.cleanup){void(*f)(void*)=phy_platform.dev.cleanup;void*data=phy_platform.dev.cleanup_data;phy_platform.dev.cleanup=NULL;f(data);}
 assert(!phy_platform.dev.pm_refs);phy_storage_live=false;
}
