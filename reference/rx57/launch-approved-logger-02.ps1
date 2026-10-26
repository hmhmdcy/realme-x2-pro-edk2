$ErrorActionPreference='Stop'
$rxRoot='E:\edk2-samurai-out\rx57'
$rxHelper=Join-Path $rxRoot 'driver-log-admin-02.ps1'
$rxManifest=Get-Content -Raw -LiteralPath (Join-Path $rxRoot 'prepared-hashes-02.json') | ConvertFrom-Json
foreach($rxName in @('driver-log-admin-02.ps1','capture-windows-02.ps1','EudRxAudit.cs','EudSerialPerf.cs','eud-terminal-rx-perf.ps1')){
    $rxExpected=$rxManifest.$rxName
    if(!$rxExpected -or (Get-FileHash -LiteralPath (Join-Path $rxRoot $rxName)).Hash.ToLower() -ne $rxExpected){throw "Reviewed bundle differs: $rxName"}
}
if(Test-Path -LiteralPath (Join-Path $rxRoot 'control-02')){throw 'This prepared administrator attempt has already been used.'}
$rxExe='C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
$rxArgs='-NoProfile -ExecutionPolicy Bypass -File "'+$rxHelper+'" -Mode Arm'
$rxAdminProcess=Start-Process -FilePath $rxExe -ArgumentList $rxArgs -Verb RunAs -WindowStyle Hidden -PassThru
try {
    $rxLaunch=[ordered]@{utc=(Get-Date).ToUniversalTime().ToString('o');admin_pid=$rxAdminProcess.Id;helper_sha256=$rxManifest.'driver-log-admin-02.ps1';new_authorization_required=$true;expected_scope='temporary two COM14 driver logging values, one reload to enable, one reload to restore, bounded diagnostic; no flash/phone reboot/driver install/ETW'}
    [IO.File]::WriteAllText((Join-Path $rxRoot 'admin-launch-02.json'),($rxLaunch | ConvertTo-Json -Depth 4).Replace("`r`n","`n")+"`n",[Text.UTF8Encoding]::new($false))
    $rxLaunch | ConvertTo-Json -Depth 4
} finally {$rxAdminProcess.Dispose()}
