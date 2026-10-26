$ErrorActionPreference='Stop'
$rxRoot='E:\edk2-samurai-out\rx58'
$rxHelper=Join-Path $rxRoot 'driver-log-etw-admin.ps1'
$rxLaunch=Join-Path $rxRoot 'admin-first-status-launch.json'
if(Test-Path -LiteralPath $rxLaunch){throw 'This launch was already attempted; preserve its evidence.'}
if((Get-FileHash -LiteralPath $rxHelper).Hash.ToLower() -ne 'dcee7311408c7d61201645b0ec74e701235775428d9c78dd72ee8acd260db09e'){throw 'Reviewed admin helper differs.'}
if(Test-Path -LiteralPath (Join-Path $rxRoot 'control-first-status-01')){throw 'Original control directory exists.'}
$rxRecord=[ordered]@{utc=[DateTime]::UtcNow.ToString('o');authorization='Human provided continuing authorization after the RX58 joint capture plan was presented.';helper_sha256='dcee7311408c7d61201645b0ec74e701235775428d9c78dd72ee8acd260db09e';pid=$null;launch_error=$null}
[IO.File]::WriteAllText($rxLaunch,($rxRecord | ConvertTo-Json)+"`n",[Text.UTF8Encoding]::new($false))
try {
    $rxProcess=Start-Process -FilePath 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',$rxHelper,'-Mode','Arm') -Verb RunAs -WindowStyle Hidden -PassThru
    $rxRecord.pid=$rxProcess.Id
}catch{$rxRecord.launch_error=$_.Exception.Message;throw}
finally{[IO.File]::WriteAllText($rxLaunch,($rxRecord | ConvertTo-Json)+"`n",[Text.UTF8Encoding]::new($false))}
$rxRecord | ConvertTo-Json
