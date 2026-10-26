#!/bin/sh
set -eu
umask 077
[ "$#" = 2 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#104 SMP PREEMPT'
grep -q 'Realme-X2Pro-samurai' /proc/asound/cards
case "$2" in
    0) dmic=0;dec=5;tx=5;widget='Handset Mic';;
    1) dmic=1;dec=7;tx=7;widget='Secondary Mic';;
    2) dmic=2;dec=5;tx=5;widget='Speaker Mic';;
    *) exit 1;;
esac
dir=/tmp/k105-capture-dmic$dmic
test ! -e "$dir"
mkdir -m700 "$dir"
mix=/tmp/k105-tinymix
codec='/sys/kernel/debug/asoc/Realme X2 Pro/wcd934x-codec.0.auto/dapm'
test -d "$codec"
snapshot_dapm() {
    for p in "$codec"/*; do
        test -f "$p" || continue
        printf '%s\n' "${p##*/}"
        cat "$p"
    done
}
cleanup() {
    "$mix" -D 0 set 'MultiMedia2 Mixer SLIMBUS_0_TX' 0 >> "$dir/cleanup.txt" 2>&1 || true
    "$mix" -D 0 set "AIF1_CAP Mixer SLIM TX$tx" 0 >> "$dir/cleanup.txt" 2>&1 || true
    "$mix" -D 0 set "CDC_IF TX$tx MUX" ZERO >> "$dir/cleanup.txt" 2>&1 || true
    "$mix" -D 0 set "DMIC MUX$dec" ZERO >> "$dir/cleanup.txt" 2>&1 || true
    "$mix" -D 0 set "$widget Switch" 0 >> "$dir/cleanup.txt" 2>&1 || true
}
trap cleanup EXIT INT TERM
printf 'DMIC=%s DEC=%s TX=%s WIDGET=%s\n' "$dmic" "$dec" "$tx" "$widget" > "$dir/route.txt"
snapshot_dapm > "$dir/dapm-before.txt"
"$mix" -D 0 set "$widget Switch" 1
"$mix" -D 0 set "DMIC MUX$dec" "DMIC$dmic"
"$mix" -D 0 set "ADC MUX$dec" DMIC
"$mix" -D 0 set "CDC_IF TX$tx MUX" "DEC$dec"
"$mix" -D 0 set "AIF1_CAP Mixer SLIM TX$tx" 1
"$mix" -D 0 set 'MultiMedia2 Mixer SLIMBUS_0_TX' 1
"$mix" -D 0 contents > "$dir/mixer-active.txt"
cat /proc/uptime > "$dir/start.txt"
timeout -k 5 15 /tmp/k105-tinycap "$dir/mic-private.wav" -D 0 -d 1 -c 1 -r 48000 -b 16 -p 960 -n 4 -t 5 > "$dir/capture.txt" 2> "$dir/capture-error.txt" &
child=$!
sleep 1
cat /proc/asound/card0/pcm1c/sub0/status > "$dir/pcm-live-status.txt"
cat /proc/asound/card0/pcm1c/sub0/hw_params > "$dir/pcm-live-hw-params.txt"
snapshot_dapm > "$dir/dapm-live.txt"
if wait "$child"; then echo 0 > "$dir/capture-exit.txt"; else echo "$?" > "$dir/capture-exit.txt"; fi
cat /proc/uptime > "$dir/end.txt"
cleanup
trap - EXIT INT TERM
snapshot_dapm > "$dir/dapm-after.txt"
cat /proc/asound/card0/pcm1c/sub0/status > "$dir/pcm-after.txt"
cat /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status > "$dir/amp-after.txt"
cat /proc/sys/kernel/tainted > "$dir/tainted.txt"
dmesg > "$dir/dmesg.txt"
(cd "$dir" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
tar -C /tmp -cf /tmp/k105-capture-dmic$dmic.tar k105-capture-dmic$dmic
sha256sum /tmp/k105-capture-dmic$dmic.tar
echo FINITE_CAPTURE_WITH_DAPM_STATE_CAPTURED
