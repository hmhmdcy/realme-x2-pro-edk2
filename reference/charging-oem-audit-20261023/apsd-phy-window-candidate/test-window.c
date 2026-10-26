/* Actual extracted functions. No device access or simulated actual packet. */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define __iomem
#define __maybe_unused
#define ENOTSUPP 524
#define BIT(n) (1U << (n))
#define GENMASK(h,l) (((~0U)<<(l))&((~0U)>>(31-(h))))
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define lockdep_assert_held(m) assert(*(m)==1)
#define EXPORT_SYMBOL_GPL(x)
#define dev_warn(...) ((void)0)
#define dev_err(...) ((void)0)
#define dev_dbg(...) ((void)0)
#define dev_vdbg(...) ((void)0)
typedef uint64_t u64;typedef uint32_t u32;typedef uint8_t u8;typedef int32_t s32;
enum phy_mode {PHY_MODE_INVALID,PHY_MODE_USB_HOST,PHY_MODE_USB_DEVICE};
struct device {void *data;};
struct phy;
struct phy_ops {int(*init)(struct phy*);int(*exit)(struct phy*);int(*set_mode)(struct phy*,enum phy_mode,int);void *owner;};
struct phy {struct device dev;const struct phy_ops *ops;int mutex,init_count,power_count;struct {enum phy_mode mode;} attrs;};
struct clk_bulk_data {int dummy;};struct reset_control {int dummy;};struct regulator_bulk_data {int dummy;};
struct phy_override_seq {bool need_update;u8 offset,value,mask;};
#include "tested-types.inc"
static struct qcom_snps_hsphy *current;
static u32 regs[64];
static int refs,pm_result,pm_gets,pm_puts,reads,writes,drop_write,reset_calls,clock_on,clock_off,power_on,power_off;
static u32 write_offsets[64];
static void (*get_hook)(void);
static void mutex_lock(int *m){assert(!*m);++*m;}
static void mutex_unlock(int *m){assert(*m==1);--*m;}
static void *phy_get_drvdata(struct phy *p){return p->dev.data;}
static void *dev_get_drvdata(struct device *p){return p->data;}
static int pm_runtime_get_if_active(struct device *dev)
{assert(!current->phy->mutex);pm_gets++;if(get_hook){void(*h)(void)=get_hook;get_hook=NULL;h();}if(pm_result>0)refs++;return pm_result;}
static void pm_runtime_put_noidle(struct device *dev){assert(!current->phy->mutex&&refs>0);refs--;pm_puts++;}
static void pm_runtime_mark_last_busy(struct device *dev){assert(!current->phy->mutex);}
static void pm_runtime_put_autosuspend(struct device *dev){pm_runtime_put_noidle(dev);}
static int phy_pm_runtime_get_sync(struct phy *p){assert(!p->mutex);return 0;}
static void phy_pm_runtime_put(struct phy *p){assert(!p->mutex);}
static u32 readl_relaxed(void *p)
{size_t i=((uintptr_t)p-(uintptr_t)current->base)/4;assert(i<64);reads++;return regs[i];}
static void writel_relaxed(u32 value,void *p)
{size_t i=((uintptr_t)p-(uintptr_t)current->base)/4;assert(i<64&&writes<64);write_offsets[writes++]=i*4;if(writes!=drop_write)regs[i]=value;}
static int regulator_bulk_enable(int n,struct regulator_bulk_data *v){power_on++;return 0;}
static int regulator_bulk_disable(int n,struct regulator_bulk_data *v){power_off++;return 0;}
static int clk_bulk_prepare_enable(int n,struct clk_bulk_data *c){clock_on++;return 0;}
static void clk_bulk_disable_unprepare(int n,struct clk_bulk_data *c){clock_off++;}
static int reset_control_assert(struct reset_control *r){reset_calls++;return 0;}
static int reset_control_deassert(struct reset_control *r){reset_calls++;return 0;}
static void usleep_range(unsigned int a,unsigned int b){}
#include "tested-functions.inc"
static const struct phy_ops qcom_snps_hsphy_gen_ops = {
 .init=qcom_snps_hsphy_init,.exit=qcom_snps_hsphy_exit,.set_mode=qcom_snps_hsphy_set_mode};
static struct phy phy;
static struct device dev;
static void setup(struct qcom_snps_hsphy *h)
{
 memset(h,0,sizeof(*h));memset(&phy,0,sizeof(phy));memset(regs,0,sizeof(regs));
 current=h;h->dev=&dev;dev.data=h;h->phy=&phy;h->base=(void*)regs;
 h->phy_initialized=true;h->mode=PHY_MODE_USB_DEVICE;phy.dev.data=h;phy.ops=&qcom_snps_hsphy_gen_ops;phy.init_count=1;
 refs=pm_gets=pm_puts=reads=writes=drop_write=reset_calls=clock_on=clock_off=power_on=power_off=0;pm_result=1;get_hook=NULL;
 regs[0x64/4]=0xa4;regs[0x3c/4]=0xf0;regs[0x94/4]=0xa2;
}
static void done(const char *name){assert(!refs&&!phy.mutex);printf("ok: %s\n",name);}
static struct qcom_snps_hsphy_window_result begin(void)
{struct qcom_snps_hsphy_window_result r;assert(qcom_snps_hsphy_window_begin(&phy,&r)==0&&r.high_z&&r.cookie&&refs==1);return r;}
static void test_exact_entry_restore(void)
{
 struct qcom_snps_hsphy h;setup(&h);struct qcom_snps_hsphy_window_result r=begin(),end;
 assert(r.attempted==7&&r.verified==7&&r.saved[0]==4&&r.saved[1]==0x10&&r.saved[2]==0);
 assert(writes==3&&write_offsets[0]==0x64&&write_offsets[1]==0x3c&&write_offsets[2]==0x94);
 assert(regs[0x64/4]==0xac&&regs[0x3c/4]==0xe8&&regs[0x94/4]==0xa3);
 regs[0x64/4]^=BIT(31); /* independently changed non-owned bit is preserved */
 assert(qcom_snps_hsphy_window_end(&phy,r.cookie,&end)==0&&end.restored&&end.restored_mask==7&&!end.high_z);
 assert(writes==6&&write_offsets[3]==0x94&&write_offsets[4]==0x3c&&write_offsets[5]==0x64);
 assert(regs[0x64/4]==(0xa4|BIT(31))&&regs[0x3c/4]==0xf0&&regs[0x94/4]==0xa2);
 assert(!reset_calls&&!clock_on&&!power_on&&pm_puts==1);
 done("OEM three writes; exact old masked restore and unrelated-bit preservation");
}
static void test_rejections(void)
{
 struct qcom_snps_hsphy h;struct qcom_snps_hsphy_window_result r;setup(&h);pm_result=0;
 assert(qcom_snps_hsphy_window_begin(&phy,&r)==-EAGAIN&&!r.cookie&&!writes);
 pm_result=-EINVAL;assert(qcom_snps_hsphy_window_begin(&phy,&r)==-EINVAL);
 pm_result=1;h.phy_initialized=false;assert(qcom_snps_hsphy_window_begin(&phy,&r)==-EAGAIN&&!refs);
 h.phy_initialized=true;phy.init_count=0;assert(qcom_snps_hsphy_window_begin(&phy,&r)==-EAGAIN&&!refs);
 phy.init_count=1;h.mode=PHY_MODE_USB_HOST;assert(qcom_snps_hsphy_window_begin(&phy,&r)==-EOPNOTSUPP&&!refs);
 phy.ops=NULL;assert(qcom_snps_hsphy_window_begin(&phy,&r)==-ENODEV);
 assert(!writes&&!reset_calls&&!clock_on&&!power_on);
 done("no resume/init/reset for inactive/uninitialized/wrong PHY or mode");
}
static void test_cookie(void)
{
 struct qcom_snps_hsphy h;setup(&h);struct qcom_snps_hsphy_window_result r=begin(),x;
 assert(qcom_snps_hsphy_window_begin(&phy,&x)==-EBUSY&&refs==1&&!x.cookie&&h.window.cookie==r.cookie);
 assert(qcom_snps_hsphy_window_end(&phy,r.cookie+1,&x)==-ESTALE&&refs==1&&writes==3);
 assert(!qcom_snps_hsphy_window_end(&phy,r.cookie,&x));
 assert(qcom_snps_hsphy_window_end(&phy,r.cookie,&x)==-ESTALE&&!refs);
 x=begin();assert(x.cookie>r.cookie);assert(!qcom_snps_hsphy_window_end(&phy,x.cookie,&r));
 done("single owner stale/double tokens and generation");
}
static void test_enter_failures(void)
{
 for(int step=1;step<=3;step++) {
  struct qcom_snps_hsphy h;setup(&h);drop_write=step;struct qcom_snps_hsphy_window_result r,x;
  assert(qcom_snps_hsphy_window_begin(&phy,&r)==-EIO&&r.cookie&&!r.high_z&&refs==1);
  assert(r.enter_error==-EIO&&r.state==QCOM_HSPHY_WINDOW_FAILED&&writes==step);
  assert(r.saved[0]==4&&r.saved[1]==0x10&&r.saved[2]==0);
  drop_write=0;assert(!qcom_snps_hsphy_window_end(&phy,r.cookie,&x)&&x.restored&&x.enter_error==-EIO&&!x.restore_error);
  assert(regs[0x64/4]==0xa4&&regs[0x3c/4]==0xf0&&regs[0x94/4]==0xa2&&!refs);
 }
 done("each enter readback failure retains all originals and PM ref");
}
static void test_restore_failures(void)
{
 for(int step=4;step<=6;step++) {
  struct qcom_snps_hsphy h;setup(&h);struct qcom_snps_hsphy_window_result r=begin(),x;drop_write=step;
  assert(qcom_snps_hsphy_window_end(&phy,r.cookie,&x)==-EIO&&refs==1&&h.window_pm_ref);
  assert(!x.high_z&&!x.restored&&x.restore_error==-EIO&&!x.enter_error&&x.state==QCOM_HSPHY_WINDOW_FAILED);
  assert(qcom_snps_hsphy_window_begin(&phy,&r)==-EBUSY&&refs==1);
  drop_write=0;assert(!qcom_snps_hsphy_window_end(&phy,x.cookie,&r)&&r.restored&&!refs);
 }
 done("each reverse restore failure stays owned; explicit retry only");
}
static void test_generic_lifecycle(void)
{
 struct qcom_snps_hsphy h;setup(&h);struct qcom_snps_hsphy_window_result r=begin(),x;int old=writes;
 assert(!phy_init(&phy)&&phy.init_count==2&&!reset_calls&&!clock_on&&!power_on);
 assert(!phy_exit(&phy)&&phy.init_count==1&&!reset_calls&&!clock_off&&!power_off&&writes==old);
 assert(phy_exit(&phy)==-EBUSY&&phy.init_count==1&&!reset_calls&&!clock_off&&!power_off);
 assert(phy_set_mode_ext(&phy,PHY_MODE_USB_HOST,17)==-EBUSY&&h.mode==PHY_MODE_USB_DEVICE&&phy.attrs.mode==PHY_MODE_INVALID);
 assert(qcom_snps_hsphy_runtime_suspend(&dev)==-EBUSY&&qcom_snps_hsphy_runtime_resume(&dev)==-EBUSY&&writes==old);
 assert(qcom_snps_hsphy_init(&phy)==-EBUSY&&!reset_calls&&!clock_on&&!power_on);
 assert(!qcom_snps_hsphy_window_end(&phy,r.cookie,&x));
 assert(!phy_set_mode_ext(&phy,PHY_MODE_USB_HOST,0)&&h.mode==PHY_MODE_USB_HOST&&phy.attrs.mode==PHY_MODE_USB_HOST);
 assert(!phy_exit(&phy)&&!phy.init_count&&!h.phy_initialized&&reset_calls==1&&clock_off==1&&power_off==1);
 done("actual generic exit/mode preserve snapshot while owned; inactive defaults return");
}
static void test_idle_defaults(void)
{
 struct qcom_snps_hsphy h;setup(&h);h.phy_initialized=false;phy.init_count=0;
 assert(!phy_init(&phy)&&h.phy_initialized&&phy.init_count==1&&reset_calls==2&&clock_on==1&&power_on==1);
 int old=writes;assert(!qcom_snps_hsphy_runtime_suspend(&dev)&&!qcom_snps_hsphy_runtime_resume(&dev)&&writes==old);
 assert(!phy_exit(&phy)&&!phy.init_count&&!h.phy_initialized&&reset_calls==3);
 done("ordinary init/reset/exit and device runtime callbacks retain original behavior");
}
static void exit_before_claim(void){assert(!phy_exit(&phy));}
static void test_claim_race(void)
{
 struct qcom_snps_hsphy h;setup(&h);struct qcom_snps_hsphy_window_result r;
 get_hook=exit_before_claim;
 assert(qcom_snps_hsphy_window_begin(&phy,&r)==-EAGAIN&&!r.cookie&&!refs&&!writes);
 assert(reset_calls==1&&!h.phy_initialized&&!phy.init_count);
 done("exit wins before generic mutex claim; begin never touches MMIO");
}
int main(void)
{test_exact_entry_restore();test_rejections();test_cookie();test_enter_failures();test_restore_failures();test_generic_lifecycle();test_idle_defaults();test_claim_race();return 0;}
