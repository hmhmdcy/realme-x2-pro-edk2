"""Offline source-only handoff assembly. Writes only this candidate directory."""
from pathlib import Path
import difflib, hashlib, json
HERE = Path(__file__).resolve().parent
REF = HERE.parent
sha = lambda b: hashlib.sha256(b).hexdigest()

def replace(text, before, after):
    assert text.count(before) == 1, before
    return text.replace(before, after)

inputs = {
    'samurai-apsd-owner.c': REF/'eud-route-pm-candidate/samurai-apsd-owner.c',
    'qcom_pmic_typec.c': REF/'tcpm-sink-shutdown-candidate/qcom_pmic_typec.c',
    'qcom_pmic_typec.h': REF/'tcpm-sink-shutdown-candidate/qcom_pmic_typec.h',
    'qcom_pmic_typec_pdphy.c': REF/'tcpm-sink-shutdown-candidate/qcom_pmic_typec_pdphy.c',
    'Makefile': REF/'pd5v-owner-context-r2/Makefile',
}
texts = {name:path.read_text() for name,path in inputs.items()}
owner = texts['samurai-apsd-owner.c']
owner = replace(owner, '#include <linux/usb/samurai-pd5v.h>\n',
    '#include <linux/usb/samurai-pd5v.h>\n#include <linux/usb/samurai-tcpm-apsd.h>\n#include <linux/regmap.h>\n')
owner = replace(owner, 'static DEFINE_MUTEX(owner_registry);\n', '''static DEFINE_MUTEX(owner_registry);
/* Full TCPM publishes before joining the original worker. No provider or
 * native getter is called from this fence. Keep it across unbind/probe error:
 * there is no proved physical-detach rearm implementation in this candidate.
 */
static bool tcpm_fenced;
static struct device *tcpm_supplier;
''')
owner = replace(owner, 'aborted = o->abort || o->blocked || o->quarantined;',
    'aborted = o->abort || o->blocked || o->quarantined || READ_ONCE(tcpm_fenced);')
owner = replace(owner, 'if (o->registered && !o->blocked && !o->abort && !o->quarantined)\n',
    'if (o->registered && !o->blocked && !o->abort && !o->quarantined &&\n\t    !READ_ONCE(tcpm_fenced))\n')
extra = '''/* First full-PD takeover runs before tcpm_register_port(). The caller
 * holds no TCPM port, input, notifier, PHY or route lock. owner_registry only
 * serializes original lifecycle owners; the joined worker never takes it.
 * The real Type-C device is retained until its devres release action runs.
 */
int samurai_apsd_tcpm_quiesce(struct device *typec, struct regmap *map)
{
\tstruct device_node *node;
\tint ret = 0;

\tif (!typec || !typec->parent || !map ||
\t    !of_machine_is_compatible("realme,samurai") ||
\t    !of_device_is_compatible(typec->of_node, "qcom,pm8150b-typec") ||
\t    dev_get_regmap(typec->parent, NULL) != map)
\t\treturn -EXDEV;
\tmutex_lock(&owner_registry);
\tif (tcpm_supplier) {
\t\tret = -EBUSY;
\t\tgoto out;
\t}
\tif (bus_dev && (bus_dev->parent != typec->parent ||
\t\tdev_get_regmap(bus_dev->parent, NULL) != map)) {
\t\tret = -EXDEV;
\t\tgoto out;
\t}
\tif (bound_owner && bound_owner->dwc) {
\t\tnode = of_parse_phandle(bound_owner->dwc->dev->of_node,
\t\t\t\t"samurai,apsd-typec", 0);
\t\tif (node != typec->of_node)
\t\t\tret = -EXDEV;
\t\tof_node_put(node);
\t\tif (ret)
\t\t\tgoto out;
\t}
\ttcpm_supplier = get_device(typec);
\t/* Every acquisition/validation and later bind sees revocation first. */
\tWRITE_ONCE(tcpm_fenced, true);
\tif (bound_owner && bound_owner->dwc)
\t\tret = owner_join(bound_owner, DWC3_APSD_PD, false);
\tif (ret) {
\t\tput_device(tcpm_supplier);
\t\ttcpm_supplier = NULL;
\t}
out:
\tmutex_unlock(&owner_registry);
\treturn ret;
}
EXPORT_SYMBOL_GPL(samurai_apsd_tcpm_quiesce);

void samurai_apsd_tcpm_release(struct device *typec)
{
\tstruct device *supplier = NULL;

\tmutex_lock(&owner_registry);
\tif (tcpm_supplier == typec) {
\t\tsupplier = tcpm_supplier;
\t\ttcpm_supplier = NULL;
\t}
\t/* Never clear tcpm_fenced on remove, RX-off, PM, reset, or a software
\t * USB disconnect. Those do not prove physical detach/vSafe0V.
\t */
\tmutex_unlock(&owner_registry);
\tput_device(supplier);
}
EXPORT_SYMBOL_GPL(samurai_apsd_tcpm_release);

'''
owner = replace(owner, 'int samurai_apsd_bus_register(struct device *dev,\n',
    extra + 'int samurai_apsd_bus_register(struct device *dev,\n')
texts['samurai-apsd-owner.c'] = owner

driver = texts['qcom_pmic_typec.c']
driver = replace(driver, '#include "qcom_pmic_typec_5v.h"\n',
    '#include "qcom_pmic_typec_5v.h"\n#include "qcom_pmic_typec_apsd.h"\n')
driver = replace(driver,
    '\ttcpm->samurai_fixed_5v = qcom_pmic_typec_samurai_fixed_5v(tcpm);\n',
    '''\ttcpm->samurai_fixed_5v = qcom_pmic_typec_samurai_fixed_5v(tcpm);
\t/* Full Samurai TCPM cannot coexist with firmware APSD/QC or the forced
\t * borrower. This real, mandatory call precedes even tcpm_register_port:
\t * pdphy_start later enables frame filters before the first set_pd_rx.
\t * Fixed-5V and other boards retain their original lifecycles.
\t */
\tif (!tcpm->samurai_fixed_5v && of_machine_is_compatible("realme,samurai")) {
\t\ttcpm->apsd_handoff = qcom_pmic_typec_apsd_prepare(dev, regmap);
\t\tif (IS_ERR(tcpm->apsd_handoff)) {
\t\t\tret = PTR_ERR(tcpm->apsd_handoff);
\t\t\tdev_err(dev, "full-PD APSD/QC takeover refused: %d\\n", ret);
\t\t\tgoto fwnode_remove;
\t\t}
\t}
''')
texts['qcom_pmic_typec.c'] = driver
texts['qcom_pmic_typec.h'] = replace(texts['qcom_pmic_typec.h'],
    '\tstruct samurai_pd5v\t*pd5v;\n',
    '\tstruct samurai_pd5v\t*pd5v;\n\tstruct qcom_pmic_typec_apsd *apsd_handoff;\n')
phy = texts['qcom_pmic_typec_pdphy.c']
phy = replace(phy, '#include "qcom_pmic_typec_pdphy.h"\n',
    '#include "qcom_pmic_typec_pdphy.h"\n#include "qcom_pmic_typec_apsd.h"\n')
phy = replace(phy, '\tif (msg) {\n', '''\t/* Sleepable read-only isolation check, before taking the PHY spinlock.
\t * This path cannot join APSD or call a native/TCPM power_supply getter.
\t */
\tret = qcom_pmic_typec_apsd_verify(tcpm->apsd_handoff);
\tif (ret)
\t\treturn ret;
\tif (msg) {
''')
rx_before = '''\tspin_lock_irqsave(&pmic_typec_pdphy->lock, flags);

\tret = regmap_write(pmic_typec_pdphy->regmap,
\t\t\t   pmic_typec_pdphy->base + USB_PDPHY_RX_ACKNOWLEDGE_REG, !on);'''
phy = replace(phy, rx_before, '''\t/* RX-off (including hard reset) must not grant APSD/QC ownership. */
\tif (on) {
\t\tret = qcom_pmic_typec_apsd_verify(tcpm->apsd_handoff);
\t\tif (ret)
\t\t\treturn ret;
\t}
''' + rx_before)
phy = replace(phy, '\tret = regulator_enable(pmic_typec_pdphy->vdd_pdphy);\n',
    '''\tret = qcom_pmic_typec_apsd_verify(tcpm->apsd_handoff);
\tif (ret)
\t\treturn ret;
\tret = regulator_enable(pmic_typec_pdphy->vdd_pdphy);
''')
texts['qcom_pmic_typec_pdphy.c'] = phy
texts['Makefile'] = texts['Makefile'].rstrip().rstrip('\\').rstrip() + ' \\\n\t\t\t\t\t   qcom_pmic_typec_apsd.o\n'

paths = {name:'drivers/usb/typec/tcpm/qcom/'+name for name in texts}
paths['samurai-apsd-owner.c'] = 'drivers/usb/dwc3/samurai-apsd-owner.c'
patch, rows = [], {}
for name,text in texts.items():
    original = inputs[name].read_text()
    (HERE/name).write_text(text)
    rows[paths[name]] = {'file':name, 'baseline_file':str(inputs[name]),
        'baseline_sha256':sha(inputs[name].read_bytes()),
        'baseline_normalized_sha256':sha(original.encode()),
        'sha256':sha((HERE/name).read_bytes())}
    patch += difflib.unified_diff(original.splitlines(True), text.splitlines(True),
        fromfile='a/'+paths[name], tofile='b/'+paths[name])
for name,path in {
    'samurai-tcpm-apsd.h':'include/linux/usb/samurai-tcpm-apsd.h',
    'qcom_pmic_typec_apsd.h':'drivers/usb/typec/tcpm/qcom/qcom_pmic_typec_apsd.h',
    'qcom_pmic_typec_apsd.c':'drivers/usb/typec/tcpm/qcom/qcom_pmic_typec_apsd.c',
}.items():
    text = (HERE/name).read_text()
    rows[path] = {'file':name, 'baseline_sha256':None,'sha256':sha((HERE/name).read_bytes())}
    patch += difflib.unified_diff([],text.splitlines(True), fromfile='/dev/null',tofile='b/'+path)
(HERE/'handoff.patch').write_text(''.join(patch))
(HERE/'source.json').write_text(json.dumps({'offline':True,'installed':False,
    'complete_coexistence':False, 'sources':rows},indent=2)+'\n')
print(json.dumps({'prepared':True,'files':len(rows),'complete_coexistence':False}))
