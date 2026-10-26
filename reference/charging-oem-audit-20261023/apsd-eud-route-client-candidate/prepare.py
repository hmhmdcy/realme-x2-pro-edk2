"""Replace the legacy COM quiet window with a real EUD-off route capability."""
from pathlib import Path
import difflib,hashlib,json
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'apsd-final-transfer-candidate'
source=(OLD/'samurai-apsd-owner.c').read_text();original=source
def replace(before,after):
 global source
 assert source.count(before)==1,(before[:100],source.count(before));source=source.replace(before,after)
replace(' * after physical off. PHY withdrawal is connected; route/final-transfer coverage is absent:\n * every APSD window/1341 attempt is still refused, not every PD control I/O.',
 ' * after physical off. The explicit EUD-off route profile joins real supplier\n * revocation and validates its original lease again at the final transfer.')
replace('#include "eud-com-window.h"','#include <linux/usb/samurai-eud-route.h>')
replace('\tstruct eud_com_window_result eud;','\tstruct device *route_device;\n\tstruct samurai_eud_route_client *route_client;\n\tstruct samurai_eud_route_lease route_lease;')
source=source.replace('eud_error','route_error').replace('o->eud.cookie','o->route_lease.client')
replace(' if (o->typec)\n  put_device(o->typec);',' if (o->typec)\n  put_device(o->typec);\n if (o->route_device)\n  put_device(o->route_device);')
mark='/* PHY withdrawal publishes its permanent fence'
replace(mark,(HERE/'route-client-functions.inc').read_text()+'\n'+mark)
start=source.index('/* A real PD5V lease and bound PHY client');end=source.index('/* Only this worker or its joined lifecycle',start)
source=source[:start]+'''/* The explicit profile needs all actual providers, never a caller Boolean. */
static int owner_entry_gate(struct samurai_apsd_owner *o)
{
	struct samurai_eud_route_status state;
	int ret;

	if (!o->bus || !o->bus->read_sample || !o->bus->rerun_once)
		return -ENODEV;
	if (!IS_ENABLED(CONFIG_USB_DWC3_SAMURAI_APSD_EUD_OFF_CLIENT) ||
	    !o->route_client || !o->pd_bridge || !o->pd_prepared ||
	    o->pd_phase != OWNER_PD_SINK_EPOCH || !o->pd_lease.owner)
		return -EOPNOTSUPP;
	if (owner_aborted(o))
		return -ECANCELED;
	ret = samurai_pd5v_validate(&o->pd_lease);
	if (ret)
		return ret;
	ret = samurai_eud_route_status(o->route_client, &state);
	if (ret)
		return ret;
	if (state.revoked || !state.exclusive)
		return -ESHUTDOWN;
	return o->route_lease.client ? samurai_eud_route_validate(&o->route_lease) : 0;
}

'''+source[end:]
replace('ret = eud_com_quiet_end(o->route_lease.client, &o->eud);','ret = samurai_eud_route_end(&o->route_lease);')
replace('\tif (o->phy.cookie) {\n\t\tret = qcom_snps_hsphy_window_end',
 '\tif (o->phy.cookie) {\n\t\t/* Independent supplier/UDC joins must not retry an already failed\n\t\t * restore or replace its original hardware error. */\n\t\tif (o->phy_error)\n\t\t\treturn o->phy_error;\n\t\tret = qcom_snps_hsphy_window_end')
replace('\t\to->route_lease.client = 0;\n','')
replace('if (!o->phy_client)\n\t\treturn -ENODEV;','if (!o->phy_client || !o->route_client)\n\t\treturn -ENODEV;')
replace('/* stays through EUD restore, beyond DWC end\'s put */','/* stays through route release, beyond DWC end\'s put */')
replace('ret = eud_com_quiet_begin(&o->eud);','ret = samurai_eud_route_begin(o->route_client, &o->route_lease);')
replace('if (!o->phy_client || !o->phy.cookie || !o->phy.high_z ||','if (!o->route_lease.client || !o->phy_client || !o->phy.cookie || !o->phy.high_z ||')
replace('/* Route capability is still absent. The actual entry gate continues to\n\t * refuse every production attempt, including this last boundary.\n\t */','/* Revalidate the exact live route lease after PD/PHY and fresh wire checks. */')
replace('\tret = owner_phy_resolve(o);','\tret = owner_route_resolve(o);\n\tif (!ret)\n\t\tret = owner_phy_resolve(o);')
replace('phy=%d dwc=%d eud=%d','phy=%d dwc=%d route=%d')
replace('\tif (owner_phy_release(o))\n\t\towner_quarantine(o);','\tif (owner_phy_release(o))\n\t\towner_quarantine(o);\n\tif (owner_route_release(o))\n\t\towner_quarantine(o);')
source=source.replace('failed PHY/EUD token','failed PHY/route token')
assert 'eud_com_' not in source and 'o->eud' not in source
header=(OLD/'samurai-apsd-owner.h').read_text().replace(' DWC3_APSD_PHY = 64,',' DWC3_APSD_PHY = 64,\n DWC3_APSD_ROUTE = 128,')
for name,raw in [('samurai-apsd-owner.c',source),('samurai-apsd-owner.h',header)]:
 path=HERE/name
 if path.exists() and path.read_text()!=raw:
  assert name=='samurai-apsd-owner.c' and path.read_bytes()==(HERE/'history/samurai-apsd-owner-before-restore-fence.c.inc').read_bytes(),name
  path.write_text(raw)
 elif path.exists():assert path.read_text()==raw,name
 else:path.write_text(raw)
patch=''.join(difflib.unified_diff(original.splitlines(True),source.splitlines(True),fromfile='a/drivers/usb/dwc3/samurai-apsd-owner.c',tofile='b/drivers/usb/dwc3/samurai-apsd-owner.c'))
patch+=''.join(difflib.unified_diff((OLD/'samurai-apsd-owner.h').read_text().splitlines(True),header.splitlines(True),fromfile='a/drivers/usb/dwc3/samurai-apsd-owner.h',tofile='b/drivers/usb/dwc3/samurai-apsd-owner.h'))
(HERE/'route-client.patch').write_text(patch)
(HERE/'source-result.json').write_text(json.dumps(dict(prepared=True,original_sha256=hashlib.sha256(original.encode()).hexdigest(),files={name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in ['samurai-apsd-owner.c','samurai-apsd-owner.h','route-client-functions.inc']},phone_accessed=False,installed=False),indent=2)+'\n')
print(json.dumps(dict(prepared=True,legacy_COM_window_calls=0)))
