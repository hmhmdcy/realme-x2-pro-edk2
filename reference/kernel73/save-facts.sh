#!/bin/sh
set -eu
out=/tmp/k73-facts.txt
find_partition() {
    wanted="$1"
    found=''
    for node in /sys/class/block/sd*/uevent; do
        if grep -qx "PARTNAME=$wanted" "$node"; then
            test -z "$found"
            found="$(sed -n 's/^DEVNAME=//p' "$node")"
        fi
    done
    test -n "$found"
    echo "/dev/$found"
}
boot_partition="$(find_partition boot)"
logdump_partition="$(find_partition logdump)"
{
    uname -a
    cat /proc/sys/kernel/random/boot_id /proc/sys/kernel/tainted
    cat /proc/mounts
    cat /proc/partitions
    for node in /sys/class/drm/card1-DSI-1/status /sys/class/drm/card1-DSI-1/modes \
        /sys/class/backlight/ae94000.dsi.0/brightness \
        /sys/class/backlight/ae94000.dsi.0/max_brightness \
        /sys/class/input/input2/name /sys/kernel/debug/devices_deferred \
        /sys/devices/system/cpu/cpufreq/policy*/cpuinfo_max_freq \
        /sys/class/hwmon/hwmon*/temp1_input; do
        echo "$node"
        cat "$node"
    done
    /usr/sbin/samurai-usb status
    echo "logdump_partition=$logdump_partition"
    sha256sum "$logdump_partition"
    echo "boot_partition=$boot_partition prefix_bytes=6680576"
    dd if="$boot_partition" bs=2048 count=3262 | sha256sum
    cat "/sys/class/block/${logdump_partition##*/}/uevent" "/sys/class/block/${boot_partition##*/}/uevent"
} > "$out" 2>&1
gzip -c "$out" > "$out.gz"
sha256sum "$out" "$out.gz"
