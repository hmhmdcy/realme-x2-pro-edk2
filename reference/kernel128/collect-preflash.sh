#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k128-preflash
test ! -e "$dest"
test "$(uname -r)" = 7.3.0-rc6-rmx1931-samurai-k126+
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k126-embedded-runtime/boot-id-private.txt)"
test "$(cat /proc/sys/kernel/tainted)" = 0
test -n "$(pgrep -x phosh)" && test -n "$(pgrep -x phoc)"
test "$(readlink -f /dev/dri/by-path/platform-ae01000.display-controller-card)" = /dev/dri/card1
test -c /dev/dri/renderD128
grep -q '^/dev/sda16 / f2fs rw' /proc/mounts
test "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline
test "$(cat /sys/devices/platform/sensor-power/state)" = 'vdd=0 vddio=0'
test "$(cat /sys/module/qcom_camss/parameters/dma_trace)" = N
test -z "$(pidof hexagonrpcd || true)"
test ! -e /sys/kernel/tracing/instances/k128-keytrace-baseline-r3
mkdir -m700 "$dest"
for dev in sda sdb sdc sdd sde sdf; do
 sectors=$(blockdev --getsz "/dev/$dev")
 test "$(blockdev --getss "/dev/$dev")" = 4096
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
sha256sum -c /var/lib/samurai/k115-vendor-camera-source/vendor-before.sha256 > "$dest/vendor-check.txt"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
cp /var/lib/samurai/k126-preflash/new-module-tree.sha256 "$dest/old126-module-tree.sha256"
(cd /usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k126+ && sha256sum -c "$dest/old126-module-tree.sha256") > "$dest/old126-module-check.txt"
sha256sum /usr/lib/modules/7.3.0-rc6-rmx1931-samurai+/kernel/drivers/net/ipa/ipa.ko > "$dest/old118-ipa.sha256"
sha256sum /usr/bin/samurai-bluetooth > "$dest/bluetooth-script.sha256"
pgrep -x phosh > "$dest/phosh.txt"
pgrep -x phoc > "$dest/phoc.txt"
cat /sys/class/drm/card1-DSI-1/status > "$dest/connector.txt"
cat /sys/class/remoteproc/remoteproc0/state /sys/devices/platform/sensor-power/state > "$dest/sensors.txt"
for name in display radio; do cat "/sys/kernel/tracing/instances/$name/tracing_on"; done > "$dest/traces.txt"
cat /proc/asound/card0/pcm0p/sub0/status /proc/asound/card0/pcm1c/sub0/status > "$dest/pcm.txt"
cat /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status > "$dest/amps.txt"
cat /proc/uptime /proc/sys/kernel/tainted > "$dest/state.txt"
dmesg > "$dest/dmesg.txt"
cat /proc/mounts > "$dest/mounts.txt"
uname -a > "$dest/uname.txt"
cat /sys/firmware/fdt > "$dest/live-fdt-private.dtb"
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -czf /tmp/k128-preflash-private.tar.gz .
echo K128_FRESH126_PREFLASH_PRIVATE_CAPTURED
