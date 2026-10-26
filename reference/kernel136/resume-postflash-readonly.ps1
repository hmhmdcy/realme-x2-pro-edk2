$ErrorActionPreference='Stop'
$out='E:/edk2-samurai-out/kernel136'
$usbipd='C:/Program Files/usbipd-win/usbipd.exe'
$prefix='postflash-readonly-resume'
$keep=$null
$attached=$false
try {
    $endpointRows=@(& $usbipd list | Where-Object { $_ -like '6-5*05c6:9505*Shared' })
    if ($endpointRows.Count -ne 1) {throw 'Observed shared EUD endpoint missing'}
    if (Test-Path -LiteralPath "$out/$prefix-tool-private.log") {throw 'Fresh read-only capture required'}
    $keep=Start-Process -FilePath 'C:/Windows/System32/wsl.exe' -ArgumentList @('-d','Ubuntu','--','sleep','120') -WindowStyle Hidden -PassThru
    & $usbipd attach --wsl --busid 6-5
    if ($LASTEXITCODE -ne 0) {throw 'Read-only EUD attach failed'}
    $attached=$true
    & wsl.exe -d Ubuntu -u root -- bash -c 'mountpoint -q /sys/kernel/debug || mount -t debugfs none /sys/kernel/debug; modprobe usbmon; python3 "/mnt/e/RealmeX2Pro edk2/linux-port/scripts/eud-usb-step.py" --seconds 45 --read-size 16 --out /mnt/e/edk2-samurai-out/kernel136/postflash-readonly-resume' *> "$out/$prefix-tool-private.log"
    if ($LASTEXITCODE -ne 0) {throw 'Read-only EUD capture failed; preserve output'}
    Write-Output 'K136_POSTFLASH_PASSIVE_CAPTURE_COMPLETE_NO_CONTROL_REPEAT_NO_OUT'
} finally {
    if ($attached) { & $usbipd detach --busid 6-5 }
    if ($keep) {if (!$keep.HasExited) {$keep.Kill();$keep.WaitForExit()}; $keep.Dispose()}
}
