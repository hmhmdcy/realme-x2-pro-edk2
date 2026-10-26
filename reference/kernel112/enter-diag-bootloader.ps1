param([ValidatePattern('^[a-z0-9-]+$')][string]$Prefix='startup-first')
$ErrorActionPreference='Stop'
$out='E:\edk2-samurai-out\kernel112'
$id=(Get-Content -LiteralPath "$out\source-boot-id-private.txt" -Raw).Trim()
if ($id -notmatch '^[a-f0-9-]{36}$') {throw 'Current boot guard missing'}
$audit=Get-Content -LiteralPath "$out\candidate-validation.json" -Raw | ConvertFrom-Json
if (Test-Path -LiteralPath "$out\$Prefix-quiesce.out") {throw 'Fresh prefix required'}
& "$PSScriptRoot\..\kernel111\usb-ssh-diagnostic.ps1" -Command "sh /tmp/k112-prepare-diag-reboot.sh $id $($audit.boot_sha256) $($audit.before_logdump_sha256)" > "$out\$Prefix-quiesce.out"
if ((Get-Content -LiteralPath "$out\$Prefix-quiesce.out" -Raw) -notmatch 'KERNEL112_DIAGNOSTIC_ROOT_NO_BLOCK_MOUNTS_REBOOT_READY') {throw 'Diagnostic root guard failed'}
$usbipd='C:\Program Files\usbipd-win\usbipd.exe';$keep=$null
try {
    $keep=Start-Process -FilePath 'C:\Windows\System32\wsl.exe' -ArgumentList @('-d','Ubuntu','--','sleep','120') -WindowStyle Hidden -PassThru
    & $usbipd attach --wsl --busid 6-5
    if ($LASTEXITCODE -ne 0) {throw 'EUD attach failed'}
    & wsl -d Ubuntu -u root -- bash -c 'for i in 1 2 3 4 5 6 7 8 9 10; do if lsusb -d 05c6:9505; then exit 0; fi; sleep 1; done; exit 1'
    if ($LASTEXITCODE -ne 0) {throw 'EUD unavailable'}
    & wsl -d Ubuntu -u root -- python3 '/mnt/e/RealmeX2Pro edk2/linux-port/scripts/eud-usb-step.py' --hex '90 02' --repeat 1 --seconds 15 --ack F1 --read-size 16 --out "/mnt/e/edk2-samurai-out/kernel112/$Prefix-f1-wsl"
    $events=Get-Content -LiteralPath "$out\$Prefix-f1-wsl.events.jsonl" | ForEach-Object {$_ | ConvertFrom-Json}
    if (!@($events | Where-Object {$_.event -eq 'receipt' -and $_.text -eq 'F1'}).Count) {throw 'F1 receipt absent'}
    Write-Output 'DIAGNOSTIC_ROOT_F1_BOOTLOADER_RECEIPT_CONFIRMED'
} finally {
    & $usbipd detach --busid 6-5
    if ($keep) {if (!$keep.HasExited) {$keep.Kill();$keep.WaitForExit()};$keep.Dispose()}
}
