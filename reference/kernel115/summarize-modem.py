from pathlib import Path
import json
out=Path('/mnt/e/edk2-samurai-out/kernel115')
data=json.loads((out/'modem-current-private.json').read_text())['modem']
safe={}
for section in ['generic','status','3gpp']:
    if section in data:
        for key,value in data[section].items():
            if key in ['state','state-failed-reason','power-state','plugin','primary-port','ports','supported-capabilities','current-capabilities','access-technologies','registration-state']:
                safe[f'{section}.{key}']=value
report=dict(modemmanager_detected=True,readonly_snapshot=safe,outbound_calls_sms_data_not_tested=True,goal_complete=False)
for dest in [out,Path('/mnt/e/RealmeX2Pro edk2/reference/kernel115')]: (dest/'modemmanager-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
