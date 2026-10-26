#!/bin/sh
set -eu
umask 077
uname -v | grep -q '^#115 '
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k115-final-health/boot-id-private.txt)"
test "$(cat /proc/sys/kernel/tainted)" = 0
test "$(cat /sys/class/remoteproc/remoteproc0/name)" = slpi
test "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline
test -z "$(pidof hexagonrpcd)"
grep -q '^/dev/sda16 / f2fs rw' /proc/mounts
test "$(id -u cy122)" = 10000
pgrep -x phosh >/dev/null
pgrep -x phoc >/dev/null
test -c /dev/dri/card0
test -c /dev/dri/renderD128
test "$(cat /sys/devices/platform/sensor-power/state)" = 'vdd=0 vddio=0'
dest=/var/lib/samurai/k119-preflash
test ! -e "$dest"
mkdir -m700 "$dest"
for dev in sda sdb sdc sdd sde sdf; do
    sectors=$(blockdev --getsz "/dev/$dev")
    block=$(blockdev --getss "/dev/$dev")
    test "$block" = 4096
    test "$((sectors % 8))" = 0
    blocks=$((sectors / 8))
    blockdev --getsz "/dev/$dev" > "$dest/$dev.geometry"
    blockdev --getss "/dev/$dev" >> "$dest/$dev.geometry"
    cat "/sys/block/$dev/device/model" >> "$dest/$dev.geometry"
    dd if="/dev/$dev" of="$dest/$dev.head" bs=4096 count=34 status=none
    dd if="/dev/$dev" of="$dest/$dev.tail" bs=4096 skip=$((blocks - 34)) count=34 status=none
done
sha256sum /dev/sde11 /dev/sde32 /dev/sda2 > "$dest/partition-check.sha256"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-check.txt"
sha256sum -c /var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256 > "$dest/source-check.txt"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
sha256sum -c /var/lib/samurai/k115-vendor-camera-source/vendor-before.sha256 > "$dest/vendor-check.txt"
sha256sum /lib/modules/7.3.0-rc6-rmx1931-samurai+/kernel/drivers/net/ipa/ipa.ko > "$dest/ipa-module.sha256"
pgrep -x phosh > "$dest/phosh.txt"
pgrep -x phoc > "$dest/phoc.txt"
cat /sys/class/drm/card0-DSI-1/status > "$dest/connector.txt"
cat /sys/class/remoteproc/remoteproc0/state /sys/devices/platform/sensor-power/state > "$dest/sensors.txt"
cat /sys/kernel/tracing/instances/display/tracing_on /sys/kernel/tracing/instances/radio/tracing_on > "$dest/traces.txt"
cat /proc/asound/card0/pcm0p/sub0/status /proc/asound/card0/pcm1c/sub0/status > "$dest/pcm.txt"
cat /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status > "$dest/amps.txt"
cat /proc/uptime /proc/sys/kernel/tainted > "$dest/state.txt"
dmesg > "$dest/dmesg.txt"
cat /proc/mounts > "$dest/mounts.txt"
uname -a > "$dest/uname.txt"
cat /sys/firmware/fdt > "$dest/live-fdt-private.dtb"
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -cf /tmp/k119-preflash.tar .
sha256sum /tmp/k119-preflash.tar
echo KERNEL119_PREFLASH_READONLY_CAPTURED
