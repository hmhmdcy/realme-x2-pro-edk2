#!/bin/sh
set -eu
umask 077
uname -v | grep -q '^#128 '
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k128-first-runtime/boot-id-private.txt)"
dest=/var/lib/samurai/k128-final-health
test ! -e "$dest"
mkdir -m700 "$dest"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
dmesg > "$dest/dmesg-before.txt"
for name in display radio; do
 path=/sys/kernel/tracing/instances/$name
 cat "$path/tracing_on" > "$dest/$name-tracing-before.txt"
 echo 0 > "$path/tracing_on"
 timeout -k 2 10 cat "$path/trace" > "$dest/$name-trace-private.txt"
 test "$(cat "$path/tracing_on")" = 0
done
for sample in 0 1 2 3 4 5; do
 test "$(cat /proc/sys/kernel/tainted)" = 0
 test -n "$(pgrep -x phosh)"
 test -n "$(pgrep -x phoc)"
 printf '%s ' "$sample" >> "$dest/samples.txt"
 cat /proc/uptime >> "$dest/samples.txt"
 if test "$sample" != 5; then sleep 10; fi
done
pgrep -x phosh > "$dest/phosh.txt"
pgrep -x phoc > "$dest/phoc.txt"
cat /sys/kernel/debug/dri/1/state > "$dest/drm-state.txt"
cat /sys/kernel/debug/dri/1/clients > "$dest/drm-clients.txt"
cat /sys/class/drm/card1-DSI-1/status > "$dest/connector.txt"
cat /proc/sys/kernel/tainted > "$dest/taint.txt"
cat /sys/class/remoteproc/remoteproc0/state /sys/devices/platform/sensor-power/state > "$dest/sensor.txt"
cat /sys/class/remoteproc/remoteproc1/state /sys/class/remoteproc/remoteproc2/state > "$dest/radio-audio.txt"
cat /proc/asound/cards > "$dest/soundcards.txt"
cat /proc/asound/card0/pcm0p/sub0/status /proc/asound/card0/pcm1c/sub0/status > "$dest/pcm.txt"
cat /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status > "$dest/amps.txt"
test -d /sys/class/bluetooth/hci0
cat /sys/class/bluetooth/hci0/uevent > "$dest/bluetooth.txt"
cat /sys/class/net/wlan0/operstate > "$dest/wlan.txt"
iw dev wlan0 link > "$dest/wlan-link-private.txt"
stat -c "%u:%g:%a" /etc/NetworkManager/system-connections/samurai-wifi.nmconnection > "$dest/wifi-profile-owner.txt"
cat /sys/kernel/debug/pm_genpd/pm_genpd_summary > "$dest/power.txt"
ip -details link show rmnet_ipa0 > "$dest/ipa-private.txt"
cat /proc/swaps > "$dest/swaps.txt"
cat /sys/block/zram0/comp_algorithm /sys/block/zram0/disksize > "$dest/zram.txt"
rc-status default > "$dest/services.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-check.txt"
sha256sum -c /var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256 > "$dest/source-check.txt"
sha256sum -c /var/lib/samurai/k115-vendor-camera-source/vendor-before.sha256 > "$dest/vendor-check.txt"
(cd /usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k128+ && sha256sum -c /var/lib/samurai/k128-preflash/new-module-tree.sha256) > "$dest/modules-check.txt"
sha256sum /dev/sde11 /dev/sde32 /dev/sda2 > "$dest/partitions.sha256"
cat /sys/module/qcom_camss/parameters/dma_trace > "$dest/dma-trace.txt"
dmesg > "$dest/dmesg-after.txt"
sync
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -czf /tmp/k128-final-health-private.tar.gz .
echo K128_FINAL_HEALTH_TRACE_PRESERVED_OFF_SIX_SAMPLES_CAPTURED
