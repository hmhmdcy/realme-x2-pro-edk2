$ErrorActionPreference='Stop'
$out='E:/edk2-samurai-out/kernel137'
$usbipd='C:/Program Files/usbipd-win/usbipd.exe'
$prefix='postflash-readonly-first'
$keep=$null
$process=$null
$attached=$false
try {
    if (Test-Path -LiteralPath "$out/$prefix-com-up.out") {throw 'Fresh postflash observation required'}
    $process=Start-Process -FilePath 'E:/eud-host/eudtool.exe' -ArgumentList @('com-up') -WindowStyle Hidden -PassThru -RedirectStandardOutput "$out/$prefix-com-up.out" -RedirectStandardError "$out/$prefix-com-up.err"
    if (!$process.WaitForExit(5000)) {throw 'EUD control request incomplete; retain observation'}
    $process.WaitForExit()
    if ($process.ExitCode -ne 0) {throw 'EUD enable failed; inspect state'}
    $endpointRows=@(& $usbipd list | Where-Object { $_ -like '6-5*05c6:9505*Shared' })
    if ($endpointRows.Count -ne 1) {throw 'Unique shared EUD endpoint missing'}
    $keep=Start-Process -FilePath 'C:/Windows/System32/wsl.exe' -ArgumentList @('-d','Ubuntu','--','sleep','120') -WindowStyle Hidden -PassThru
    & $usbipd attach --wsl --busid 6-5
    if ($LASTEXITCODE -ne 0) {throw 'Read-only EUD attach failed'}
    $attached=$true
    & wsl.exe -d Ubuntu -u root -- bash -c 'mountpoint -q /sys/kernel/debug || mount -t debugfs none /sys/kernel/debug; modprobe usbmon; python3 "/mnt/e/RealmeX2Pro edk2/linux-port/scripts/eud-usb-step.py" --seconds 45 --read-size 16 --out /mnt/e/edk2-samurai-out/kernel137/postflash-readonly-first' *> "$out/$prefix-tool-private.log"
    if ($LASTEXITCODE -ne 0) {throw 'Read-only EUD capture failed; preserve output'}
    Write-Output 'K137_POSTFLASH_PASSIVE_CAPTURE_COMPLETE_NO_OUT'
} finally {
    if ($attached) { & $usbipd detach --busid 6-5 }
    foreach ($p in @($keep,$process)) {
        if ($p) {if (!$p.HasExited) {$p.Kill();$p.WaitForExit()};$p.Dispose()}
    }
}
