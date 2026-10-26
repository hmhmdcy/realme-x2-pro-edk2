/* Actual complete pinned OEM functions; fake OS/register/PHY boundaries only. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define VENDOR_EDIT
#define BIT(n) (1u << (n))
#include "oem-registers.inc"
#define POWER_SUPPLY_TYPEC_SINK 3
#define POWER_SUPPLY_CONNECTOR_TYPEC 2
#define POWER_SUPPLY_TYPE_UNKNOWN 0
#define POWER_SUPPLY_TYPE_USB 1
#define POWER_SUPPLY_TYPE_USB_CDP 2
#define POWER_SUPPLY_TYPE_USB_DCP 3
#define IRQ_HANDLED 1
#define PR_MISC 0
#define PR_INTERRUPT 0
#define smblib_dbg(...) ((void)0)
#define smblib_err(...) ((void)0)
#define pr_info(...) ((void)0)
#define dev_dbg(...) ((void)0)
#define IS_ERR(p) ((intptr_t)(p)<0)
#define PTR_ERR(p) ((int)(intptr_t)(p))
typedef uint8_t u8;
typedef int irqreturn_t;
struct regulator { bool enabled; } regulator;
struct device { void *of_node; } device;
struct smb_charger { struct device *dev; struct regulator *dpdm_reg;
 bool pr_swap_in_progress,pd_active,fake_usb_insertion,uusb_apsd_rerun_done;
 int typec_mode,connector_type; void *usb_psy; };
struct smb_irq_data { struct smb_charger *parent_data; };
struct oppo_chg_chip {int vbatt_num;} chip={2},*g_oppo_chip=&chip;
struct apsd_result {int pst;} apsd_result;
union power_supply_propval {int intval;};
struct write_record {unsigned reg,mask,value;} writes[16],phy_writes[8];
static int nwrites,read_error,result_error,write_error,handled,notified,woke,reads;
static unsigned apsd_status,apsd_bits;
static int property=1,get_error,enable_error,disable_error,get_count,enables,disables,present=1,present_error;
static int smblib_masked_write(struct smb_charger *c,unsigned reg,unsigned mask,unsigned value)
{assert(nwrites<16);writes[nwrites++]=(struct write_record){reg,mask,value};return write_error;}
static int smblib_read(struct smb_charger *c,unsigned reg,u8 *value)
{reads++;if(read_error)return read_error;if(reg==APSD_RESULT_STATUS_REG&&result_error)return result_error;
 *value=reg==APSD_STATUS_REG?apsd_status:apsd_bits;return 0;}
static void *of_get_property(void *node,const char *name,void *len){return property?&property:NULL;}
static struct regulator *devm_regulator_get(struct device *dev,const char *name)
{get_count++;return get_error?(struct regulator *)(intptr_t)get_error:&regulator;}
static int regulator_is_enabled(struct regulator *r){return r->enabled;}
static int regulator_enable(struct regulator *r){enables++;if(enable_error)return enable_error;r->enabled=true;return 0;}
static int regulator_disable(struct regulator *r){disables++;if(disable_error)return disable_error;r->enabled=false;return 0;}
static int smblib_get_prop_usb_present(struct smb_charger *c,union power_supply_propval *v)
{v->intval=present;return present_error;}
static const struct apsd_result *smblib_get_apsd_result(struct smb_charger *c){return &apsd_result;}
static void smblib_handle_apsd_done(struct smb_charger *c,bool rising){if(rising)handled++;}
static void oppo_chg_wake_update_work(void){woke++;}
static void smblib_handle_hvdcp_detect_done(struct smb_charger*c,bool a){}
static void smblib_handle_hvdcp_check_timeout(struct smb_charger*c,bool a,bool b){}
static void smblib_handle_hvdcp_3p0_auth_done(struct smb_charger*c,bool a){}
static void smblib_handle_sdp_enumeration_done(struct smb_charger*c,bool a){}
static void smblib_handle_slow_plugin_timeout(struct smb_charger*c,bool a){}
static void smblib_hvdcp_adaptive_voltage_change(struct smb_charger*c){}
static void power_supply_changed(void *p){notified++;}
#include "tested-oem-smb.inc"

struct msm_hsphy {struct {void *dev;}phy;int phy_lock;bool dpdm_enable,cable_connected;void *base;};
struct regulator_dev {struct msm_hsphy *driver_data;};
static int lock_depth,power_error,power_calls,clock_calls,resets,phy_count,sequence[16],seq_count;
static void *rdev_get_drvdata(struct regulator_dev *r){return r->driver_data;}
static void mutex_lock(int *lock){assert(!lock_depth);lock_depth++;}
static void mutex_unlock(int *lock){assert(lock_depth==1);lock_depth--;}
static int msm_hsphy_enable_power(struct msm_hsphy *p,bool on)
{assert(lock_depth==1);power_calls++;sequence[seq_count++]=on?1:7;return power_error;}
static void msm_hsphy_enable_clocks(struct msm_hsphy *p,bool on)
{assert(lock_depth==1);clock_calls++;sequence[seq_count++]=on?2:6;}
static void msm_hsphy_reset(struct msm_hsphy *p){assert(lock_depth==1);resets++;sequence[seq_count++]=3;}
static void msm_usb_write_readback(void *base,unsigned reg,unsigned mask,unsigned value)
{assert(lock_depth==1&&phy_count<8);sequence[seq_count++]=4;phy_writes[phy_count++]=(struct write_record){reg,mask,value};}
#include "tested-oem-phy.inc"

static struct smb_charger fresh(void)
{
 nwrites=read_error=result_error=write_error=handled=notified=woke=reads=0;
 get_error=enable_error=disable_error=get_count=enables=disables=0;
 property=present=1;present_error=0;regulator.enabled=false;apsd_result.pst=POWER_SUPPLY_TYPE_USB;
 apsd_status=0x11;apsd_bits=1;chip.vbatt_num=2;
 return (struct smb_charger){.dev=&device,.connector_type=POWER_SUPPLY_CONNECTOR_TYPEC};
}
static void call_irq(struct smb_charger *c){struct smb_irq_data d={c};assert(usb_source_change_irq_handler(0,&d)==IRQ_HANDLED);}
static void test_typec_sdp_cdp_once(void)
{
 struct smb_charger c=fresh();call_irq(&c);
 assert(c.uusb_apsd_rerun_done&&nwrites==1&&handled==0&&notified==0);
 assert(writes[0].reg==0x1341&&writes[0].mask==1&&writes[0].value==1);
 /* Next completed result is consumed; this test does not predict its real value. */
 apsd_bits=4;call_irq(&c);assert(nwrites==1&&handled==1&&notified==1);
 c=fresh();apsd_bits=4;call_irq(&c);assert(c.uusb_apsd_rerun_done&&nwrites==1);
 c=fresh();apsd_bits=8;call_irq(&c);assert(!c.uusb_apsd_rerun_done&&nwrites==0&&handled==1);
}
static void test_role_pd_and_fake_gates(void)
{
 struct smb_charger c=fresh();c.pd_active=true;call_irq(&c);assert(!reads&&!nwrites&&!handled);
 c=fresh();c.fake_usb_insertion=true;call_irq(&c);assert(!reads&&!nwrites);
 c=fresh();c.typec_mode=POWER_SUPPLY_TYPEC_SINK;call_irq(&c);assert(!reads&&!nwrites);
 c=fresh();apsd_status=0;call_irq(&c);assert(!nwrites&&!handled);
}
static void test_original_errors_do_not_prove_complete_detection(void)
{
 struct smb_charger c=fresh();read_error=-5;call_irq(&c);assert(!nwrites&&!c.uusb_apsd_rerun_done);
 c=fresh();result_error=-5;call_irq(&c);assert(!nwrites&&!c.uusb_apsd_rerun_done&&handled==1);
 c=fresh();write_error=-5;call_irq(&c);assert(nwrites==1&&c.uusb_apsd_rerun_done&&handled==0);
 /* OEM marks rerun consumed before void write helper reports/logs failure. */
}
static void test_dpdm_actual_request_lifecycle(void)
{
 struct smb_charger c=fresh();c.pr_swap_in_progress=true;
 assert(smblib_request_dpdm(&c,true)==0&&!get_count&&!enables);
 c=fresh();property=0;assert(smblib_request_dpdm(&c,true)==0&&!get_count&&!enables);
 c=fresh();get_error=-19;assert(smblib_request_dpdm(&c,true)==-19&&!c.dpdm_reg);
 c=fresh();assert(smblib_request_dpdm(&c,true)==0&&get_count==1&&enables==1&&regulator.enabled);
 assert(smblib_request_dpdm(&c,true)==0&&enables==1);
 assert(smblib_request_dpdm(&c,false)==0&&disables==1&&!regulator.enabled);
 assert(smblib_request_dpdm(&c,false)==0&&disables==1);
 c=fresh();enable_error=-5;assert(smblib_request_dpdm(&c,true)==-5&&!regulator.enabled);
}
static void test_original_rerun_helper_preconditions_and_failure_gap(void)
{
 struct smb_charger c=fresh();present=0;assert(smblib_rerun_apsd_if_required(&c)==0&&!nwrites&&!enables);
 c=fresh();present_error=-5;assert(smblib_rerun_apsd_if_required(&c)==-5&&!nwrites);
 c=fresh();apsd_result.pst=POWER_SUPPLY_TYPE_USB_DCP;
 assert(smblib_rerun_apsd_if_required(&c)==0&&!nwrites&&!enables);
 c=fresh();assert(smblib_rerun_apsd_if_required(&c)==0&&nwrites==1&&enables==1&&c.uusb_apsd_rerun_done);
 c=fresh();enable_error=-5;assert(smblib_rerun_apsd_if_required(&c)==0&&nwrites==1&&!regulator.enabled);
 smblib_apsd_enable(&c,true);assert(writes[1].reg==0x1362&&writes[1].mask==8&&writes[1].value==8);
}
static void reset_phy(void){lock_depth=power_error=power_calls=clock_calls=resets=phy_count=seq_count=0;}
static void test_phy_high_z_order_and_lock(void)
{
 struct msm_hsphy p={0};struct regulator_dev d={&p};reset_phy();
 assert(msm_hsphy_dpdm_regulator_enable(&d)==0&&p.dpdm_enable&&!lock_depth);
 assert(power_calls==1&&clock_calls==1&&resets==1&&phy_count==3);
 assert(sequence[0]==1&&sequence[1]==2&&sequence[2]==3);
 assert(phy_writes[0].reg==0x64&&phy_writes[0].mask==0xc&&phy_writes[0].value==0xc);
 assert(phy_writes[1].reg==0x3c&&phy_writes[1].mask==0x18&&phy_writes[1].value==8);
 assert(phy_writes[2].reg==0x94&&phy_writes[2].mask==1&&phy_writes[2].value==1);
 assert(msm_hsphy_dpdm_regulator_is_enabled(&d)==1);
 assert(msm_hsphy_dpdm_regulator_enable(&d)==0&&phy_count==3&&power_calls==1);
}
static void test_phy_failure_and_release_with_connected_cable(void)
{
 struct msm_hsphy p={0};struct regulator_dev d={&p};reset_phy();power_error=-5;
 assert(msm_hsphy_dpdm_regulator_enable(&d)==-5&&!p.dpdm_enable&&!lock_depth&&phy_count==0);
 reset_phy();p.dpdm_enable=true;p.cable_connected=true;
 assert(msm_hsphy_dpdm_regulator_disable(&d)==0&&!p.dpdm_enable&&!power_calls&&!clock_calls&&!lock_depth);
 reset_phy();p.dpdm_enable=true;p.cable_connected=false;
 assert(msm_hsphy_dpdm_regulator_disable(&d)==0&&!p.dpdm_enable&&power_calls==1&&clock_calls==1&&!lock_depth);
 reset_phy();p.dpdm_enable=true;power_error=-5;
 assert(msm_hsphy_dpdm_regulator_disable(&d)==-5&&p.dpdm_enable&&!lock_depth);
}
int main(void)
{
 test_typec_sdp_cdp_once();test_role_pd_and_fake_gates();
 test_original_errors_do_not_prove_complete_detection();test_dpdm_actual_request_lifecycle();
 test_original_rerun_helper_preconditions_and_failure_gap();test_phy_high_z_order_and_lock();
 test_phy_failure_and_release_with_connected_cable();
 puts("7 focused groups passed: exact OEM Type-C rerun/DPDM/PHY functions; no hardware");return 0;
}
