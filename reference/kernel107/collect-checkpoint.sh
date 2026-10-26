#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#106 SMP PREEMPT'
dir=/tmp/k107-checkpoint
test ! -e "$dir"
mkdir -m700 "$dir"
for name in audio-runtime first-radio-trace playback capture-dmic0 auto-network 24g-once final-network; do
    test ! -f "/tmp/k107-$name.tar" || cp "/tmp/k107-$name.tar" "$dir/$name.tar"
done
{
    uname -a
    cat /proc/sys/kernel/random/boot_id /proc/uptime /proc/sys/kernel/tainted
    for p in /sys/class/remoteproc/remoteproc*; do cat "$p/name" "$p/state"; done
} > "$dir/state.txt"
ps > "$dir/processes.txt"
cat /proc/modules > "$dir/modules.txt"
cat /proc/interrupts > "$dir/interrupts.txt"
cat /proc/mounts > "$dir/mounts.txt"
dmesg > "$dir/dmesg.txt"
qrtr-lookup > "$dir/qrtr.txt"
cp /run/samurai-wifi/boot-finished /run/samurai-wifi-boot.log /run/samurai-bluetooth-boot.log "$dir/"
for name in tftp.log rmtfs.log wpa.log; do cp "/run/samurai-wifi/$name" "$dir/$name"; done
/usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status > "$dir/wpa-status.txt"
ls /sys/class/bluetooth > "$dir/bt-class.txt"
cat "$(/tmp/k107-haptics-device)/status" > "$dir/haptics-status.txt"
cat /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status > "$dir/amp-status.txt"
cat /proc/asound/card0/pcm0p/sub0/status /proc/asound/card0/pcm1c/sub0/status > "$dir/pcm-status.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-check.txt"
sha256sum /dev/sda2 /dev/sde17 /dev/sde11 /dev/sde32 > "$dir/partitions.sha"
sha256sum /init /usr/sbin/samurai-wifi /usr/sbin/samurai-radio-address /usr/sbin/samurai-modem-remoteproc > "$dir/services.sha"
cp /sys/firmware/fdt "$dir/runtime-fdt.bin"
(cd "$dir" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
tar -C /tmp -cf /tmp/k107-checkpoint.tar k107-checkpoint
sha256sum /tmp/k107-checkpoint.tar
echo CHECKPOINT_COMPLETE
