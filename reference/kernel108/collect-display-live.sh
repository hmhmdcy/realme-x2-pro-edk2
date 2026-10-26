#!/bin/sh
# Read-only display evidence; preserve the boot-time fault snapshot.
set -eu
out=/tmp/k108-display-live-detail
test ! -e "$out"
mkdir -m 700 "$out"
cat /proc/sys/kernel/random/boot_id > "$out/boot-id-private.txt"
uname -a > "$out/uname.txt"
cat /proc/uptime > "$out/uptime.txt"
dmesg > "$out/dmesg.txt"
for item in /sys/kernel/debug/dri/*/state /sys/kernel/debug/dri/*/encoder-*/status; do
    test -f "$item" || continue
    name=$(echo "$item" | tr / _)
    cat "$item" > "$out/$name"
done
for node in /sys/class/drm/card*-DSI-*; do
    test -d "$node" || continue
    for attr in status enabled modes; do
        test -f "$node/$attr" || continue
        cat "$node/$attr" > "$out/$(basename "$node")-$attr.txt"
    done
done
for node in /sys/class/backlight/*; do
    test -d "$node" || continue
    for attr in brightness actual_brightness max_brightness bl_power type; do
        test -f "$node/$attr" || continue
        cat "$node/$attr" > "$out/$(basename "$node")-$attr.txt"
    done
    readlink -f "$node/device/driver" > "$out/$(basename "$node")-driver.txt" || true
done
find /sys/kernel/debug/dri -maxdepth 3 -type f > "$out/drm-debug-files.txt"
for item in snapshot trace trace_clock buffer_size_kb; do
    path=/sys/kernel/tracing/instances/display/$item
    test -f "$path" || continue
    cat "$path" > "$out/display-$item.txt"
done
for item in /sys/kernel/tracing/instances/display/per_cpu/cpu*/stats; do
    test -f "$item" || continue
    cat "$item" > "$out/$(echo "$item" | tr / _).txt"
done
tar -cf "$out.tar" -C /tmp "$(basename "$out")"
echo DISPLAY_DETAIL_SAVED_NO_STATE_CHANGED
