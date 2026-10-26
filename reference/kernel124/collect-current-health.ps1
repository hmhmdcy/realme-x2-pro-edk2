$ErrorActionPreference='Stop'
$command=@'
set -eu
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k119-first-runtime/boot-id-private.txt)"
uname -v
cat /proc/sys/kernel/tainted
pgrep -x phosh
pgrep -x phoc
dmesg | grep -c 'frame done timeout'
dmesg | grep -c '\*\*\* gpu fault'
cat /proc/asound/card0/pcm0p/sub0/status /proc/asound/card0/pcm1c/sub0/status
cat /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status
cat /sys/class/remoteproc/remoteproc0/state /sys/devices/platform/sensor-power/state
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt
sha256sum -c /var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256
sha256sum -c /var/lib/samurai/k115-vendor-camera-source/vendor-before.sha256
'@
$result=& 'E:/RealmeX2Pro edk2/reference/kernel109/usb-ssh-pmos.ps1' -Command $command
$result | Set-Content -LiteralPath 'E:/edk2-samurai-out/kernel124/runtime-health-final-private.txt' -Encoding utf8NoBOM
Write-Output 'K124_SAME_BOOT_READONLY_PHONE_SNAPSHOT_PRIVATE_SAVED'
