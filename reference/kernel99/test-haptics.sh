#!/bin/sh
set -eu
umask 077
[ "$#" = 2 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#98 SMP PREEMPT'
case "$2" in initial-retry1) phase=$2;; *) exit 2;; esac
dir=/tmp/k99-haptics-$phase
test ! -e "$dir"
mkdir -m700 "$dir"
devices=''
for d in /sys/bus/i2c/devices/*-005a; do
    test -f "$d/status" || continue
    [ "$(readlink -f "$d/driver")" = /sys/bus/i2c/drivers/aw8697-samurai ] || continue
    devices="$devices $d"
done
[ "$(printf '%s' "$devices" | wc -w)" = 1 ]
device=$(printf '%s' "$devices" | awk '{print $1}')
events=''
for file in /sys/class/input/event*/device/name; do
    grep -qx 'Realme X2 Pro AW8697 haptics' "$file" || continue
    events="$events /dev/input/$(basename "$(dirname "$(dirname "$file")")")"
done
[ "$(printf '%s' "$events" | wc -w)" = 1 ]
event=$(printf '%s' "$events" | awk '{print $1}')
printf '%s\n' "$device" "$event" > "$dir/device-paths.txt"
cat "$device/status" > "$dir/status-before.txt"
grep -q '^id=97 go=00 state=00 .*active=0 .*starts=0 .*error=0$' "$dir/status-before.txt"
dmesg > "$dir/dmesg-before.txt"
cat /proc/bus/input/devices > "$dir/input-devices.txt"
cat /sys/kernel/debug/pinctrl/3100000.pinctrl/pinmux-pins > "$dir/pinmux.txt"
readlink -f "$device/of_node" > "$dir/of-node.txt"
for n in 1 2 3; do
    /tmp/k99-ff-pulse "$event" 20 150 > "$dir/pulse$n.log" 2>&1 &
    pid=$!
    trap 'kill -TERM "$pid" 2>/dev/null || true; wait "$pid" 2>/dev/null || true' EXIT
    while kill -0 "$pid" 2>/dev/null; do
        printf 'uptime=%s ' "$(cut -d ' ' -f1 /proc/uptime)" >> "$dir/pulse$n-samples.txt"
        cat "$device/status" >> "$dir/pulse$n-samples.txt"
        sleep 0.01
    done
    wait "$pid"
    trap - EXIT
    for marker in FF_UPLOAD_PASS FF_START_PASS FF_STOP_PASS FF_ERASE_PASS; do grep -qx "$marker" "$dir/pulse$n.log"; done
    cat "$device/status" > "$dir/status-after$n.txt"
    grep -q '^id=97 go=00 state=00 .*active=0 .*error=0$' "$dir/status-after$n.txt"
    grep -q 'go=01 state=06 .*active=1 ' "$dir/pulse$n-samples.txt"
    sleep 1
done
{
    uname -a
    cat /proc/sys/kernel/random/boot_id /proc/uptime /proc/sys/kernel/tainted
    cat /sys/class/remoteproc/remoteproc0/state
    cat /sys/kernel/debug/dri/1/encoder-0/status
} > "$dir/state.txt"
[ "$(cat /proc/sys/kernel/tainted)" = 0 ]
dmesg > "$dir/dmesg-after.txt"
echo HAPTICS_FF_AND_ELECTRICAL_PASS > "$dir/result.txt"
(cd "$dir" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
tar -C /tmp -cf "/tmp/k99-haptics-$phase.tar" "k99-haptics-$phase"
sha256sum "/tmp/k99-haptics-$phase.tar"
