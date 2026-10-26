#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#99 SMP PREEMPT'
dir=/tmp/k101-audio-preflight
test ! -e "$dir"
mkdir -m700 "$dir" "$dir/vendor-mount" "$dir/modem-mount" "$dir/vendor-config" "$dir/adsp"
resolve()
{
    found=;matches=0
    for attrs in /sys/class/block/sd*/uevent; do
        if grep -qx "PARTNAME=$1" "$attrs"; then
            node=${attrs%/uevent};node=${node##*/}
            test -b "/dev/$node"
            [ "$(cat "/sys/class/block/$node/size")" = "$2" ]
            parent=$(readlink -f "/sys/class/block/$node/..")
            [ "$(cat "$parent/device/model")" = 'KLUDG4UHDB-B2D1 ' ]
            found=/dev/$node;matches=$((matches+1))
        fi
    done
    [ "$matches" = 1 ]
    printf '%s\n' "$found"
}
vendor=$(resolve vendor 3342336)
modem=$(resolve modem 524288)
cleanup() { umount "$dir/vendor-mount" 2>/dev/null || true; umount "$dir/modem-mount" 2>/dev/null || true; }
trap cleanup EXIT
mount -t ext4 -o ro,noload,nosuid,nodev,noexec "$vendor" "$dir/vendor-mount"
mount -t vfat -o ro,nosuid,nodev,noexec "$modem" "$dir/modem-mount"
{
    uname -a
    cat /proc/sys/kernel/random/boot_id /proc/uptime /proc/sys/kernel/tainted
    cat /sys/class/remoteproc/remoteproc0/state
} > "$dir/state.txt"
cat /proc/mounts > "$dir/mounts-during.txt"
cat /sys/firmware/fdt > "$dir/runtime-fdt-private.dtb"
cat /sys/kernel/debug/pinctrl/3100000.pinctrl/pinmux-pins > "$dir/pinmux.txt"
cat /proc/modules > "$dir/modules.txt"
cat /proc/interrupts > "$dir/interrupts.txt"
cat /sys/bus/i2c/devices/1-005a/status > "$dir/haptics-status.txt"
dmesg > "$dir/dmesg.txt"
/usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status > "$dir/wpa-status.txt"
ps > "$dir/processes.txt"
find /sys/class/remoteproc /sys/class/sound /sys/bus/iio/devices -maxdepth 2 -type f -name name -exec sh -c 'printf "%s " "$1"; cat "$1"' sh '{}' ';' > "$dir/devices.txt" 2>/dev/null || true
find "$dir/vendor-mount/etc" -maxdepth 3 -type f \( -iname '*audio*' -o -iname '*mixer*' -o -iname '*maxim*' -o -iname '*tfa*' \) > "$dir/vendor-audio-files.txt"
find "$dir/vendor-mount/firmware" -maxdepth 2 \( -iname '*adsp*' -o -iname '*slpi*' -o -iname '*wcd*' -o -iname '*tfa*' \) > "$dir/vendor-firmware-files.txt"
for file in "$dir/vendor-mount"/etc/mixer_paths*.xml "$dir/vendor-mount"/etc/audio_platform_info*.xml "$dir/vendor-mount"/etc/audio_policy*.xml "$dir/vendor-mount"/build.prop; do
    test -f "$file" || continue
    test ! -L "$file" || continue
    cp "$file" "$dir/vendor-config/"
done
find "$dir/modem-mount/image" -maxdepth 1 -type f -name 'adsp*' > "$dir/modem-adsp-files.txt"
for file in "$dir/modem-mount"/image/adsp.mdt "$dir/modem-mount"/image/adsp.b[0-9][0-9] "$dir/modem-mount"/image/adsp*.jsn; do
    test -f "$file" || continue
    test ! -L "$file"
    cp "$file" "$dir/adsp/"
    cmp "$file" "$dir/adsp/$(basename "$file")"
done
test -f "$dir/adsp/adsp.mdt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-check.txt"
cleanup
trap - EXIT
cat /proc/mounts > "$dir/mounts-after.txt"
echo READ_ONLY_AUDIO_PREFLIGHT_PASS > "$dir/result.txt"
(cd "$dir" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
tar -C /tmp -cf /tmp/k101-audio-preflight.tar k101-audio-preflight
sha256sum /tmp/k101-audio-preflight.tar
