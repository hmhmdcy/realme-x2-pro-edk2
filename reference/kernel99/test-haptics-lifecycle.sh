#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#98 SMP PREEMPT'
dir=/tmp/k99-haptics-lifecycle
test ! -e "$dir"
mkdir -m700 "$dir"
device=/sys/bus/i2c/devices/1-005a
[ "$(readlink -f "$device/driver")" = /sys/bus/i2c/drivers/aw8697-samurai ]
events=''
for file in /sys/class/input/event*/device/name; do
    grep -qx 'Realme X2 Pro AW8697 haptics' "$file" || continue
    events="$events /dev/input/$(basename "$(dirname "$(dirname "$file")")")"
done
[ "$(printf '%s' "$events" | wc -w)" = 1 ]
event=$(printf '%s' "$events" | awk '{print $1}')
dmesg > "$dir/dmesg-before.txt"
cat "$device/status" > "$dir/status-before.txt"
grep -q '^id=97 go=00 state=00 .*active=0 .*error=0$' "$dir/status-before.txt"
for mode in close kill watchdog; do
    /tmp/k99-ff-lifecycle "$event" "$mode" > "$dir/$mode.log" 2>&1 &
    pid=$!
    trap 'kill -TERM "$pid" 2>/dev/null || true; wait "$pid" 2>/dev/null || true' EXIT
    active_seen=0
    for attempt in $(seq 1 250); do
        printf 'uptime=%s ' "$(cut -d ' ' -f1 /proc/uptime)" >> "$dir/$mode-samples.txt"
        cat "$device/status" >> "$dir/$mode-samples.txt"
        if grep -q 'go=01 state=06 .*active=1' "$dir/$mode-samples.txt"; then active_seen=1; fi
        if [ "$mode" = kill ] && [ "$active_seen" = 1 ]; then
            kill -KILL "$pid"
            break
        fi
        kill -0 "$pid" 2>/dev/null || break
        sleep 0.01
    done
    if [ "$mode" = kill ]; then
        result=0
        wait "$pid" || result=$?
        [ "$result" = 137 ]
    else
        wait "$pid"
    fi
    trap - EXIT
    [ "$active_seen" = 1 ]
    grep -qx FF_LIFECYCLE_STARTED "$dir/$mode.log"
    for attempt in $(seq 1 20); do
        cat "$device/status" > "$dir/$mode-after.txt"
        if grep -q '^id=97 go=00 state=00 .*active=0 .*error=0$' "$dir/$mode-after.txt"; then break; fi
        sleep 0.01
    done
    grep -q '^id=97 go=00 state=00 .*active=0 .*error=0$' "$dir/$mode-after.txt"
    sleep 1
done
grep -qx WATCHDOG_FD_STILL_OPEN_AFTER_1800MS "$dir/watchdog.log"
grep -q 'active=0 .*watchdog_stops=1 error=0$' "$dir/watchdog-after.txt"
dmesg > "$dir/dmesg-after.txt"
cat /proc/sys/kernel/tainted /proc/uptime > "$dir/state.txt"
[ "$(cat /proc/sys/kernel/tainted)" = 0 ]
echo HAPTICS_CLOSE_KILL_WATCHDOG_PASS > "$dir/result.txt"
(cd "$dir" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
tar -C /tmp -cf /tmp/k99-haptics-lifecycle.tar k99-haptics-lifecycle
sha256sum /tmp/k99-haptics-lifecycle.tar
