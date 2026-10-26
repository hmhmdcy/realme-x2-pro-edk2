"""Add the actual USB supply to default-Rp TCPM; no hardware access."""
from pathlib import Path
import difflib,hashlib,json
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'tcpm-sink-shutdown-candidate'
CORE=HERE.parent/'apsd-tcpm-owner-candidate/sources/drivers--usb--typec--tcpm--tcpm.c'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def replace(text,old,new):
    assert text.count(old)==1,old
    return text.replace(old,new)
assert not (HERE/'source.json').exists()
port=(OLD/'qcom_pmic_typec_port.c').read_text()
port=replace(port,'#include <linux/platform_device.h>\n',
             '#include <linux/platform_device.h>\n#include <linux/power_supply.h>\n#include <linux/property.h>\n')
port=replace(port,'\tstruct regulator\t\t*vdd_vbus;\n',
             '\tstruct power_supply\t\t*usb_psy;\n\tstruct regulator\t\t*vdd_vbus;\n')
extra='''/* Default Rp carries no BC1.2/USB enumeration allowance. Read the real
 * supplier; an unavailable, offline or invalid budget grants no current.
 * The fixed-5V trial ceiling is a cap, never a substitute for permission.
 */
static int qcom_pmic_typec_port_get_current_limit(struct tcpc_dev *tcpc)
{
\tstruct pmic_typec *tcpm = tcpc_to_tcpm(tcpc);
\tstruct power_supply *psy = tcpm->pmic_typec_port->usb_psy;
\tunion power_supply_propval value;
\tint ret, limit;

\tret = power_supply_get_property(psy, POWER_SUPPLY_PROP_ONLINE, &value);
\tif (ret || value.intval != 1)
\t\treturn 0;
\tret = power_supply_get_property(psy, POWER_SUPPLY_PROP_CURRENT_MAX, &value);
\tif (ret || value.intval <= 0)
\t\treturn 0;
\tlimit = value.intval / 1000;
\tif (tcpm->samurai_fixed_5v)
\t\tlimit = min(limit, 500);
\treturn limit;
}

static int qcom_pmic_typec_port_get_usb_supply(struct device *dev,
\t\t\t\t\t    struct pmic_typec *tcpm)
{
\tstruct power_supply *psy;

\tif (!device_property_present(dev, "power-supplies"))
\t\treturn 0;
\tpsy = devm_power_supply_get_by_reference(dev, "power-supplies");
\tif (IS_ERR(psy))
\t\treturn PTR_ERR(psy);
\tif (!psy)
\t\treturn -EPROBE_DEFER;
\ttcpm->pmic_typec_port->usb_psy = psy;
\ttcpm->tcpc.get_current_limit = qcom_pmic_typec_port_get_current_limit;
\treturn 0;
}

'''
port=replace(port,'int qcom_pmic_typec_port_probe(struct platform_device *pdev,\n',
             extra+'int qcom_pmic_typec_port_probe(struct platform_device *pdev,\n')
port=replace(port,'\ttcpm->pmic_typec_port = pmic_typec_port;\n',
             '\ttcpm->pmic_typec_port = pmic_typec_port;\n\tret = qcom_pmic_typec_port_get_usb_supply(dev, tcpm);\n\tif (ret)\n\t\treturn ret;\n')
core=CORE.read_text()
assert sha(CORE.read_bytes())=='e7e8b9c692e64782e3422ba8e1f79b21072ed89e1dce8751d53f4b197762c0ab'
notify='''/* The supplier can change its USB allowance without a CC transition
 * (enumeration, suspend or resume). Only refresh default-Rp, non-PD ready
 * sinks. Contract negotiation and other states retain TCPM's own limits.
 */
static void tcpm_psy_external_power_changed(struct power_supply *psy)
{
\tstruct tcpm_port *port = power_supply_get_drvdata(psy);
\tenum typec_cc_status cc;
\tu32 limit;

\tmutex_lock(&port->lock);
\tcc = port->polarity ? port->cc2 : port->cc1;
\tif (port->registered && port->tcpc->get_current_limit &&
\t    port->state == SNK_READY && port->pwr_role == TYPEC_SINK &&
\t    port->attached && port->vbus_present &&
\t    !port->pd_capable && !port->explicit_contract &&
\t    cc == TYPEC_CC_RP_DEF) {
\t\tlimit = tcpm_get_current_limit(port);
\t\tif (limit != port->current_limit)
\t\t\ttcpm_set_current_limit(port, limit, 5000);
\t}
\tmutex_unlock(&port->lock);
}

'''
core=replace(core,'static const char *tcpm_psy_name_prefix = "tcpm-source-psy-";\n',
             notify+'static const char *tcpm_psy_name_prefix = "tcpm-source-psy-";\n')
core=replace(core,'\tport->psy_desc.get_property = tcpm_psy_get_prop;\n',
             '\tport->psy_desc.get_property = tcpm_psy_get_prop;\n\tport->psy_desc.external_power_changed = tcpm_psy_external_power_changed;\n')
core=replace(core,'\tport->registered = false;\n\tkthread_destroy_worker(port->wq);\n',
             '\t/* Join any supplier callback before destroying the TCPM worker. */\n\tmutex_lock(&port->lock);\n\tport->registered = false;\n\tmutex_unlock(&port->lock);\n\tkthread_destroy_worker(port->wq);\n')
sources={}
patch=[]
for name,before,after,path in [
 ('qcom_pmic_typec_port.c',(OLD/'qcom_pmic_typec_port.c').read_text(),port,'drivers/usb/typec/tcpm/qcom/qcom_pmic_typec_port.c'),
 ('tcpm.c',CORE.read_text(),core,'drivers/usb/typec/tcpm/tcpm.c')]:
    (HERE/name).write_text(after)
    sources[path]={'file':name,'baseline_sha256':sha(before.encode()),'candidate_sha256':sha(after.encode())}
    patch.extend(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+path,tofile='b/'+path))
(HERE/'usb-budget.patch').write_text(''.join(patch))
(HERE/'source.json').write_text(json.dumps({'prepared':True,'installed':False,'sources':sources},indent=2)+'\n')
print(json.dumps({'prepared':True,'sources':sources}))
