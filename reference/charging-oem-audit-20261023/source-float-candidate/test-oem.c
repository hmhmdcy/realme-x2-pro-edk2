/* Verbatim OEM functions with fake votes/read boundaries, no PMIC operations. */
#include <stdbool.h>
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#define POWER_SUPPLY_TYPE_USB_FLOAT 1
#define POWER_SUPPLY_TYPE_USB 2
#define POWER_SUPPLY_CONNECTOR_TYPEC 3
#define FLOAT_OPTIONS_MASK 3
#define FORCE_FLOAT_SDP_CFG_BIT 1
#define USBIN_500MA 500000
#define SDP_CURRENT_UA 500000
#define DCP_CURRENT_UA 1500000
#define USBIN_25MA 25000
#define SW_ICL_MAX_VOTER 1
#define USB_PSY_VOTER 2
#define PD_SUSPEND_SUPPORTED_VOTER 3
#define smblib_err(...) ((void)0)
#define pr_err(...) ((void)0)
union power_supply_propval { int intval; };
struct smb_charger { int real_charger_type, float_cfg, connector_type; bool pd_active, system_suspend_supported; void *usb_icl_votable; };
static struct { int present, read_error, vote_count, requested, voter, enabled, set_sdp; } fake;
static int smblib_get_prop_usb_present(struct smb_charger *c, union power_supply_propval *v) { (void)c; v->intval = fake.present; return fake.read_error; }
static int smblib_get_prop_typec_mode(struct smb_charger *c) { (void)c; return 0; }
static int get_rp_based_dcp_current(struct smb_charger *c, int mode) { (void)c; (void)mode; return 1500000; }
static int set_sdp_current(struct smb_charger *c, int ua) { (void)c; fake.set_sdp = ua; return 0; }
static bool is_flash_active(struct smb_charger *c) { (void)c; return false; }
static int vote(void *v, int voter, bool enabled, int ua) { (void)v; fake.vote_count++; if (voter == USB_PSY_VOTER || voter == PD_SUSPEND_SUPPORTED_VOTER || enabled) { fake.requested = ua; fake.voter = voter; fake.enabled = enabled; } return 0; }
#include "oem-functions.inc"
static int checks;
#define CHECK(x) do { assert(x); checks++; } while (0)
static void reset(void) { fake = (typeof(fake)){ .present = 1 }; }
int main(void) {
    struct smb_charger c;
    union power_supply_propval v;
    int ua[] = { 0, 2000, 100000, 500000 };
    for (unsigned i = 0; i < sizeof(ua)/sizeof(ua[0]); i++) {
        reset(); c = (struct smb_charger){ .real_charger_type = POWER_SUPPLY_TYPE_USB_FLOAT };
        v.intval = ua[i]; CHECK(smblib_set_prop_sdp_current_max(&c, &v) == 0);
        CHECK(c.real_charger_type == POWER_SUPPLY_TYPE_USB && fake.requested == ua[i] && fake.voter == USB_PSY_VOTER && fake.vote_count == 2);
    }
    reset(); fake.present = 0; c = (struct smb_charger){ .real_charger_type = POWER_SUPPLY_TYPE_USB_FLOAT };
    v.intval = 100000; CHECK(!smblib_set_prop_sdp_current_max(&c, &v) && !fake.vote_count && c.real_charger_type == POWER_SUPPLY_TYPE_USB_FLOAT);
    reset(); fake.read_error = -EIO; CHECK(smblib_set_prop_sdp_current_max(&c, &v) == -EIO && !fake.vote_count);
    reset(); c.pd_active = true; CHECK(!smblib_set_prop_sdp_current_max(&c, &v) && !fake.vote_count && c.real_charger_type == POWER_SUPPLY_TYPE_USB_FLOAT);
    reset(); c.system_suspend_supported = true; v.intval = 2000;
    CHECK(!smblib_set_prop_sdp_current_max(&c, &v) && fake.voter == PD_SUSPEND_SUPPORTED_VOTER && fake.enabled);
    reset(); c = (struct smb_charger){ .real_charger_type = POWER_SUPPLY_TYPE_USB_FLOAT, .connector_type = POWER_SUPPLY_CONNECTOR_TYPEC };
    v.intval = -ETIMEDOUT; CHECK(!smblib_set_prop_sdp_current_max(&c, &v) && fake.requested == 1500000 && c.real_charger_type == POWER_SUPPLY_TYPE_USB_FLOAT);
    reset(); c.float_cfg = FORCE_FLOAT_SDP_CFG_BIT;
    CHECK(!smblib_set_prop_sdp_current_max(&c, &v) && fake.set_sdp == 500000 && !fake.vote_count);
    printf("{\"actual_oem_function_assertions\":%d,\"hardware_accessed\":false,\"oem_timeout_escalation_not_copied\":true}\n", checks);
    return 0;
}
