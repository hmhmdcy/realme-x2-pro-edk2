#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#103 SMP PREEMPT'
dir=/tmp/k104-checkpoint
test ! -e "$dir"
mkdir -m700 "$dir" "$dir/tests"
for name in audio-runtime playback auto-network capture-dmic0 capture-dmic1 capture-dmic2 first-boot-failure radio-recovery-first core-rebind-once; do
    test -f "/tmp/k104-$name/SHA256SUMS"
    cp -a "/tmp/k104-$name" "$dir/tests/"
done
{
    uname -a
    cat /proc/sys/kernel/random/boot_id /proc/uptime /proc/sys/kernel/tainted
    for r in /sys/class/remoteproc/remoteproc*; do cat "$r/name" "$r/state"; done
} > "$dir/state.txt"
cat /proc/asound/cards /proc/asound/pcm > "$dir/alsa.txt"
cat /proc/asound/card0/pcm0p/sub0/status /proc/asound/card0/pcm1c/sub0/status > "$dir/pcm-closed.txt"
cat /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status > "$dir/amp-status.txt"
cat "$(/tmp/k104-haptics-device)/status" > "$dir/haptics-status.txt"
ls /sys/class/bluetooth > "$dir/bt-class.txt"
/usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status > "$dir/wifi-status.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-source-check.txt"
sha256sum /dev/sda2 /dev/sde17 > "$dir/persist-stock-dtbo.sha"
sha256sum /dev/sde11 /dev/sde32 /init /usr/sbin/samurai-wifi /usr/sbin/samurai-bluetooth /usr/sbin/samurai-modem-remoteproc /usr/sbin/samurai-radio-address > "$dir/deployment.sha"
find /lib/modules -type f -name '*.ko' -exec sha256sum '{}' ';' >> "$dir/deployment.sha"
cp /sys/firmware/fdt "$dir/runtime-fdt.bin"
cat /proc/modules > "$dir/modules.txt"
ps > "$dir/processes.txt"
dmesg > "$dir/dmesg.txt"
(cd "$dir" && find . -type f ! -path ./SHA256SUMS -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
tar -C /tmp -cf /tmp/k104-checkpoint.tar k104-checkpoint
sha256sum /tmp/k104-checkpoint.tar
echo CHECKPOINT_CAPTURED_WITH_ALL_NESTED_MANIFESTS
