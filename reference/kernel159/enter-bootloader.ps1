param([ValidatePattern('^[a-z0-9-]+$')][string]$Prefix='same158-second')
$ErrorActionPreference='Stop'
$out='E:\edk2-samurai-out\kernel159'
$known='E:/edk2-samurai-out/kernel109/known_hosts-pmos'
$key='E:/edk2-samurai-out/kernel72/id_ed25519'
$bootId=(Get-Content -LiteralPath "$out\source-boot-id-private.txt" -Raw).Trim()
if ($bootId -notmatch '^[a-f0-9-]{36}$') {throw 'Current private boot guard missing'}
$quiesce=Get-Content -LiteralPath "$out\quiesce-validation.json" -Raw | ConvertFrom-Json
if (!$quiesce.quiesce_audit_pass -or $quiesce.boot_id -ne $bootId -or !$quiesce.gui_user_and_drm_crtcs_quiesced -or !$quiesce.all_remoteprocs_offline) {throw 'Current boot full quiesce proof absent'}
$enum=(& 'C:\Program Files\usbipd-win\usbipd.exe' list | Out-String).Replace("`r",'')
$eudLines=[regex]::Matches($enum,'(?m)^6-5\s+05c6:9505\s+[^\n]*$')
if($eudLines.Count -ne 1 -or $eudLines[0].Value.TrimEnd() -notlike '*Shared'){throw 'Enable and verify the unique shared EUD endpoint before freezing'}
$enum | Set-Content -LiteralPath "$out\$Prefix-eud-enumeration-private.txt" -Encoding utf8NoBOM
$proc=$null;$keep=$null;$frozen=$false;$receipt=$false
try {
    if (Test-Path -LiteralPath "$out\$Prefix-freeze.out") {throw 'Use a fresh attempt prefix'}
    $keep=Start-Process -FilePath 'C:\Windows\System32\wsl.exe' -ArgumentList @('-d','Ubuntu','--','sleep','120') -WindowStyle Hidden -PassThru
    & wsl -d Ubuntu -u root -- bash -c 'mountpoint -q /sys/kernel/debug || mount -t debugfs none /sys/kernel/debug; modprobe usbmon; test -r /sys/kernel/debug/usb/usbmon/0u'
    if ($LASTEXITCODE -ne 0) {throw 'Host usbmon precondition failed before freezing root'}
    $proc=Start-Process -FilePath 'C:\Windows\System32\OpenSSH\ssh.exe' -ArgumentList @('-T','-i',$key,'-o','StrictHostKeyChecking=yes','-o',"UserKnownHostsFile=$known",'-o','ConnectTimeout=5','root@169.254.42.1',"sh /tmp/k159-freeze-for-bootloader.sh $bootId") -WindowStyle Hidden -PassThru -RedirectStandardOutput "$out\$Prefix-freeze.out" -RedirectStandardError "$out\$Prefix-freeze.err"
    $frozen=$false
    for ($i=0;$i -lt 45;$i++) {
        Start-Sleep -Seconds 1
        if ((Get-Content -LiteralPath "$out\$Prefix-freeze.out" -Raw) -match 'K159_F2FS_FROZEN_FOR_BOOTLOADER') {$frozen=$true;break}
        if ($proc.HasExited -and $proc.ExitCode -ne 0) {throw 'Quiesce/freeze failed; inspect before retrying'}
    }
    if (!$frozen) {throw 'No successful freeze receipt; do not reboot or flash'}
    Write-Output 'F2FS_FREEZE_RECEIPT_CONFIRMED'
    $usbipd='C:\Program Files\usbipd-win\usbipd.exe'
    & $usbipd attach --wsl --busid 6-5
    if ($LASTEXITCODE -ne 0) {throw 'EUD attach failed; root is frozen and needs a controlled thaw or reboot'}
    & wsl -d Ubuntu -u root -- bash -c 'for attempt in 1 2 3 4 5 6 7 8 9 10; do if lsusb -d 05c6:9505; then exit 0; fi; sleep 1; done; exit 1'
    if ($LASTEXITCODE -ne 0) {throw 'EUD unavailable; frozen root must be thawed before continuing'}
    & wsl -d Ubuntu -u root -- python3 '/mnt/e/RealmeX2Pro edk2/linux-port/scripts/eud-usb-step.py' --hex '90 02' --repeat 1 --seconds 15 --ack F1 --read-size 16 --out "/mnt/e/edk2-samurai-out/kernel159/$Prefix-f1-wsl"
    $events=Get-Content -LiteralPath "$out\$Prefix-f1-wsl.events.jsonl" | ForEach-Object {$_ | ConvertFrom-Json}
    if (!@($events | Where-Object {$_.event -eq 'receipt' -and $_.text -eq 'F1'}).Count) {throw 'F1 receipt absent; inspect the current device before doing anything else'}
    $receipt=$true
    Write-Output 'FROZEN_ROOT_F1_BOOTLOADER_RECEIPT_CONFIRMED'
} finally {
    if ($frozen -and !$receipt) {
        try {
            $thaw=& 'E:/RealmeX2Pro edk2/reference/kernel109/usb-ssh-pmos.ps1' -Command "test `"`$(cat /proc/sys/kernel/random/boot_id)`" = '$bootId' && fsfreeze -u / && echo K159_CONTROLLED_THAW"
            $thaw | Set-Content -LiteralPath "$out\$Prefix-thaw-private.txt" -Encoding utf8NoBOM
        } catch { $_ | Out-String | Set-Content -LiteralPath "$out\$Prefix-thaw-error-private.txt" -Encoding utf8NoBOM }
    }
    & 'C:\Program Files\usbipd-win\usbipd.exe' detach --busid 6-5
    foreach ($p in @($proc,$keep)) {
        if ($p) {if (!$p.HasExited) {$p.Kill();$p.WaitForExit()};$p.Dispose()}
    }
}
