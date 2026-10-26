#!/bin/sh
set -eu
umask 077
prefix=${1:?fresh prefix required}
case "$prefix" in *[!a-z0-9-]*|'') exit 2;; esac
uname -v | grep -q '^#113 '
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k113-reboot-audio-clean-12/boot-id-private.txt)"
test "$(cat /proc/sys/kernel/tainted)" = 0
test "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline
test "$(cat /sys/devices/platform/sensor-power/state)" = 'vdd=0 vddio=0'
test -z "$(pidof hexagonrpcd || true)"
dest=/var/lib/samurai/k113-$prefix
test ! -e "$dest"
mkdir -m700 "$dest"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
dmesg > "$dest/dmesg-before.txt"
for service in greetd chronyd networkmanager iio-sensor-proxy; do
    if rc-service "$service" status >/dev/null 2>&1; then
        rc-service "$service" stop >> "$dest/services.txt" 2>&1
    fi
done
for pid in $(pgrep -u 10000 || true); do kill -TERM "$pid" 2>/dev/null || true; done
sleep 2
for pid in $(pgrep -u 10000 || true); do kill -KILL "$pid" 2>/dev/null || true; done
test -z "$(pgrep -u 10000 || true)"
cat /proc/asound/card0/pcm0p/sub0/status /proc/asound/card0/pcm1c/sub0/status > "$dest/pcm-idle.txt"
test "$(cat "$dest/pcm-idle.txt")" = "$(printf 'closed\nclosed')"
cat /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status > "$dest/amps.txt"
test "$(grep -c 'powered=0 muted=1' "$dest/amps.txt")" = 2
for pid in $(pidof wpa_supplicant || true); do
    test "$(cat /proc/$pid/comm)" = wpa_supplicant
    kill -TERM "$pid"
done
sleep 1
test -z "$(pidof wpa_supplicant || true)"
/usr/sbin/samurai-bluetooth stop > "$dest/bluetooth.txt" 2>&1
echo 18800000.wifi > /sys/bus/platform/drivers/ath10k_snoc/unbind
mpss=$(/usr/sbin/samurai-modem-remoteproc)
timeout -s TERM -k 2 15 sh -c 'echo stop > "$1/state"' sh "$mpss" > "$dest/mpss-stop.txt" 2>&1
test "$(cat "$mpss/state")" = offline
adsp=/sys/class/remoteproc/remoteproc2
test "$(cat "$adsp/name")" = adsp
test "$(cat "$adsp/state")" = running
timeout -s TERM -k 2 15 sh -c 'echo stop > "$1/state"' sh "$adsp" > "$dest/adsp-stop.txt" 2>&1
test "$(cat "$adsp/state")" = offline
cat "$adsp/state" > "$dest/adsp-final-state.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-check.txt"
sha256sum -c /var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256 > "$dest/source-check.txt"
cat /proc/uptime /proc/sys/kernel/tainted > "$dest/state.txt"
dmesg > "$dest/dmesg-after.txt"
sync
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -cf "/tmp/k113-$prefix.tar" .
sha256sum "/tmp/k113-$prefix.tar"
echo AUDIO_AND_RADIO_QUIESCED_READY_FOR_NORMAL_OPENRC_REBOOT
