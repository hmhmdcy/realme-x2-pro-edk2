#!/bin/sh
set -eu
umask 077
before=/var/lib/samurai/k236-baseline
dest=/var/lib/samurai/k236-quiesce
uname -v | grep -q '^#183 '
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat "$before/boot-id-private.txt")"
test "$(cat /proc/sys/kernel/tainted)" = 0
test "$(readlink -f /dev/dri/by-path/platform-ae01000.display-controller-card)" = /dev/dri/card1
test "$(uname -r)" = 7.3.0-rc6-rmx1931-samurai-k132+
test ! -e "$dest"
mkdir -m700 "$dest"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
dmesg > "$dest/dmesg-before.txt"
for name in display radio; do
 path=/sys/kernel/tracing/instances/$name
 echo 0 > "$path/tracing_on"
 timeout -k 2 10 cat "$path/trace" > "$dest/$name-trace-private.txt"
 test "$(cat "$path/tracing_on")" = 0
done

# GPS is inactive before stopping its watcher; preserve its default runlevel link.
python3 /tmp/k236-stop-gnss-idle.py
for service in bluetooth greetd chronyd networkmanager iio-sensor-proxy samurai-ssc nfcd neard; do
 if rc-service "$service" status >/dev/null 2>&1; then timeout -s TERM -k 2 25 rc-service "$service" stop >> "$dest/services.txt" 2>&1; fi
done
for pid in $(pgrep -u 10000 || true); do kill -TERM "$pid" 2>/dev/null || true; done
sleep 2
for pid in $(pgrep -u 10000 || true); do kill -KILL "$pid" 2>/dev/null || true; done
test -z "$(pgrep -u 10000 || true)"
test -z "$(pgrep -x phosh || true)"
test -z "$(pgrep -x phoc || true)"
python3 /tmp/k236-quiesce-camera.py
test ! -d /sys/module/qcom_camss
if rc-service elogind status >/dev/null 2>&1; then timeout -s TERM -k 2 25 rc-service elogind stop >> "$dest/services.txt" 2>&1; fi
cat /sys/kernel/debug/dri/1/clients > "$dest/drm-clients-after-gui.txt"
test "$(wc -l < "$dest/drm-clients-after-gui.txt")" = 1
cat /sys/kernel/debug/dri/1/state > "$dest/drm-before-blank.txt"
cat /proc/asound/cards > "$dest/soundcards-before-stop.txt"
for pcm in /proc/asound/card*/pcm*/sub*/status; do
 test -f "$pcm" || continue
 test "$(cat "$pcm")" = closed
done
cat /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status > "$dest/amps-before-stop.txt"
test "$(grep -c 'powered=0 muted=1' "$dest/amps-before-stop.txt")" = 2
for pid in $(pidof wpa_supplicant || true); do test "$(cat /proc/$pid/comm)" = wpa_supplicant; kill -TERM "$pid"; done
sleep 1
test -z "$(pidof wpa_supplicant || true)"
for pid in $(pidof ModemManager || true); do test "$(sha256sum /proc/$pid/exe | cut -d' ' -f1)" = b350c55ba334b7d23564136fe3ce19bf37f95db0d374f63cc89351341d9b9ddc; kill -TERM "$pid"; done
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
(cd /usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k132+ && sha256sum -c /var/lib/samurai/k235-module-stage/module-tree-after.sha256) > "$dest/new-module-check.txt"
test "$(cat /sys/class/vtconsole/vtcon1/name)" = '(M) frame buffer device'
echo 0 > /sys/class/vtconsole/vtcon1/bind
test "$(cat /sys/class/vtconsole/vtcon1/bind)" = 0
python3 /tmp/k236-disable-crtc.py > "$dest/explicit-crtc-disable.txt" 2>&1
for sample in 1 2 3; do
 sleep 1
 cat /sys/kernel/debug/dri/1/state > "$dest/drm-detached-sample-$sample.txt"
 test "$(grep -c 'active=1' "$dest/drm-detached-sample-$sample.txt" || true)" = 0
done
python3 /tmp/k236-check-quiesce.py --record
cat /proc/uptime /proc/sys/kernel/tainted > "$dest/state.txt"
dmesg > "$dest/dmesg-after.txt"
sha256sum -c /var/lib/samurai/k235-module-stage/loader-config-after.sha256 > /var/lib/samurai/k236-quiesce/loader-config-check.txt
sync
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -cf /tmp/k236-quiesce-private.tar .
echo K202_CURRENT183_QUIESCE_COMPLETE
