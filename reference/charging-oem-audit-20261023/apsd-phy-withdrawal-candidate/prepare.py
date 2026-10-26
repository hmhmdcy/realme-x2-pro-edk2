"""Derive the provider lifetime implementation from the pinned PHY window."""
from pathlib import Path
import difflib,hashlib,json,re
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'apsd-phy-window-candidate'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
source=(OLD/'phy-qcom-snps-femto-v2.c').read_text();header=(OLD/'phy-qcom-snps-femto-v2-window.h').read_text()
assert sha(source.encode())=='cc8e7f3292792f1f921db090384202fcf8ebb426f5a782f976b5f4614ba6b6dc'
def replace(text,a,b):
    assert text.count(a)==1,a;return text.replace(a,b)
source=replace(source,'#include <linux/clk.h>','#include <linux/clk.h>\n#include <linux/completion.h>\n#include <linux/kref.h>\n#include <linux/list.h>')
source=replace(source,'/**\n * struct qcom_snps_hsphy','struct qcom_hsphy_window_provider;\n\n/**\n * struct qcom_snps_hsphy')
source=replace(source,' * @mode: contains',' * @window_withdrawing: provider removal/shutdown has revoked new operations\n * @window_provider: separately referenced publication and withdrawal state\n * @mode: contains')
source=replace(source,'\tbool window_pm_ref;','\tbool window_pm_ref;\n\tbool window_withdrawing;\n\tstruct qcom_hsphy_window_provider *window_provider;')
for name in ['begin','end']:
    source=replace(source,'int qcom_snps_hsphy_window_'+name+'(struct phy *phy,','static int qcom_snps_hsphy_window_bound_'+name+'(struct phy *phy,')
    source=replace(source,' * qcom_snps_hsphy_window_'+name+' -',' * qcom_snps_hsphy_window_bound_'+name+' -')
for name in ['qcom_snps_hsphy_init','qcom_snps_hsphy_exit','qcom_snps_hsphy_set_mode']:
    start=source.index('static int '+name+'(');pos=source.index('\n\tif (qcom_snps_hsphy_window_busy(hsphy))',start)
    source=source[:pos]+'\n\tif (hsphy->window_withdrawing)\n\t\treturn -ESHUTDOWN;\n'+source[pos:]
for name in ['qcom_snps_hsphy_runtime_suspend','qcom_snps_hsphy_runtime_resume']:
    start=source.index('qcom_snps_hsphy_'+name.split('qcom_snps_hsphy_')[1]+'(')
    pos=source.index('\n\tif (qcom_snps_hsphy_window_busy(hsphy))',start)
    source=source[:pos]+'\n\tif (hsphy->window_withdrawing)\n\t\tret = -ESHUTDOWN;\n\telse'+source[pos:]
source=replace(source,'static int qcom_snps_hsphy_suspend(struct qcom_snps_hsphy *hsphy)',(HERE/'provider-lifetime.inc').read_text()+'\n\nstatic int qcom_snps_hsphy_suspend(struct qcom_snps_hsphy *hsphy)')
source=replace(source,'\tdev_dbg(dev, "Registered Qcom-SNPS HS phy\\n");','\tret = qcom_hsphy_window_publish(hsphy);\n\tif (ret) {\n\t\tpm_runtime_put_noidle(dev);\n\t\treturn ret;\n\t}\n\n\tdev_dbg(dev, "Registered Qcom-SNPS HS phy\\n");')
source=replace(source,'\t.probe\t\t= qcom_snps_hsphy_probe,','\t.probe\t\t= qcom_snps_hsphy_probe,\n\t.remove\t\t= qcom_snps_hsphy_remove,\n\t.shutdown\t= qcom_snps_hsphy_shutdown,')
header=header[:header.index('/* Internal same-Image')]+'''/* Internal same-Image interface. Registration pins the real owner context.
 * The caller joins all of its API users before unregister. EBUSY retains the
 * handle/context until exact restoration or completed provider revocation.
 * Withdrawal calls cancel_join without component locks; the callback must
 * stop/join detection and may call end/unregister. A failed end must never
 * reconnect DWC/EUD. status remains readable after provider devres is gone.
 * No handle authorizes route, PD, DWC HALT or a PMIC detection transfer. */
'''+header[header.index('enum qcom_snps_hsphy_window_state'):]
header=replace(header,'\tbool high_z, restored;','\tbool high_z, restored, revoked;')
header=replace(header,'\tint enter_error, restore_error;','\tint enter_error, restore_error, withdraw_error;')
header=header[:header.index('int qcom_snps_hsphy_window_begin')]+'''struct qcom_snps_hsphy_window_client;
struct qcom_snps_hsphy_window_client_ops {
 bool (*get_unless_zero)(void *context);
 void (*put)(void *context);
 int (*cancel_join)(void *context);
};
int qcom_snps_hsphy_window_client_register(struct phy *phy,
 const struct qcom_snps_hsphy_window_client_ops *ops, void *context,
 struct qcom_snps_hsphy_window_client **client);
int qcom_snps_hsphy_window_client_unregister(struct qcom_snps_hsphy_window_client *client);
int qcom_snps_hsphy_window_begin(struct qcom_snps_hsphy_window_client *client,
 struct qcom_snps_hsphy_window_result *result);
int qcom_snps_hsphy_window_end(struct qcom_snps_hsphy_window_client *client, u64 cookie,
 struct qcom_snps_hsphy_window_result *result);
int qcom_snps_hsphy_window_status(struct qcom_snps_hsphy_window_client *client,
 struct qcom_snps_hsphy_window_result *result);
#endif
'''
files={'phy-qcom-snps-femto-v2.c':source,'phy-qcom-snps-femto-v2-window.h':header}
patch=''
for name,text in files.items():
    (HERE/name).write_text(text)
    patch+=''.join(difflib.unified_diff((OLD/name).read_text().splitlines(True),text.splitlines(True),fromfile='a/drivers/phy/qualcomm/'+name,tofile='b/drivers/phy/qualcomm/'+name))
(HERE/'withdrawal.patch').write_text(patch)
result=dict(prepared=True,source_sha256=sha((OLD/'phy-qcom-snps-femto-v2.c').read_bytes()),
    files={name:sha(text.encode()) for name,text in files.items()},phone_accessed=False,consumer_connected=False)
(HERE/'source-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
