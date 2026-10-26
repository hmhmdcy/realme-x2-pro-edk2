#!/bin/sh
set -eu
umask 077
test "$#" = 1
test "$(cat /proc/sys/kernel/random/boot_id)" = "$1"
uname -v | grep -q '^#106 '
out=/tmp/k108-checkpoint
test ! -e "$out"
mkdir -m 700 "$out"
for name in first-radio-trace auto-network final-network; do
    test -s "/tmp/k108-$name.tar"
    cp "/tmp/k108-$name.tar" "$out/$name.tar"
done
{
    uname -a
    cat /proc/sys/kernel/random/boot_id /proc/uptime /proc/sys/kernel/tainted
    for p in /sys/class/remoteproc/remoteproc*; do cat "$p/name" "$p/state"; done
} > "$out/state.txt"
ps > "$out/processes.txt"
cat /proc/modules > "$out/modules.txt"
cat /proc/interrupts > "$out/interrupts.txt"
cat /proc/mounts > "$out/mounts.txt"
dmesg > "$out/dmesg.txt"
qrtr-lookup > "$out/qrtr.txt"
cp /run/samurai-wifi/boot-finished /run/samurai-wifi-boot.log /run/samurai-bluetooth-boot.log "$out/"
for name in tftp.log rmtfs.log wpa.log; do cp "/run/samurai-wifi/$name" "$out/$name"; done
/usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status > "$out/wpa-status.txt"
ls /sys/class/bluetooth > "$out/bt-class.txt"
cat "$(/tmp/k108-haptics-device)/status" > "$out/haptics-status.txt"
cat /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status > "$out/amp-status.txt"
cat /proc/asound/card0/pcm0p/sub0/status /proc/asound/card0/pcm1c/sub0/status > "$out/pcm-status.txt"
cat /sys/kernel/debug/dri/1/state > "$out/drm-state.txt"
cat /sys/kernel/debug/dri/1/encoder-0/status > "$out/encoder.txt"
for name in brightness actual_brightness bl_power; do cat "/sys/class/backlight/ae94000.dsi.0/$name" > "$out/$name.txt"; done
sha256sum /sys/kernel/tracing/instances/display/snapshot > "$out/display-snapshot.sha"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$out/nv-check.txt"
sha256sum /dev/sda2 /dev/sde17 /dev/sde11 /dev/sde32 > "$out/partitions.sha"
sha256sum /init /usr/sbin/samurai-wifi /usr/sbin/samurai-radio-address /usr/sbin/samurai-modem-remoteproc > "$out/services.sha"
cp /sys/firmware/fdt "$out/runtime-fdt.bin"
(cd "$out" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$out/SHA256SUMS"
tar -cf "$out.tar" -C /tmp k108-checkpoint
sha256sum "$out.tar"
echo CHECKPOINT_COMPLETE
