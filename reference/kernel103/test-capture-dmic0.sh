#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#102 SMP PREEMPT'
grep -q 'Realme-X2Pro-samurai' /proc/asound/cards
dir=/tmp/k103-capture-dmic0
test ! -e "$dir"
mkdir -m700 "$dir"
mix=/tmp/k103-tinymix
cleanup() {
    "$mix" -D 0 set 'MultiMedia2 Mixer SLIMBUS_0_TX' 0 >> "$dir/cleanup.txt" 2>&1 || true
    "$mix" -D 0 set 'AIF1_CAP Mixer SLIM TX5' 0 >> "$dir/cleanup.txt" 2>&1 || true
    "$mix" -D 0 set 'CDC_IF TX5 MUX' ZERO >> "$dir/cleanup.txt" 2>&1 || true
    "$mix" -D 0 set 'DMIC MUX5' ZERO >> "$dir/cleanup.txt" 2>&1 || true
    "$mix" -D 0 set 'ADC MUX5' DMIC >> "$dir/cleanup.txt" 2>&1 || true
    "$mix" -D 0 set 'Handset Mic Switch' 0 >> "$dir/cleanup.txt" 2>&1 || true
}
trap cleanup EXIT INT TERM
"$mix" -D 0 set 'Handset Mic Switch' 1
"$mix" -D 0 set 'DMIC MUX5' DMIC0
"$mix" -D 0 set 'ADC MUX5' DMIC
"$mix" -D 0 set 'CDC_IF TX5 MUX' DEC5
"$mix" -D 0 set 'AIF1_CAP Mixer SLIM TX5' 1
"$mix" -D 0 set 'MultiMedia2 Mixer SLIMBUS_0_TX' 1
cat /proc/uptime > "$dir/start.txt"
timeout -k 5 15 /tmp/k103-tinycap "$dir/mic-private.wav" -D 0 -d 1 -c 1 -r 48000 -b 16 -p 960 -n 4 -t 5 > "$dir/capture.txt" 2> "$dir/capture-error.txt" &
child=$!
sleep 1
cat /proc/asound/card0/pcm1c/sub0/status > "$dir/pcm-live-status.txt"
cat /proc/asound/card0/pcm1c/sub0/hw_params > "$dir/pcm-live-hw-params.txt"
if wait "$child"; then echo 0 > "$dir/capture-exit.txt"; else echo "$?" > "$dir/capture-exit.txt"; fi
cat /proc/uptime > "$dir/end.txt"
cleanup
trap - EXIT INT TERM
cat /proc/asound/card0/pcm1c/sub0/status > "$dir/pcm-after.txt"
cat /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status > "$dir/amp-after.txt"
dmesg > "$dir/dmesg.txt"
(cd "$dir" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
tar -C /tmp -cf /tmp/k103-capture-dmic0.tar k103-capture-dmic0
sha256sum /tmp/k103-capture-dmic0.tar
echo FINITE_CAPTURE_ATTEMPT_CAPTURED
