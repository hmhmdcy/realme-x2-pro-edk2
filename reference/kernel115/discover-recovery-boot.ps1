$ErrorActionPreference='Stop'
$out='E:/edk2-samurai-out/kernel115'
$deadline=[DateTime]::UtcNow.AddSeconds(300)
while ([DateTime]::UtcNow -lt $deadline) {
    try {
        & "$PSScriptRoot/../kernel109/usb-ssh-pmos.ps1" -Command 'set -eu; uname -v | grep -q "^#115 "; test "$(cat /proc/sys/kernel/random/boot_id)" != "$(cat /var/lib/samurai/k115-delay-fix-runtime/boot-id-private.txt)"; grep -q "^/dev/sda16 / f2fs rw" /proc/mounts; uname -v; cat /proc/sys/kernel/tainted; rc-status default; cat /proc/swaps' *> "$out/display-recovery-ssh-discovery-private.txt"
        Write-Output 'KERNEL115_FRESH_DISPLAY_RECOVERY_BOOT_USB_SSH_REACHABLE'
        exit 0
    } catch { Start-Sleep -Seconds 5 }
}
throw 'Recovery boot discovery deadline reached; inspect EUD before next action'
