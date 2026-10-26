$ErrorActionPreference='Stop'
$rxRoot='E:\edk2-samurai-out\rx65'
$rxBaseline=Get-Content -Raw -LiteralPath (Join-Path $rxRoot 'baseline-state.json') -Encoding UTF8 | ConvertFrom-Json
$rxBus=$rxBaseline.busid
if($rxBus -ne '6-5'){throw 'Prepared target bus changed; inspect before attaching.'}
if((Get-FileHash -LiteralPath (Join-Path $rxRoot 'eud-usb-full-overlap.py')).Hash.ToLower() -ne 'c145e7f847b01bc0396b0ca1db98da737f012a057b9aeec7802315e0c825f7af'){throw 'Helper differs.'}
if(Test-Path -LiteralPath (Join-Path $rxRoot 'wsl-full.raw')){throw 'Single-use experiment consumed.'}
$rxOwners=@(Get-CimInstance Win32_Process | Where-Object {$_.ProcessId -ne $PID -and $_.CommandLine -match 'eud-terminal.*\.ps1|eud-console-overlap\.ps1|eud-usb-.*\.py|capture-windows-.*\.ps1|driver-log-etw-admin\.ps1'})
if($rxOwners.Count){throw 'Existing owner detected.'}
$rxAttached=$false
try {
  & 'C:\Program Files\usbipd-win\usbipd.exe' attach --wsl --busid $rxBus
  if($LASTEXITCODE -ne 0){throw 'Attach failed; no forcebind or retry.'}
  $rxAttached=$true
  & wsl.exe -d Ubuntu -u root -- python3 /mnt/e/edk2-samurai-out/rx65/eud-usb-full-overlap.py --out /mnt/e/edk2-samurai-out/rx65/wsl-full --seconds 180
  $rxExit=$LASTEXITCODE
  if($rxExit -ne 0){throw ('Bounded owner ended with exit '+$rxExit)}
} finally {
  if($rxAttached){& 'C:\Program Files\usbipd-win\usbipd.exe' detach --busid $rxBus;if($LASTEXITCODE -ne 0){Write-Error 'Detach failed; inspect the same target before proceeding.'}}
}
