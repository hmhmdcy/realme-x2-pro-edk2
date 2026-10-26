"""Reuse saved W1 kernel compiler commands; compile only the changed owner."""
from pathlib import Path
import ast,hashlib
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'apsd-pd5v-client-bridge-candidate'
original=(OLD/'build-private.py').read_text()
source=original
def replace(a,b):
    global source
    assert source.count(a)==1,a;source=source.replace(a,b)
replace("t['affected_groups']==14","t['group_count']==12")
replace("t['tested_files'].items()","t['files'].items()")
replace("apsd-pd5v-client-bridge-objects-04","apsd-phy-client-objects-02")
replace("headers={'linux/usb/samurai-apsd-backend.h':","headers={'core.h':OLD/'core.h','samurai-apsd-owner.h':HERE/'samurai-apsd-owner.h','linux/usb/samurai-apsd-backend.h':")
replace("HERE/'samurai-apsd-backend.h'","OLD/'samurai-apsd-backend.h'")
replace("'linux/usb/samurai-pd5v.h':HERE/'qcom_pmic_typec_5v.h'","'linux/usb/samurai-pd5v.h':OLD/'qcom_pmic_typec_5v.h'")
replace("REF/'charging-oem-audit-20261023/apsd-phy-window-candidate/phy-qcom-snps-femto-v2-window.h'","HERE/'phy-qcom-snps-femto-v2-window.h'")
replace("previous=json.loads((HERE/'history/build-before-abort-gates.json').read_bytes())","previous=json.loads((OLD/'history/build-before-abort-gates.json').read_bytes())")
replace("sha(HERE/'qcom_pmic_typec_5v.c')","sha(OLD/'qcom_pmic_typec_5v.c')")
replace("sha(HERE/'qcom_pmic_typec_5v.h')","sha(OLD/'qcom_pmic_typec_5v.h')")
replace("'-I'+str(include),'-I'+str(HERE),'-I'+str(SOURCE/rel)","'-I'+str(include),'-I'+str(HERE),'-I'+str(OLD),'-I'+str(SOURCE/rel)")
replace("['samurai-apsd-owner.c','samurai-apsd-owner.h','qcom_pmic_typec_5v.c','qcom_pmic_typec_5v.h','Kconfig.fragment']","['samurai-apsd-owner.c','samurai-apsd-owner.h','Kconfig.fragment']")
replace("receipt_sha256=sha(HERE/'history/build-before-abort-gates.json')","receipt_sha256=sha(OLD/'history/build-before-abort-gates.json')")
source=source.replace("r=dict(passed=False,","r=dict(original_builder_sha256='"+hashlib.sha256(original.encode()).hexdigest()+"',passed=False,",1)
ast.parse(source)
exec(compile(source,'<existing-saved-compiler-PHY-client>','exec'),dict(__file__=str(HERE/'build-private.py'),__name__='__main__',OLD=OLD))
