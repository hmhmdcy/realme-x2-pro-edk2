"""Extract exact current functions for boundary tests; no driver candidate."""
from pathlib import Path
import hashlib
import json
import re

HERE=Path(__file__).resolve().parent
TARGETS={
 'snapshots/drivers--phy--qualcomm--phy-qcom-snps-femto-v2.c':['qcom_snps_hsphy_set_mode'],
 'snapshots/drivers--phy--phy-core.c':['phy_set_mode_ext'],
 'snapshots/drivers--usb--dwc3--core.c':['dwc3_set_mode'],
 'snapshots/drivers--usb--dwc3--drd.c':['dwc3_usb_role_switch_set'],
 'snapshots/drivers--usb--roles--class.c':['usb_role_switch_set_role'],
 'snapshots/drivers--usb--dwc3--gadget.c':['dwc3_gadget_pullup'],
 'extra-snapshots/drivers--usb--gadget--udc--core.c':['usb_gadget_connect_locked','usb_gadget_disconnect_locked',
     'usb_gadget_deactivate','usb_gadget_activate']}


def main():
 rows=[];bodies=[]
 for path,names in TARGETS.items():
  text=(HERE/path).read_text()
  for name in names:
   match=re.search(r'^(?:static\s+)?[\w\s*]+?\b'+name+r'\([^;]*?\)\n(?:\s+__must_hold[^\n]+\n)?\{',text,re.M)
   assert match,name
   a=match.start()
   while text[a]=='\n':a+=1
   b=text.index('\n}',match.end())+2;body=text[a:b]
   rows.append(dict(function=name,snapshot=path,line=text.count('\n',0,a)+1,
                    sha256=hashlib.sha256(body.encode()).hexdigest()))
   bodies.append(body)
 (HERE/'actual-functions.inc').write_text('\n\n'.join(bodies)+'\n')
 (HERE/'function-manifest.json').write_text(json.dumps(rows,indent=2)+'\n')
 print(json.dumps({'exact_functions':len(rows),'driver_changes':False}))


if __name__=='__main__':main()
