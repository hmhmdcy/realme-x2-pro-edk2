$ErrorActionPreference='Stop'
$out='E:\edk2-samurai-out\kernel135'
$usbipd='C:\Program Files\usbipd-win\usbipd.exe'
$prefix='postflash-readonly-r1'
$keep=$null
$bus=$null
try {
    & "$PSScriptRoot\enable-eud.ps1" -Prefix $prefix
    $lines=(& $usbipd list | Out-String)
    $lines | Set-Content -Encoding utf8NoBOM -LiteralPath "$out\$prefix-enumeration-private.txt"
    $m=[regex]::Matches($lines,'(?m)^([0-9]+-[0-9]+)\s+05c6:9505\s+[^\r\n]*$')
    if ($m.Count -ne 1 -or $m[0].Value -notmatch '\bShared\s*$') {throw 'Unique shared EUD endpoint missing'}
    $bus=$m[0].Groups[1].Value
    $keep=Start-Process -FilePath 'C:\Windows\System32\wsl.exe' -ArgumentList @('-d','Ubuntu','--','sleep','120') -WindowStyle Hidden -PassThru
    & $usbipd attach --wsl --busid $bus
    if ($LASTEXITCODE -ne 0) {throw 'Read-only EUD attach failed'}
    & wsl.exe -d Ubuntu -u root -- bash -c 'mountpoint -q /sys/kernel/debug || mount -t debugfs none /sys/kernel/debug; modprobe usbmon; python3 "/mnt/e/RealmeX2Pro edk2/linux-port/scripts/eud-usb-step.py" --seconds 45 --read-size 16 --out /mnt/e/edk2-samurai-out/kernel135/postflash-readonly-r1' *> "$out\$prefix-tool-private.log"
    if ($LASTEXITCODE -ne 0) {throw 'EUD capture failed; preserve partial capture'}
    Write-Output 'K135_POSTFLASH_READONLY_EUD_CAPTURE_COMPLETE_NO_OUT_OR_RESET'
} finally {
    if ($bus) { & $usbipd detach --busid $bus }
    if ($keep) { if (!$keep.HasExited) {$keep.Kill();$keep.WaitForExit()}; $keep.Dispose() }
}
