"""Actual audit predicate against stale/zero/contract-mismatched readings; no device access."""
from pathlib import Path
import copy,hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('readonly_budget_audit',HERE/'audit-phone.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
roles={'power_operation_mode':'default'}
psy={'online':'1','voltage_now':'5000000','usb_type':'[C] PD PD_PPS',
     'current_max':'500000','current_now':'500000'}
cases={'correct':{},'zero_max':{'current_max':'0'},'stale100_max':{'current_max':'100000'},
 'zero_operating':{'current_now':'0'},'stale100_operating':{'current_now':'100000'},
 'above_native':{'current_max':'1500000'},'negative':{'current_max':'-500000'},
 'offline':{'online':'0'},'wrong_voltage':{'voltage_now':'9000000'},
 'PD_type':{'usb_type':'C [PD] PD_PPS'},'PD_mode':{},'Rp1p5':{},'native100':{}}
for name,changes in cases.items():
    p=copy.deepcopy(psy);p.update(changes);r=dict(roles)
    if name=='PD_mode':r['power_operation_mode']='usb_power_delivery'
    if name=='Rp1p5':r['power_operation_mode']='1.5A'
    try:result=m.check_default_usb_budget(r,p,100000 if name=='native100' else 500000)
    except AssertionError:
        assert name!='correct',name
    else:
        assert name=='correct' and result['native_allowance_ua']==500000,name
result={'passed':True,'cases':len(cases),'actual_predicate':'check_default_usb_budget',
 'audit_sha256':hashlib.sha256((HERE/'audit-phone.py').read_bytes()).hexdigest(),
 'phone_accessed':False,'positive_actual508_budget_verified':False}
(HERE/'audit-budget-test-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
