from pathlib import Path
from hashlib import sha256
import json

root=Path(__file__).resolve().parent
def replace_once(text, old, new):
    assert text.count(old)==1, old
    return text.replace(old,new)
original=json.loads((root/'prepared-hashes.json').read_text())
for name,expected in original.items():
    assert sha256((root/name).read_bytes()).hexdigest()==expected,name
text=(root/'driver-log-admin.ps1').read_text()
text=replace_once(text,"'control-01'","'control-02'")
text=replace_once(text,"'driver-logs-01'","'driver-logs-02'")
text=replace_once(text,"'logging-plan.json'","'logging-plan-02.json'")
text=replace_once(text,r"rx57[\\/]capture-windows\.ps1",r"rx57[\\/]capture-windows(?:-02)?\.ps1")
text=replace_once(text,"        $rxCode=Disable-PnpDevice -InstanceId $rxInstance -Confirm:$false -PassThru -ErrorAction Stop\n        if($rxCode -ne 0){throw \"Disable-PnpDevice returned $rxCode\"}","        Disable-PnpDevice -InstanceId $rxInstance -Confirm:$false -ErrorAction Stop | Out-Null\n        $rxDisabledWait=[Diagnostics.Stopwatch]::StartNew()\n        while($true){\n            $rxDisabledNode=Get-PnpDevice -InstanceId $rxInstance -ErrorAction Stop\n            if([int]$rxDisabledNode.ConfigManagerErrorCode -eq 22){break}\n            if($rxDisabledWait.ElapsedMilliseconds -ge 5000){throw 'Exact COM14 instance did not become disabled (CM_PROB_DISABLED=22).'}\n            Start-Sleep -Milliseconds 250\n        }")
text=replace_once(text,"        $rxCode=Enable-PnpDevice -InstanceId $rxInstance -Confirm:$false -PassThru -ErrorAction Stop\n        if($rxCode -ne 0){throw \"Enable-PnpDevice returned $rxCode\"}","        Enable-PnpDevice -InstanceId $rxInstance -Confirm:$false -ErrorAction Stop | Out-Null")
(root/'driver-log-admin-02.ps1').write_text(text,newline='\n')
text=(root/'capture-windows.ps1').read_text().replace("'control-01'","'control-02'").replace('windows-log-01','windows-log-02')
(root/'capture-windows-02.ps1').write_text(text,newline='\n')
text=(root/'launch-approved-logger.ps1').read_text().replace('driver-log-admin.ps1','driver-log-admin-02.ps1').replace('capture-windows.ps1','capture-windows-02.ps1').replace('prepared-hashes.json','prepared-hashes-02.json').replace('control-01','control-02').replace('admin-launch.json','admin-launch-02.json')
(root/'launch-approved-logger-02.ps1').write_text(text,newline='\n')
text=(root/'test-prepared.ps1').read_text().replace('driver-log-admin.ps1','driver-log-admin-02.ps1').replace('capture-windows.ps1','capture-windows-02.ps1').replace('launch-approved-logger.ps1','launch-approved-logger-02.ps1').replace('control-01','control-02').replace('prepared-tests.json','prepared-tests-02.json').replace("('mock-'+","('mock02-'+")
text=replace_once(text,"    $rxReloadSim=@'","    $rxReloadSim=@'\nfunction Get-PnpDevice { param($InstanceId,$ErrorAction)\n return [pscustomobject]@{InstanceId=$rxInstance;ConfigManagerErrorCode=22}\n}")
text=replace_once(text," if($rxReloadCase -eq 'enable-error'){return 5}"," if($rxReloadCase -eq 'enable-error'){throw 'simulated enable error'}")
text=text.replace(' return 0'," return [pscustomobject]@{DeviceID=$rxInstance;Status='OK';ConfigManagerErrorCode=0}")
(root/'test-prepared-02.ps1').write_text(text,newline='\n')
print('Prepared retry helpers; originals unchanged; no native actions run.')
