$ErrorActionPreference='Stop'
$out='E:/edk2-samurai-out/kernel115'
$deadline=[DateTime]::UtcNow.AddSeconds(180)
while ([DateTime]::UtcNow -lt $deadline) {
    try {
        & "$PSScriptRoot/../kernel109/usb-ssh-pmos.ps1" -Command 'set -eu; uname -v | grep -q "^#115 "; grep -q "^/dev/sda16 / f2fs rw" /proc/mounts; uname -v; cat /proc/sys/kernel/tainted; rc-status default; ls /sys/class/net; cat /proc/swaps' *> "$out/ipa-zram-first-ssh-discovery-private.txt"
        Write-Output 'KERNEL115_FRESH_F2FS_USB_SSH_REACHABLE'
        exit 0
    } catch { Start-Sleep -Seconds 5 }
}
throw 'Kernel115 USB SSH discovery deadline reached; inspect EUD before recovery'
