"""Private candidate only; normal qcom probe remainder is byte-preserved."""
from pathlib import Path
import difflib,hashlib,json
HERE=Path(__file__).resolve().parent
SRC=HERE.parent/'apsd-tcpm-owner-candidate/sources'
sha=lambda b:hashlib.sha256(b).hexdigest()
names=['qcom_pmic_typec.c','qcom_pmic_typec.h','Makefile']
raw={n:(SRC/('drivers--usb--typec--tcpm--qcom--'+n)).read_bytes() for n in names}
text={n:v.decode().replace('\r\n','\n') for n,v in raw.items()}
s=text['qcom_pmic_typec.c']
s=s.replace('#include "qcom_pmic_typec_port.h"','#include "qcom_pmic_typec_port.h"\n#include "qcom_pmic_typec_5v.h"\n\nstatic bool samurai_5v_only;\nmodule_param(samurai_5v_only, bool, 0400);\nMODULE_PARM_DESC(samurai_5v_only, "Opt in to the explicitly marked Samurai PD-disabled owner");\nstatic struct platform_driver qcom_pmic_typec_driver;')
at='\tret = of_property_read_u32_index(np, "reg", 0, &base);'
branch='''\t/* Both explicit opt-ins are required. Never fall through into TCPM
\t * when the special mode is requested but its binding is incomplete. */
\tif (samurai_5v_only || of_property_read_bool(np, "realme,pd5v-only")) {
\t\tu32 pd_base;
\t\tif (!samurai_5v_only || !of_property_read_bool(np, "realme,pd5v-only") ||
\t\t    !of_machine_is_compatible("realme,samurai") ||
\t\t    !of_device_is_compatible(np, "qcom,pm8150b-typec"))
\t\t\treturn -EOPNOTSUPP;
\t\tif (of_get_child_count(np))
\t\t\treturn -EBUSY;
\t\tret = of_property_read_u32_index(np, "reg", 0, &base);
\t\tif (ret)
\t\t\treturn ret;
\t\tret = of_property_read_u32_index(np, "reg", 1, &pd_base);
\t\tif (ret)
\t\t\treturn ret;
\t\tif (base != 0x1500 || pd_base != 0x1700)
\t\t\treturn -EXDEV;
\t\ttcpm->pd5v = samurai_pd5v_create(dev, regmap);
\t\tif (IS_ERR(tcpm->pd5v))
\t\t\treturn PTR_ERR(tcpm->pd5v);
\t\tplatform_set_drvdata(pdev, tcpm);
\t\treturn 0;
\t}

'''
assert s.count(at)==1;s=s.replace(at,branch+at)
at='\ttcpm->pdphy_stop(tcpm);\n\ttcpm->port_stop(tcpm);'
replacement='''\tif (tcpm->pd5v) {
\t\tsamurai_pd5v_destroy(tcpm->pd5v);
\t\treturn;
\t}

'''+at
assert s.count(at)==1;s=s.replace(at,replacement)
at='static const struct pmic_typec_resources pm8150b_typec_res = {'
extra='''static int qcom_pmic_typec_prepare(struct device *dev)
{
\tstruct pmic_typec *tcpm = dev_get_drvdata(dev);
\treturn tcpm->pd5v ? samurai_pd5v_quiesce(tcpm->pd5v) : 0;
}

static void qcom_pmic_typec_complete(struct device *dev)
{
\tstruct pmic_typec *tcpm = dev_get_drvdata(dev);
\tif (tcpm->pd5v)
\t\tsamurai_pd5v_complete(tcpm->pd5v);
}

static void qcom_pmic_typec_shutdown(struct platform_device *pdev)
{
\tstruct pmic_typec *tcpm = platform_get_drvdata(pdev);
\tif (tcpm->pd5v)
\t\tsamurai_pd5v_quiesce(tcpm->pd5v);
}

static const struct dev_pm_ops qcom_pmic_typec_pm_ops = {
\t.prepare = qcom_pmic_typec_prepare,
\t.complete = qcom_pmic_typec_complete,
};

'''
assert at in s;s=s.replace(at,extra+at)
s=s.replace('\t\t.of_match_table = qcom_pmic_typec_table,','\t\t.of_match_table = qcom_pmic_typec_table,\n\t\t.pm = &qcom_pmic_typec_pm_ops,')
s=s.replace('\t.remove = qcom_pmic_typec_remove,','\t.remove = qcom_pmic_typec_remove,\n\t.shutdown = qcom_pmic_typec_shutdown,')
out={'qcom_pmic_typec.c':s,'qcom_pmic_typec.h':text['qcom_pmic_typec.h'].replace('\tstruct device\t\t*dev;','\tstruct device\t\t*dev;\n\tstruct samurai_pd5v\t*pd5v;')}
out['Makefile']=text['Makefile'].replace('qcom_pmic_typec.o \\', 'qcom_pmic_typec.o \\\n\t\t\t\t\t   qcom_pmic_typec_5v.o \\')
for n,value in out.items():
 (HERE/n).write_bytes(value.encode())
patch=[]
for n,value in out.items():
 patch.extend(difflib.unified_diff(text[n].splitlines(True),value.splitlines(True),fromfile='a/drivers/usb/typec/tcpm/qcom/'+n,tofile='b/drivers/usb/typec/tcpm/qcom/'+n))
for n in ['qcom_pmic_typec_5v.c','qcom_pmic_typec_5v.h']:
 patch.extend(difflib.unified_diff([], (HERE/n).read_text().splitlines(True),fromfile='/dev/null',tofile='b/drivers/usb/typec/tcpm/qcom/'+n))
(HERE/'pd5v-owner.patch').write_bytes(''.join(patch).encode())
# Exact normal branch tails survive the insertion; no normal operation body changed.
base=text['qcom_pmic_typec.c']
start=base.index(at) if False else base.index('\tret = of_property_read_u32_index(np, "reg", 0, &base);')
tail=base[start:base.index('\nstatic void qcom_pmic_typec_remove')]
assert tail in s
(HERE/'integration-result.json').write_text(json.dumps(dict(original={n:sha(b) for n,b in raw.items()},candidate={n:sha(v.encode()) for n,v in out.items()},normal_probe_original_tail_unchanged=True,parameter_default=False,TCPM_started_in_special_branch=False,source_shared_modified=False),indent=2)+'\n')
print(json.dumps(dict(prepared=True,files=list(out))))
