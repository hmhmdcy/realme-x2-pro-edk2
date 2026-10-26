#!/bin/sh
set -eu
umask 077
[ "$#" = 2 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#106 SMP PREEMPT'
case "$2" in ''|*[!0-9]*) exit 1;; esac
[ "$2" -gt 1000000 ] && [ "$2" -lt 100663296 ]
dir=/tmp/k108-audio-runtime
test ! -e "$dir"
mkdir -m700 "$dir"
mountpoint -q /sys/kernel/debug || mount -t debugfs debugfs /sys/kernel/debug
{
    uname -a
    cat /proc/sys/kernel/random/boot_id /proc/uptime /proc/sys/kernel/tainted
    for p in /sys/class/remoteproc/remoteproc*; do
        echo "$p"
        cat "$p/name" "$p/state" "$p/firmware" "$p/recovery"
        readlink -f "$p/device/of_node"
        if [ "$(cat "$p/name")" = adsp ]; then echo disabled > "$p/recovery"; fi
    done
} > "$dir/state.txt"
cat /proc/asound/cards /proc/asound/pcm /proc/asound/devices > "$dir/alsa.txt"
ls -l /dev/snd > "$dir/snd-devices.txt"
for p in /sys/bus/i2c/devices/*-0039 /sys/bus/i2c/devices/*-003a; do
    echo "$p"
    cat "$p/name"
    readlink -f "$p/driver" || true
    if test -r "$p/status"; then cat "$p/status"; fi
done > "$dir/amplifiers.txt"
cat /sys/kernel/debug/pinctrl/3100000.pinctrl/pinmux-pins > "$dir/pinmux.txt"
cat /sys/kernel/debug/gpio > "$dir/gpio.txt"
cat /sys/kernel/debug/devices_deferred > "$dir/deferred.txt"
find /sys/bus/aprbus/devices /sys/bus/slimbus/devices /sys/bus/platform/drivers/wcd934x-codec /sys/bus/i2c/drivers/max98937-samurai -maxdepth 2 -type l -exec ls -l '{}' ';' > "$dir/audio-bus.txt"
for f in /sys/bus/aprbus/devices/*/samurai_api; do
    if test -r "$f"; then
        if cat "$f" > "$dir/native-api.txt" 2> "$dir/native-api-error.txt"; then
            echo 0 > "$dir/native-api-exit.txt"
        else
            echo 1 > "$dir/native-api-exit.txt"
        fi
    fi
done
cat "$(/tmp/k108-haptics-device)/status" > "$dir/haptics-status.txt"
cp /run/samurai-wifi-boot.log /run/samurai-bluetooth-boot.log "$dir/"
test ! -e /run/samurai-wifi/boot-finished || cp /run/samurai-wifi/boot-finished "$dir/"
test ! -e /run/samurai-wifi/nv-source-hashes.txt || {
    cp /run/samurai-wifi/nv-source-hashes.txt "$dir/"
    sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-source-check.txt"
}
sha256sum /dev/sda2 /dev/sde17 > "$dir/persist-stock-dtbo.sha"
dd if=/dev/sde11 of=/tmp/k108-boot-readback.img bs=1048576
dd if=/dev/sde32 of=/tmp/k108-logdump-readback.img bs=1048576
sha256sum /tmp/k108-boot-readback.img /tmp/k108-logdump-readback.img > "$dir/partitions.sha"
head -c "$2" /dev/sde11 | sha256sum > "$dir/boot-prefix.sha"
sha256sum /init /usr/sbin/samurai-wifi /usr/sbin/samurai-radio-address /usr/sbin/samurai-modem-remoteproc > "$dir/deployment.sha"
cp /sys/firmware/fdt "$dir/runtime-fdt.bin"
cat /proc/modules > "$dir/modules.txt"
ps > "$dir/processes.txt"
cat /proc/interrupts > "$dir/interrupts.txt"
find /sys/kernel/debug/asoc -maxdepth 3 -type f > "$dir/asoc-debug-files.txt"
dmesg > "$dir/dmesg.txt"
(cd "$dir" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
tar -C /tmp -cf /tmp/k108-audio-runtime.tar k108-audio-runtime
sha256sum /tmp/k108-audio-runtime.tar
echo AUDIO_RUNTIME_CAPTURE_COMPLETE
