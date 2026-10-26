$ErrorActionPreference='Stop'
$rxRoot='E:\edk2-samurai-out\rx60'
$rxLaunchPath=Join-Path $rxRoot 'admin-even-launch.json'
$rxLaunch=Get-Content -Raw -LiteralPath $rxLaunchPath | ConvertFrom-Json
if($rxLaunch.pid -or $rxLaunch.launch_error){throw 'Launch is no longer pending; inspect helper before cancelling.'}
$rxControl=Join-Path $rxRoot 'control-even-01'
# Block any future Arm before registry writes; an already-started helper sees
# restore.request and must finish restoration before any new serial owner.
[IO.Directory]::CreateDirectory($rxControl) | Out-Null
[IO.File]::WriteAllText((Join-Path $rxControl 'restore.request'),'cancel pending launch; no capture will start'+"`n",[Text.UTF8Encoding]::new($false))
$rxTargets=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'powershell.exe' -and $_.CommandLine -match '-File\s+E:\\edk2-samurai-out\\rx60\\launch-authorized-even\.ps1(?:\s|$)'})
if($rxTargets.Count -gt 1){throw 'More than one matching launcher; no process stopped.'}
foreach($rxTarget in $rxTargets){Stop-Process -Id $rxTarget.ProcessId -ErrorAction Stop}
$rxRecord=[ordered]@{utc=[DateTime]::UtcNow.ToString('o');reason='Desktop UAC launch stayed pending; replace the unstarted logger attempt with one bounded no-admin even reversal.';stopped_launcher_pids=@($rxTargets.ProcessId);blocked_control_directory=$rxControl;helper_started=(Test-Path -LiteralPath (Join-Path $rxControl 'backup.json'))}
[IO.File]::WriteAllText((Join-Path $rxRoot 'even-launch-cancelled.json'),($rxRecord | ConvertTo-Json -Depth 4)+"`n",[Text.UTF8Encoding]::new($false))
$rxRecord | ConvertTo-Json -Depth 4
