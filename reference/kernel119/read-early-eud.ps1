param([ValidatePattern('^[a-z0-9-]+$')][string]$Prefix='postflash')
$ErrorActionPreference='Stop'
$usbipd='C:\Program Files\usbipd-win\usbipd.exe'
$keep=$null
try {
    $keep=Start-Process -FilePath 'C:\Windows\System32\wsl.exe' -ArgumentList @('-d','Ubuntu','--','sleep','120') -WindowStyle Hidden -PassThru
    & wsl -d Ubuntu -u root -- bash -c 'mountpoint -q /sys/kernel/debug || mount -t debugfs none /sys/kernel/debug; modprobe usbmon; test -r /sys/kernel/debug/usb/usbmon/0u'
    if ($LASTEXITCODE -ne 0) {throw 'Host usbmon precondition failed'}
    # com-up completion can precede Windows USB re-enumeration.
    $enumerationDeadline=[DateTime]::UtcNow.AddSeconds(15)
    $enumerated=$false
    while ([DateTime]::UtcNow -lt $enumerationDeadline) {
        $inventory=& $usbipd state | ConvertFrom-Json
        if ($LASTEXITCODE -ne 0) {throw 'USB inventory failed'}
        $matches=@($inventory.Devices | Where-Object { $_.BusId -eq '6-5' -and $_.InstanceId -match 'VID_05C6&PID_9505' })
        if ($matches.Count -eq 1) {$enumerated=$true;break}
        Start-Sleep -Milliseconds 500
    }
    if (!$enumerated) {throw 'Expected EUD port did not enumerate within 15 seconds'}
    & $usbipd attach --wsl --busid 6-5
    if ($LASTEXITCODE -ne 0) {throw 'EUD attach failed'}
    & wsl -d Ubuntu -u root -- bash -c 'for attempt in 1 2 3 4 5 6 7 8 9 10; do if lsusb -d 05c6:9505; then exit 0; fi; sleep 1; done; exit 1'
    if ($LASTEXITCODE -ne 0) {throw 'EUD not visible in WSL'}
    & wsl -d Ubuntu -u root -- python3 '/mnt/e/RealmeX2Pro edk2/linux-port/scripts/eud-usb-step.py' --seconds 45 --read-size 16 --out "/mnt/e/edk2-samurai-out/kernel119/$Prefix-read-wsl"
    if ($LASTEXITCODE -ne 0) {throw 'Bounded EUD capture failed'}
} finally {
    & $usbipd detach --busid 6-5
    if ($keep) {
        if (!$keep.HasExited) {$keep.Kill();$keep.WaitForExit()}
        $keep.Dispose()
    }
}

