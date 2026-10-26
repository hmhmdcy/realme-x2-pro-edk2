#!/bin/sh
set -eu
umask 077
uname -v | grep -q '^#113 '
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k113-reboot-audio-clean-15/boot-id-private.txt)"
dest=/var/lib/samurai/k113-display-regression-boot15
test ! -e "$dest"
mkdir -m700 "$dest"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
date -u > "$dest/time.txt"
cat /proc/uptime /proc/sys/kernel/tainted > "$dest/state-before.txt"
dmesg > "$dest/dmesg-before.txt"
cat /sys/class/remoteproc/remoteproc0/state > "$dest/slpi-before.txt"
cat /sys/devices/platform/sensor-power/state > "$dest/power-before.txt"
ps -eo pid,user,args > "$dest/processes-before-private.txt"
count=0
for dump_node in /sys/class/devcoredump/devcd*; do
    test -e "$dump_node" || continue
    if [ "$(readlink -f "$dump_node/failing_device")" = /sys/devices/platform/soc@0/ae00000.display-subsystem/ae01000.display-controller ]; then
        count=$((count+1))
        set +e
        timeout -s TERM -k 2 25 dd if="$dump_node/data" of="$dest/display-$count-private.bin" bs=1M count=64 > "$dest/read-$count.txt" 2>&1
        printf '%s\n' "$?" > "$dest/read-$count-exit.txt"
        set -e
    fi
done
printf '%s\n' "$count" > "$dest/dumps-found.txt"
for item in /sys/kernel/debug/dri/*; do
    test -f "$item/state" || continue
    name=$(basename "$item")
    cat "$item/state" > "$dest/drm-$name-state-private.txt"
done
for item in /sys/class/drm/card*-DSI-*; do
    test -e "$item" || continue
    name=$(basename "$item")
    for field in status enabled modes; do
        test -f "$item/$field" || continue
        cat "$item/$field" > "$dest/$name-$field.txt"
    done
done
cat /sys/kernel/debug/clk/clk_summary > "$dest/clocks-private.txt"
cat /sys/kernel/debug/regulator/regulator_summary > "$dest/regulators-private.txt"
cat /proc/uptime /proc/sys/kernel/tainted > "$dest/state-after.txt"
dmesg > "$dest/dmesg-after.txt"
cat /sys/class/remoteproc/remoteproc0/state > "$dest/slpi-after.txt"
cat /sys/devices/platform/sensor-power/state > "$dest/power-after.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-check.txt"
sha256sum -c /var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256 > "$dest/source-check.txt"
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -cf /tmp/k113-display-regression-boot15.tar .
sha256sum /tmp/k113-display-regression-boot15.tar
echo DISPLAY_REGRESSION_BOOT15_SNAPSHOT_SAVED_EXISTING_DUMP_NOT_RELEASED
