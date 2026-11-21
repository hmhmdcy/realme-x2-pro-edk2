[CmdletBinding()]
param(
    [string]$Serial = "62bc28a1",
    [string]$Image = "E:\edk2-samurai-out\standard-arm64-v731\rootfs-stable-20261119-clean\samurai-stable-f2fs-partuuid.simg",
    [string]$Adb = "E:\edk2-samurai-out\standard-arm64-v731\platform-tools\platform-tools\adb.exe",
    [string]$ExpectedHash = "54d9768acedaccd4245960ff13558c03c5b750214b151c5c05847bfce71e0fc3",
    [int64]$ExpectedBytes = 3644199308,
    [switch]$Confirm,
    [switch]$Reboot
)

# Flashes the rootfs through TWRP instead of fastboot.
#
# Why this path exists: this bootloader's USB command channel wedges after a
# large write (reboot/continue/getvar all fail with error 121), so every
# fastboot flash needs a manual power cycle.  TWRP keeps a working adb shell
# through the whole write and can expand the sparse image straight onto the
# block device with its own simg2img.
#
# Only userdata (/dev/block/sda16) is touched.  boot, logdump and the DTB
# partition are untouched, so a bad rootfs still leaves fastboot/UEFI intact.

$ErrorActionPreference = "Stop"

function Invoke-Adb {
    param([string[]]$Arguments)
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $out = & $Adb @Arguments 2>&1 | ForEach-Object { "$_" } | Out-String
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previous
    }
    if ($code -ne 0) { throw "adb $($Arguments -join ' ') failed with exit code $code`n$out" }
    return $out
}

if (-not (Test-Path -LiteralPath $Image)) { throw "image not found: $Image" }
if (-not (Test-Path -LiteralPath $Adb)) { throw "adb not found: $Adb" }

$item = Get-Item -LiteralPath $Image
if ($item.Length -ne $ExpectedBytes) {
    throw "image size mismatch: expected $ExpectedBytes, got $($item.Length)"
}
$hash = (Get-FileHash -LiteralPath $Image -Algorithm SHA256).Hash.ToLowerInvariant()
if ($hash -ne $ExpectedHash.ToLowerInvariant()) { throw "image hash mismatch: got $hash" }
Write-Host "image verified: $([math]::Round($item.Length/1GB,2)) GiB sha256=$hash"

$devices = Invoke-Adb -Arguments @("devices")
$match = $devices -split "`r?`n" | Where-Object { $_ -match "^$Serial\s+recovery" }
if (-not $match) {
    throw "device $Serial is not in recovery. Boot TWRP and enable adb."
}
Write-Host "target: $Serial (recovery)"

# TWRP keeps /data mounted.  A df check refuses early if /tmp cannot hold the
# sparse image, which is the only failure mode that needs planning.
$df = Invoke-Adb -Arguments @("shell", "df -k /tmp | tail -1")
$freeKb = [int64]($df -split "\s+" | Where-Object { $_ -match '^\d+$' } | Select-Object -Index 3)
if ($freeKb -lt ($item.Length / 1024)) {
    throw "/tmp has $([math]::Round($freeKb/1048576,2)) GiB free; the image needs $([math]::Round($item.Length/1GB,2)) GiB"
}

if (-not $Confirm) {
    Write-Host "dry run only; nothing was written." -ForegroundColor Yellow
    Write-Host "to flash: .\flash-from-recovery.ps1 -Confirm:`$true -Reboot"
    return
}

Write-Host "pushing image to /tmp/flash (this takes a few minutes)"
Invoke-Adb -Arguments @("shell", "rm -rf /tmp/flash; mkdir -p /tmp/flash") | Out-Null
Invoke-Adb -Arguments @("push", $Image, "/tmp/flash/rootfs.simg") | Out-Null

# Verify the copy on the phone: a truncated push would otherwise be expanded
# into userdata and only fail later at boot.
$deviceHash = (Invoke-Adb -Arguments @("shell", "sha256sum /tmp/flash/rootfs.simg")).Trim()
if ($deviceHash -notmatch $ExpectedHash.ToLowerInvariant()) {
    throw "hash mismatch on device: $deviceHash"
}
Write-Host "device copy verified" -ForegroundColor Green

Write-Host "unmounting /data and expanding the sparse image onto sda16"
Invoke-Adb -Arguments @("shell", "umount /sdcard 2>/dev/null; umount /data 2>/dev/null; mount | grep -c sda16") | Out-Null
Invoke-Adb -Arguments @(
    "shell",
    "simg2img /tmp/flash/rootfs.simg /dev/block/sda16 && sync && echo EXPAND_OK"
) | Out-Null

Write-Host "checking the written filesystem"
$verify = Invoke-Adb -Arguments @(
    "shell",
    "mount -t f2fs -o ro,norecovery /dev/block/sda16 /mnt/vfy && " +
    "grep -E '^PRETTY_NAME' /mnt/vfy/etc/os-release && " +
    "grep -c '^P:' /mnt/vfy/lib/apk/db/installed && " +
    "umount /mnt/vfy"
)
Write-Host $verify.Trim()

Invoke-Adb -Arguments @("shell", "rm -f /tmp/flash/rootfs.simg; sync") | Out-Null
Write-Host "flash complete; userdata written." -ForegroundColor Green

if ($Reboot) {
    Invoke-Adb -Arguments @("reboot") | Out-Null
    Write-Host "rebooting into the new rootfs"
} else {
    Write-Host "reboot when ready: adb reboot"
}
