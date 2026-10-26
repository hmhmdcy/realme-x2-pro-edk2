param([ValidatePattern('^[a-z0-9-]+$')][string]$Prefix='before-ctl-ram')
$ErrorActionPreference='Stop'
$out='E:/edk2-samurai-out/kernel158'
$boot=(Get-Content -Raw -LiteralPath "$out/source-boot-id-private.txt").Trim()
if ($boot -notmatch '^[a-f0-9-]{36}$') {throw 'Current RAM identity missing'}
$proof=& "$PSScriptRoot/../kernel72/usb-ssh.ps1" -Command "sh /tmp/k158-check-current-ram.sh $boot"
if ($proof -notcontains 'K158_CURRENT157_RAM_ONLY_NO_DISK_FILESYSTEM_VERIFIED') {throw 'Fresh RAM-only proof absent'}
$proof | Set-Content -LiteralPath "$out/$Prefix-ram-proof.txt" -Encoding utf8NoBOM
$enum=(& 'C:/Program Files/usbipd-win/usbipd.exe' list | Out-String).Replace("`r",'')
if ($enum -notmatch '(?m)^6-5\s+05c6:9505\s+[^\n]*Shared\s*$') {throw 'Actual EUD endpoint is not uniquely shared'}
$enum | Set-Content -LiteralPath "$out/$Prefix-eud-enumeration-private.txt" -Encoding utf8NoBOM
if (Test-Path -LiteralPath "$out/$Prefix-f1-wsl.events.jsonl") {throw 'F1 attempt already recorded; inspect state'}
$keep=Start-Process -FilePath 'C:/Windows/System32/wsl.exe' -ArgumentList @('-d','Ubuntu','--','sleep','120') -WindowStyle Hidden -PassThru
try {
 & wsl -d Ubuntu -u root -- bash -c 'mountpoint -q /sys/kernel/debug || mount -t debugfs none /sys/kernel/debug; modprobe usbmon; test -r /sys/kernel/debug/usb/usbmon/0u'
 if ($LASTEXITCODE -ne 0) {throw 'Host usbmon precondition missing'}
 & 'C:/Program Files/usbipd-win/usbipd.exe' attach --wsl --busid 6-5
 if ($LASTEXITCODE -ne 0) {throw 'Current endpoint attachment failed'}
 & wsl -d Ubuntu -u root -- bash -c 'for attempt in 1 2 3 4 5; do if lsusb -d 05c6:9505; then exit 0; fi; sleep 1; done; exit 1'
 if ($LASTEXITCODE -ne 0) {throw 'Actual endpoint not visible'}
 & wsl -d Ubuntu -u root -- python3 '/mnt/e/RealmeX2Pro edk2/linux-port/scripts/eud-usb-step.py' --hex '90 02' --repeat 1 --seconds 15 --ack F1 --read-size 16 --out "/mnt/e/edk2-samurai-out/kernel158/$Prefix-f1-wsl" *> "$out/$Prefix-f1-step-private.log"
 $events=Get-Content -LiteralPath "$out/$Prefix-f1-wsl.events.jsonl" | ForEach-Object {$_ | ConvertFrom-Json}
 if (@($events | Where-Object {$_.event -eq 'receipt' -and $_.text -eq 'F1'}).Count -ne 1 -or @($events | Where-Object {$_.event -eq 'out_submit'}).Count -ne 1) {throw 'Single accepted F1 transition not confirmed'}
 Write-Output K158_RAM_F1_RECEIPT_CONFIRMED
} finally {
 & 'C:/Program Files/usbipd-win/usbipd.exe' detach --busid 6-5
 if (!$keep.HasExited) {$keep.Kill();$keep.WaitForExit()};$keep.Dispose()
}
