"""Extract actual existing functions to test current hook limits, not new policy."""
from pathlib import Path
import hashlib,json,re
HERE=Path(__file__).resolve().parent;SRC=HERE/'sources'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
selected={
 'drivers--usb--typec--tcpm--tcpm.c':['tcpm_pd_receive','tcpm_pd_hard_reset','tcpm_cc_change'],
 'drivers--usb--typec--tcpm--qcom--qcom_pmic_typec_pdphy.c':['qcom_pmic_typec_pdphy_sig_reset_work','qcom_pmic_typec_pdphy_isr','qcom_pmic_typec_pdphy_set_pd_rx','qcom_pmic_typec_pdphy_set_roles'],
 'drivers--usb--typec--tcpm--qcom--qcom_pmic_typec_port.c':['qcom_pmic_typec_port_vbus_detect','qcom_pmic_typec_port_get_vbus']}
parts=[];records=[]
for filename,names in selected.items():
 source=(SRC/filename).read_text()
 for name in names:
  m=re.search(r'(?m)^(?:static\s+)?(?:void|int|irqreturn_t)\s+'+re.escape(name)+r'\s*\(',source)
  assert m,name
  first=source.index('{',m.start());depth=1;end=first+1
  while depth:
   if source[end]=='{':depth+=1
   elif source[end]=='}':depth-=1
   end+=1
  text=source[m.start():end]
  parts.append(text+'\n\n');records.append(dict(name=name,source=filename,line=source[:m.start()].count('\n')+1,sha256=sha(text.encode())))
(HERE/'actual-functions.inc').write_text(''.join(parts))
(HERE/'function-manifest.json').write_text(json.dumps(dict(actual_functions=records),indent=2)+'\n')
print(json.dumps(dict(functions=len(records))))
