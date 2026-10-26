$ErrorActionPreference='Stop'
$rxRoot='E:\edk2-samurai-out\rx65'
if(Test-Path -LiteralPath (Join-Path $rxRoot 'wsl-compressed.json')){throw 'Retrieval consumed.'}
if((Get-FileHash -LiteralPath (Join-Path $rxRoot 'eud-usb-full-overlap.py')).Hash.ToLower() -ne 'c145e7f847b01bc0396b0ca1db98da737f012a057b9aeec7802315e0c825f7af'){throw 'Helper differs.'}
$rxOwners=@(Get-CimInstance Win32_Process | Where-Object {$_.ProcessId -ne $PID -and $_.CommandLine -match 'eud-terminal.*\.ps1|eud-usb-.*\.py|driver-log-etw-admin\.ps1'})
if($rxOwners.Count){throw 'Existing owner detected.'}
$rxList=(& 'C:\Program Files\usbipd-win\usbipd.exe' list | Out-String)
if($LASTEXITCODE -ne 0 -or $rxList -notmatch '(?m)^6-5\s+05c6:9505\s+[^\r\n]*Shared\s*$'){throw 'Live target changed.'}
& wsl.exe -d Ubuntu -u root -- python3 /mnt/e/edk2-samurai-out/rx65/prepare-compressed-usbmon.py
if($LASTEXITCODE -ne 0){throw 'WSL trace readiness failed.'}
$rxAttached=$false
try {
  & 'C:\Program Files\usbipd-win\usbipd.exe' attach --wsl --busid 6-5
  if($LASTEXITCODE -ne 0){throw 'Attach failed.'}
  $rxAttached=$true
  & wsl.exe -d Ubuntu -u root -- python3 /mnt/e/edk2-samurai-out/rx65/eud-usb-full-overlap.py --out /mnt/e/edk2-samurai-out/rx65/wsl-compressed --seconds 90
  if($LASTEXITCODE -ne 0){throw 'Bounded retrieval failed.'}
} finally {
  if($rxAttached){& 'C:\Program Files\usbipd-win\usbipd.exe' detach --busid 6-5;if($LASTEXITCODE -ne 0){Write-Error 'Detach failed.'}}
}
