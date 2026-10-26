param([Parameter(Mandatory)][ValidatePattern('^[a-z0-9-]+$')][string]$Prefix,
      [Parameter(Mandatory)][ValidatePattern('^[a-z0-9-]+$')][string]$PreviousCheckpoint)
$ErrorActionPreference='Stop'
$out='E:\edk2-samurai-out\kernel113'
$discovery="$out\$Prefix-ssh-discovery-private.txt"
if (Test-Path -LiteralPath $discovery) {throw 'Use a fresh discovery prefix'}
$command='set -eu; uname -v | grep -q "^#113 "; test "$(cat /proc/sys/kernel/random/boot_id)" != "$(cat /var/lib/samurai/k113-{0}/boot-id-private.txt)"; grep -q "^/dev/sda16 / f2fs rw" /proc/mounts; printf "TAINT="; cat /proc/sys/kernel/tainted; printf "SLPI="; cat /sys/class/remoteproc/remoteproc0/state; cat /sys/devices/platform/sensor-power/state' -f $PreviousCheckpoint
$deadline=[DateTime]::UtcNow.AddSeconds(300)
$reachable=$false
while ([DateTime]::UtcNow -lt $deadline) {
    try {
        & "$PSScriptRoot\..\kernel109\usb-ssh-pmos.ps1" -Command $command *> $discovery
        $reachable=$true
        break
    } catch {Start-Sleep -Seconds 5}
}
if (!$reachable) {throw 'Fresh-root SSH discovery deadline reached; inspect logs before recovery'}
Write-Output 'FRESH_USB_SSH_REACHABLE_HEALTH_CHECK_IS_SEPARATE'
$collect='set -eu; sh /var/lib/samurai/k113-tools/collect-runtime.sh {0}' -f $Prefix
& "$PSScriptRoot\..\kernel109\usb-ssh-pmos.ps1" -Command $collect
