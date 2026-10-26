#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
case "$1" in *[!a-z0-9-]*|'') exit 2;; esac
dir=/var/lib/samurai/k109-$1
test ! -e "$dir"
mkdir -m700 "$dir"
uname -a | grep -q '#109 SMP PREEMPT'
grep -qx kernel109 /etc/samurai-rootfs-stage
grep -q '^/dev/sda16 / f2fs rw' /proc/mounts
mountpoint -q /sys/kernel/debug || mount -t debugfs debugfs /sys/kernel/debug
{
    uname -a
    cat /proc/sys/kernel/random/boot_id /proc/uptime /proc/sys/kernel/tainted
    cat /etc/os-release /etc/samurai-rootfs-release
    readlink /proc/1/exe
    cat /proc/mounts
    df -h /
    rc-status -a
} > "$dir/system.txt"
dmesg > "$dir/dmesg.txt"
test ! -f /var/log/rc.log || cp /var/log/rc.log "$dir/rc.log"
test ! -f /var/lib/samurai/persistence-test.txt || cp /var/lib/samurai/persistence-test.txt "$dir/"
cat /proc/modules > "$dir/modules.txt"
cat /proc/bus/input/devices > "$dir/input.txt"
{
    ls /sys/class/drm /sys/class/graphics
    cat /sys/kernel/debug/dri/1/encoder-0/status
    cat /sys/class/backlight/*/brightness /sys/class/backlight/*/bl_power
} > "$dir/display.txt"
{
    for p in /sys/class/remoteproc/remoteproc*; do cat "$p/name" "$p/state"; done
    ls /sys/class/net
    ip -4 addr
    ip -4 route
    if nmcli -t -f RUNNING general 2>/dev/null | grep -qx running; then
        nmcli -t -f GENERAL.STATE,GENERAL.CONNECTION,IP4.ADDRESS device show wlan0
        iw dev wlan0 link
    else
        /usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status || true
    fi
    cat /run/samurai-wifi/boot-finished || true
} > "$dir/radio.txt"
{
    ls /dev/dri
    for p in /sys/devices/system/cpu/cpufreq/policy*; do cat "$p/related_cpus" "$p/cpuinfo_max_freq"; done
    cat /proc/asound/cards
} > "$dir/hardware.txt"
if [ -e /run/samurai-wifi/nv-source-hashes.txt ]; then
    sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-check.txt"
    cp /run/samurai-wifi-boot.log "$dir/"
fi
sha256sum /dev/sde11 /dev/sde32 /dev/sda2 > "$dir/boot-logdump-persist.sha256"
sync
(cd "$dir" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
tar -C /var/lib/samurai -cf "/tmp/k109-$1.tar" "k109-$1"
sha256sum "/tmp/k109-$1.tar"
echo PMOS_PERSISTENT_ROOTFS_CHECKPOINT_COMPLETE
