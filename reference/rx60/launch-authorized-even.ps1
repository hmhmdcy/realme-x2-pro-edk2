$ErrorActionPreference='Stop'
$rxRoot='E:\edk2-samurai-out\rx60'
$rxHelper=Join-Path $rxRoot 'driver-log-etw-admin.ps1'
$rxLaunch=Join-Path $rxRoot 'admin-even-launch.json'
if(Test-Path -LiteralPath $rxLaunch){throw 'This launch was already attempted; preserve its evidence.'}
if((Get-FileHash -LiteralPath $rxHelper).Hash.ToLower() -ne 'effe2bc4f5ae67bd6956a85da1677de09ee296ccddef2254a96b9deef14513d4'){throw 'Reviewed admin helper differs.'}
if(Test-Path -LiteralPath (Join-Path $rxRoot 'control-even-01')){throw 'Original control directory exists.'}
$rxRecord=[ordered]@{utc=[DateTime]::UtcNow.ToString('o');authorization='Human provided continuing authorization for the same scoped COM14 diagnostics; RX60 even-IN reversal protocol recorded before launch.';helper_sha256='effe2bc4f5ae67bd6956a85da1677de09ee296ccddef2254a96b9deef14513d4';pid=$null;launch_error=$null}
[IO.File]::WriteAllText($rxLaunch,($rxRecord | ConvertTo-Json)+"`n",[Text.UTF8Encoding]::new($false))
try {
    $rxProcess=Start-Process -FilePath 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',$rxHelper,'-Mode','Arm') -Verb RunAs -WindowStyle Hidden -PassThru
    $rxRecord.pid=$rxProcess.Id
}catch{$rxRecord.launch_error=$_.Exception.Message;throw}
finally{[IO.File]::WriteAllText($rxLaunch,($rxRecord | ConvertTo-Json)+"`n",[Text.UTF8Encoding]::new($false))}
$rxRecord | ConvertTo-Json
