param([ValidatePattern('^[a-z0-9-]+$')][string]$Prefix='display')
$ErrorActionPreference='Stop'
$out='E:\edk2-samurai-out\kernel74'
$usbipd='C:\Program Files\usbipd-win\usbipd.exe'
$keep=$null
try {
    $keep=Start-Process -FilePath 'C:\Windows\System32\wsl.exe' -ArgumentList @('-d','Ubuntu','--','sleep','120') -WindowStyle Hidden -PassThru
    & $usbipd attach --wsl --busid 6-5
    if ($LASTEXITCODE -ne 0) {throw 'EUD attach failed'}
    & wsl -d Ubuntu -u root -- bash -c 'for attempt in 1 2 3 4 5 6 7 8 9 10; do if lsusb -d 05c6:9505; then exit 0; fi; sleep 1; done; exit 1'
    if ($LASTEXITCODE -ne 0) {throw 'EUD not visible in WSL'}
    & wsl -d Ubuntu -u root -- python3 '/mnt/e/RealmeX2Pro edk2/linux-port/scripts/eud-usb-step.py' --hex '90 02' --repeat 1 --seconds 15 --ack F1 --read-size 16 --out "/mnt/e/edk2-samurai-out/kernel74/$Prefix-f1-wsl"
} finally {
    & $usbipd detach --busid 6-5
    if ($keep) {
        if (!$keep.HasExited) {$keep.Kill();$keep.WaitForExit()}
        $keep.Dispose()
    }
}
