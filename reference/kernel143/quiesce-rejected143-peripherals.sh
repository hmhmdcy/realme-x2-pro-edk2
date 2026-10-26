#!/bin/sh
set -eu
umask 077
before=/var/lib/samurai/k143-first-runtime
dest=/var/lib/samurai/k143-rollback-quiesce
uname -v | grep -q '^#143 '
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat "$dest/boot-id-private.txt")"
test ! -e /tmp/k143-rollback-quiesce-private.tar
test ! -e "$dest/SHA256SUMS"
cat /proc/asound/card0/pcm0p/sub0/status /proc/asound/card0/pcm1c/sub0/status > "$dest/pcm-idle.txt"
test "$(cat "$dest/pcm-idle.txt")" = "$(printf 'closed\nclosed')"
cat /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status > "$dest/amps-before-stop.txt"
test "$(grep -c 'powered=0 muted=1' "$dest/amps-before-stop.txt")" = 2
for pid in $(pidof wpa_supplicant || true); do test "$(cat /proc/$pid/comm)" = wpa_supplicant; kill -TERM "$pid"; done
sleep 1
test -z "$(pidof wpa_supplicant || true)"
for pid in $(pidof ModemManager || true); do test "$(readlink -f /proc/$pid/exe)" = "$(readlink -f /usr/sbin/ModemManager)"; kill -TERM "$pid"; done
sleep 1
test -z "$(pidof ModemManager || true)"
/usr/sbin/samurai-bluetooth stop > "$dest/bluetooth-stop.txt" 2>&1
test -e /sys/bus/platform/devices/18800000.wifi
if test -L /sys/bus/platform/devices/18800000.wifi/driver; then
 test "$(readlink -f /sys/bus/platform/devices/18800000.wifi/driver)" = /sys/bus/platform/drivers/ath10k_snoc
 echo 18800000.wifi > /sys/bus/platform/drivers/ath10k_snoc/unbind
fi
test ! -e /sys/bus/platform/devices/18800000.wifi/driver
test ! -e /sys/class/net/wlan0
echo WIFI_PLATFORM_DRIVER_DETACHED_AND_WLAN_ABSENT > "$dest/wifi-final-state.txt"
mpss=$(/usr/sbin/samurai-modem-remoteproc)
test "$(cat "$mpss/name")" = modem
if test "$(cat "$mpss/state")" = running; then timeout -s TERM -k 2 20 sh -c 'echo stop > "$1/state"' sh "$mpss" > "$dest/mpss-stop.txt" 2>&1; fi
test "$(cat "$mpss/state")" = offline
adsp=/sys/class/remoteproc/remoteproc2
test "$(cat "$adsp/name")" = adsp
if test "$(cat "$adsp/state")" = running; then timeout -s TERM -k 2 25 sh -c 'echo stop > "$1/state"' sh "$adsp" > "$dest/adsp-stop.txt" 2>&1; fi
test "$(cat "$adsp/state")" = offline
test ! -e /proc/asound/card0
cat /proc/asound/cards > "$dest/soundcards-after-stop.txt"
for number in 0 1 2; do item=/sys/class/remoteproc/remoteproc$number;test "$(cat "$item/state")" = offline;printf '%s %s %s\n' "$number" "$(cat "$item/name")" "$(cat "$item/state")";done > "$dest/remoteproc-final-state.txt"
cat /sys/devices/platform/sensor-power/state > "$dest/sensor-power-final-state.txt"
test "$(cat "$dest/sensor-power-final-state.txt")" = 'vdd=0 vddio=0'
cat /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status > "$dest/amps-final.txt"
test "$(grep -c 'powered=0 muted=1' "$dest/amps-final.txt")" = 2
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-check.txt"
sha256sum -c /var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256 > "$dest/source-check.txt"
sha256sum -c /var/lib/samurai/k115-vendor-camera-source/vendor-before.sha256 > "$dest/vendor-check.txt"
sha256sum -c "$before/partition-check.sha256" > "$dest/partition-check.txt"
(cd /usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k132+ && sha256sum -c /var/lib/samurai/k132-preflash/new-module-tree.sha256) > "$dest/new-module-check.txt"
python3 /tmp/k143-check-rollback-warning.py --record
cat /proc/uptime /proc/sys/kernel/tainted > "$dest/state.txt"
sync
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -cf /tmp/k143-rollback-quiesce-private.tar .
echo K143_REJECTED143_PERIPHERALS_QUIESCED_AND_SEALED
