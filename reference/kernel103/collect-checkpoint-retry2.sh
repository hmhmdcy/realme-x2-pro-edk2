#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#102 SMP PREEMPT'
dir=/tmp/k103-checkpoint-retry2
test ! -e "$dir"
mkdir -m700 "$dir" "$dir/tests"
for name in k103-audio-runtime-retry1 k103-playback k103-capture k103-capture-dmic0 k103-auto-network k103-core-rebind-once; do
    test -s "/tmp/$name/SHA256SUMS"
    cp -a "/tmp/$name" "$dir/tests/"
done
cp -a /tmp/k103-audio-runtime "$dir/first-runtime-partial"
cp -a /tmp/k103-checkpoint "$dir/first-checkpoint-partial"
{
    uname -a
    cat /proc/sys/kernel/random/boot_id /proc/uptime /proc/sys/kernel/tainted
    for p in /sys/class/remoteproc/remoteproc*; do cat "$p/name" "$p/state"; done
} > "$dir/state.txt"
cat /proc/asound/cards /proc/asound/pcm > "$dir/alsa.txt"
cat /proc/asound/card0/pcm0p/sub0/status /proc/asound/card0/pcm1c/sub0/status > "$dir/pcm-closed.txt"
cat /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status > "$dir/amp-status.txt"
cat "$(/tmp/k103-haptics-device)/status" > "$dir/haptics-status.txt"
ls /sys/class/bluetooth > "$dir/bt-class.txt"
/usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status > "$dir/wifi-status.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-source-check.txt"
sha256sum /dev/sda2 /dev/sde17 > "$dir/persist-stock-dtbo.sha"
sha256sum /dev/sde11 /dev/sde32 /init /usr/sbin/samurai-wifi /usr/sbin/samurai-radio-address /usr/sbin/samurai-modem-remoteproc > "$dir/deployment.sha"
find /lib/modules -type f -name "*.ko" -exec sha256sum '{}' ';' >> "$dir/deployment.sha"
cp /sys/firmware/fdt "$dir/runtime-fdt.bin"
cat /sys/kernel/debug/gpio > "$dir/gpio.txt"
cat /sys/kernel/debug/pinctrl/3100000.pinctrl/pinmux-pins > "$dir/pinmux.txt"
cat /sys/kernel/debug/asoc/components > "$dir/asoc-components.txt"
cat /sys/kernel/debug/devices_deferred > "$dir/deferred.txt"
cat /proc/modules > "$dir/modules.txt"
ps > "$dir/processes.txt"
cp /run/samurai-wifi-boot.log /run/samurai-bluetooth-boot.log /run/samurai-wifi/boot-finished "$dir/"
dmesg > "$dir/dmesg.txt"
echo ALSA_DUAL_MAX98937_FINITE_PCM_AND_5G_CHECKPOINT_CAPTURED > "$dir/result.txt"
(cd "$dir" && find . -type f ! -path ./SHA256SUMS -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
tar -C /tmp -cf /tmp/k103-checkpoint-retry2.tar k103-checkpoint-retry2
sha256sum /tmp/k103-checkpoint-retry2.tar
echo CHECKPOINT_CAPTURE_COMPLETE
