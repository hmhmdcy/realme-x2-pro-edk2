param([ValidatePattern('^[a-z0-9-]+$')][string]$Prefix,
      [switch]$ProbeLiveness,
      [switch]$RecoverBootloader)
$ErrorActionPreference='Stop'
$out='E:/edk2-samurai-out/kernel152'
$usbipd='C:/Program Files/usbipd-win/usbipd.exe'
$keep=$null
if ($ProbeLiveness -and $RecoverBootloader) {throw 'Select one operation'}
try {
    $keep=Start-Process -FilePath 'C:/Windows/System32/wsl.exe' -ArgumentList @('-d','Ubuntu','--','sleep','120') -WindowStyle Hidden -PassThru
    Start-Sleep -Seconds 2
    & wsl -d Ubuntu -u root -- bash -c 'mountpoint -q /sys/kernel/debug || mount -t debugfs none /sys/kernel/debug; modprobe usbmon; test -r /sys/kernel/debug/usb/usbmon/0u'
    if ($LASTEXITCODE -ne 0) {throw 'Host capture precondition failed'}
    & $usbipd attach --wsl --busid 6-5
    if ($LASTEXITCODE -ne 0) {throw 'EUD attach failed'}
    & wsl -d Ubuntu -u root -- bash -c 'for attempt in 1 2 3 4 5 6 7 8 9 10; do if lsusb -d 05c6:9505; then exit 0; fi; sleep 1; done; exit 1'
    if ($LASTEXITCODE -ne 0) {throw 'EUD enumeration absent'}
    $args152=@('-d','Ubuntu','-u','root','--','python3','/mnt/e/RealmeX2Pro edk2/linux-port/scripts/eud-usb-step.py',
        '--seconds','15','--read-size','16','--out',"/mnt/e/edk2-samurai-out/kernel152/$Prefix")
    if ($ProbeLiveness) {$args152+=@('--hex','90 01 15','--repeat','1')}
    if ($RecoverBootloader) {$args152+=@('--hex','90 02','--repeat','1','--ack','F1')}
    & wsl @args152
    if ($RecoverBootloader) {
        $events=Get-Content -LiteralPath "$out/$Prefix.events.jsonl" | ForEach-Object {$_ | ConvertFrom-Json}
        if (@($events | Where-Object {$_.event -eq 'receipt' -and $_.text -eq 'F1'}).Count -ne 1) {throw 'Recovery F1 not confirmed; inspect device state'}
    } elseif ($LASTEXITCODE -ne 0) {throw 'Capture failed; inspect preserved files'}
} finally {
    & $usbipd detach --busid 6-5
    if($keep){if(!$keep.HasExited){$keep.Kill();$keep.WaitForExit()};$keep.Dispose()}
}
