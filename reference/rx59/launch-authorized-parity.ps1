$ErrorActionPreference='Stop'
$rxRoot='E:\edk2-samurai-out\rx59'
$rxHelper=Join-Path $rxRoot 'driver-log-etw-admin.ps1'
$rxLaunch=Join-Path $rxRoot 'admin-parity-launch.json'
if(Test-Path -LiteralPath $rxLaunch){throw 'This launch was already attempted; preserve its evidence.'}
if((Get-FileHash -LiteralPath $rxHelper).Hash.ToLower() -ne '18c0f157d4c9fd603fe6caacdc1be5028b46d481378abb742dbdf58c9c604f64'){throw 'Reviewed admin helper differs.'}
if(Test-Path -LiteralPath (Join-Path $rxRoot 'control-parity-01')){throw 'Original control directory exists.'}
$rxRecord=[ordered]@{utc=[DateTime]::UtcNow.ToString('o');authorization='Human provided continuing authorization for the same scoped COM14 diagnostics; RX59 parity protocol recorded before launch.';helper_sha256='18c0f157d4c9fd603fe6caacdc1be5028b46d481378abb742dbdf58c9c604f64';pid=$null;launch_error=$null}
[IO.File]::WriteAllText($rxLaunch,($rxRecord | ConvertTo-Json)+"`n",[Text.UTF8Encoding]::new($false))
try {
    $rxProcess=Start-Process -FilePath 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',$rxHelper,'-Mode','Arm') -Verb RunAs -WindowStyle Hidden -PassThru
    $rxRecord.pid=$rxProcess.Id
}catch{$rxRecord.launch_error=$_.Exception.Message;throw}
finally{[IO.File]::WriteAllText($rxLaunch,($rxRecord | ConvertTo-Json)+"`n",[Text.UTF8Encoding]::new($false))}
$rxRecord | ConvertTo-Json
