param([ValidatePattern('^[a-z0-9-]+$')][string]$Prefix='sensor-power-first')
$ErrorActionPreference='Stop'
$out='E:\edk2-samurai-out\kernel115'
$known='E:/edk2-samurai-out/kernel109/known_hosts-pmos'
$key='E:/edk2-samurai-out/kernel72/id_ed25519'
$bootId=(Get-Content -LiteralPath "$out\recover-source-boot-id-private.txt" -Raw).Trim()
if ($bootId -notmatch '^[a-f0-9-]{36}$') {throw 'Current private boot guard missing'}
$proc=$null;$keep=$null
try {
    if (Test-Path -LiteralPath "$out\$Prefix-freeze.out") {throw 'Use a fresh attempt prefix'}
    $proc=Start-Process -FilePath 'C:\Windows\System32\OpenSSH\ssh.exe' -ArgumentList @('-T','-i',$key,'-o','StrictHostKeyChecking=yes','-o',"UserKnownHostsFile=$known",'-o','ConnectTimeout=5','root@169.254.42.1',"sh /tmp/k115-freeze-recovery.sh $bootId") -WindowStyle Hidden -PassThru -RedirectStandardOutput "$out\$Prefix-freeze.out" -RedirectStandardError "$out\$Prefix-freeze.err"
    $frozen=$false
    for ($i=0;$i -lt 45;$i++) {
        Start-Sleep -Seconds 1
        if ((Get-Content -LiteralPath "$out\$Prefix-freeze.out" -Raw) -match 'KERNEL115_F2FS_FROZEN_FOR_BOOTLOADER') {$frozen=$true;break}
        if ($proc.HasExited -and $proc.ExitCode -ne 0) {throw 'Quiesce/freeze failed; inspect before retrying'}
    }
    if (!$frozen) {throw 'No successful freeze receipt; do not reboot or flash'}
    Write-Output 'F2FS_FREEZE_RECEIPT_CONFIRMED'
    $usbipd='C:\Program Files\usbipd-win\usbipd.exe'
    $keep=Start-Process -FilePath 'C:\Windows\System32\wsl.exe' -ArgumentList @('-d','Ubuntu','--','sleep','120') -WindowStyle Hidden -PassThru
    & $usbipd attach --wsl --busid 6-5
    if ($LASTEXITCODE -ne 0) {throw 'EUD attach failed; root is frozen and needs a controlled thaw or reboot'}
    & wsl -d Ubuntu -u root -- bash -c 'for attempt in 1 2 3 4 5 6 7 8 9 10; do if lsusb -d 05c6:9505; then exit 0; fi; sleep 1; done; exit 1'
    if ($LASTEXITCODE -ne 0) {throw 'EUD unavailable; frozen root must be thawed before continuing'}
    & wsl -d Ubuntu -u root -- python3 '/mnt/e/RealmeX2Pro edk2/linux-port/scripts/eud-usb-step.py' --hex '90 02' --repeat 1 --seconds 15 --ack F1 --read-size 16 --out "/mnt/e/edk2-samurai-out/kernel115/$Prefix-f1-wsl"
    $events=Get-Content -LiteralPath "$out\$Prefix-f1-wsl.events.jsonl" | ForEach-Object {$_ | ConvertFrom-Json}
    if (!@($events | Where-Object {$_.event -eq 'receipt' -and $_.text -eq 'F1'}).Count) {throw 'F1 receipt absent; inspect the current device before doing anything else'}
    Write-Output 'FROZEN_ROOT_F1_BOOTLOADER_RECEIPT_CONFIRMED'
} finally {
    & 'C:\Program Files\usbipd-win\usbipd.exe' detach --busid 6-5
    foreach ($p in @($proc,$keep)) {
        if ($p) {if (!$p.HasExited) {$p.Kill();$p.WaitForExit()};$p.Dispose()}
    }
}
