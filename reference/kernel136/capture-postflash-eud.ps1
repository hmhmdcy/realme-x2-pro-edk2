$ErrorActionPreference='Stop'
$out='E:/edk2-samurai-out/kernel136'
$usbipd='C:/Program Files/usbipd-win/usbipd.exe'
$prefix='postflash-readonly-first'
$keep=$null
$bus=$null
$process=$null
try {
    if (Test-Path -LiteralPath "$out/$prefix-com-up.out") {throw 'Fresh postflash observation required'}
    $process=Start-Process -FilePath 'E:/eud-host/eudtool.exe' -ArgumentList @('com-up') -WindowStyle Hidden -PassThru -RedirectStandardOutput "$out/$prefix-com-up.out" -RedirectStandardError "$out/$prefix-com-up.err"
    if (!$process.WaitForExit(5000)) {throw 'EUD control request timed out; retain observation'}
    $process.WaitForExit()
    if ($process.ExitCode -ne 0) {throw 'EUD enable failed; inspect state'}
    $lines=(& $usbipd list | Out-String)
    $lines | Set-Content -Encoding utf8NoBOM -LiteralPath "$out/$prefix-enumeration-private.txt"
    $matches=[regex]::Matches($lines,'(?m)^([0-9]+-[0-9]+)\s+05c6:9505\s+[^\r\n]*$')
    if ($matches.Count -ne 1 -or $matches[0].Value -notmatch '\bShared\s*$') {throw 'Unique shared EUD endpoint missing'}
    $bus=$matches[0].Groups[1].Value
    $keep=Start-Process -FilePath 'C:/Windows/System32/wsl.exe' -ArgumentList @('-d','Ubuntu','--','sleep','120') -WindowStyle Hidden -PassThru
    & $usbipd attach --wsl --busid $bus
    if ($LASTEXITCODE -ne 0) {throw 'Read-only EUD attach failed'}
    & wsl.exe -d Ubuntu -u root -- bash -c 'mountpoint -q /sys/kernel/debug || mount -t debugfs none /sys/kernel/debug; modprobe usbmon; python3 "/mnt/e/RealmeX2Pro edk2/linux-port/scripts/eud-usb-step.py" --seconds 45 --read-size 16 --out /mnt/e/edk2-samurai-out/kernel136/postflash-readonly-first' *> "$out/$prefix-tool-private.log"
    if ($LASTEXITCODE -ne 0) {throw 'EUD capture failed; retain partial capture'}
    Write-Output 'K136_POSTFLASH_READONLY_EUD_CAPTURE_COMPLETE_NO_OUT_OR_RESET'
} finally {
    if ($bus) { & $usbipd detach --busid $bus }
    foreach ($p in @($keep,$process)) {
        if ($p) {if (!$p.HasExited) {$p.Kill();$p.WaitForExit()}; $p.Dispose()}
    }
}
