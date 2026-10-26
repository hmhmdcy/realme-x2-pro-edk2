#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#102 SMP PREEMPT'
grep -q 'Realme-X2Pro-samurai' /proc/asound/cards
dir=/tmp/k103-playback
test ! -e "$dir"
mkdir -m700 "$dir"
mix=/tmp/k103-tinymix
cleanup() {
    "$mix" -D 0 set 'QUAT_MI2S_RX Audio Mixer MultiMedia1' 0 >> "$dir/cleanup.txt" 2>&1 || true
    "$mix" -D 0 set 'Left Speaker Switch' 0 >> "$dir/cleanup.txt" 2>&1 || true
    "$mix" -D 0 set 'Right Speaker Switch' 0 >> "$dir/cleanup.txt" 2>&1 || true
}
trap cleanup EXIT INT TERM
cat /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status > "$dir/amp-before.txt"
"$mix" -D 0 set 'Left Speaker Switch' 1
"$mix" -D 0 set 'Right Speaker Switch' 1
"$mix" -D 0 set 'QUAT_MI2S_RX Audio Mixer MultiMedia1' 1
"$mix" -D 0 get 'QUAT_MI2S_RX Audio Mixer MultiMedia1' > "$dir/route-enabled.txt"
cat /proc/uptime > "$dir/start.txt"
# Explicit DSP period alignment: 960 stereo frames, four periods.
if timeout -k 5 20 /tmp/k103-tinyplay /tmp/k103-tone-low-private.wav -D 0 -d 0 -p 960 -n 4 > "$dir/play.txt" 2> "$dir/play-error.txt"; then
    echo 0 > "$dir/play-exit.txt"
else
    echo "$?" > "$dir/play-exit.txt"
fi
cat /proc/uptime > "$dir/end.txt"
cleanup
trap - EXIT INT TERM
cat /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status > "$dir/amp-after.txt"
cat /proc/asound/card0/pcm0p/sub0/status > "$dir/pcm-after.txt"
dmesg > "$dir/dmesg.txt"
(cd "$dir" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
tar -C /tmp -cf /tmp/k103-playback.tar k103-playback
sha256sum /tmp/k103-playback.tar
echo FINITE_PLAYBACK_ATTEMPT_CAPTURED
