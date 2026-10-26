#!/bin/sh
set -eu
umask 077
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k129-first-runtime/boot-id-private.txt)"
test -f /var/lib/samurai/k130-bluez-discovery-r2/result.json
test -z "$(pgrep -x bluetoothd)"
dest=/var/lib/samurai/k130-discovery-checkpoint
test ! -e "$dest"
mkdir -m700 "$dest"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
cp -a /var/lib/samurai/k130-mgmt-before /var/lib/samurai/k130-address-provision /var/lib/samurai/k130-bluez-discovery /var/lib/samurai/k130-bluez-discovery-r2 "$dest/"
dmesg > "$dest/dmesg-final.txt"
cat /proc/sys/kernel/tainted > "$dest/taint.txt"
pgrep -x phosh > "$dest/phosh.txt"
pgrep -x phoc > "$dest/phoc.txt"
iw dev wlan0 link > "$dest/wifi-link-private.txt"
cp -a /etc/NetworkManager/system-connections/samurai-wifi.nmconnection "$dest/wifi-profile-private.nmconnection"
cat /sys/class/remoteproc/remoteproc0/state /sys/devices/platform/sensor-power/state > "$dest/sensor.txt"
cat /sys/class/remoteproc/remoteproc1/state /sys/class/remoteproc/remoteproc2/state > "$dest/radio-audio.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-check.txt"
sha256sum -c /var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256 > "$dest/source-check.txt"
sha256sum -c /var/lib/samurai/k115-vendor-camera-source/vendor-before.sha256 > "$dest/vendor-check.txt"
sha256sum /dev/sde11 /dev/sde32 /dev/sda2 > "$dest/partitions.sha256"
cat /sys/kernel/debug/dri/1/state > "$dest/drm-state.txt"
cat /proc/asound/card0/pcm0p/sub0/status /proc/asound/card0/pcm1c/sub0/status > "$dest/pcm.txt"
cat /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status > "$dest/amps.txt"
cp -a /var/lib/bluetooth "$dest/bluetooth-storage-private"
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -czf /tmp/k130-discovery-checkpoint-private.tar.gz .
sha256sum /tmp/k130-discovery-checkpoint-private.tar.gz > /tmp/k130-discovery-checkpoint-private.tar.gz.sha256
echo K130_DISCOVERY_CHECKPOINT_ARCHIVED
