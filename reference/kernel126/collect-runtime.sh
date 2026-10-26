#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k126-first-runtime
test ! -e "$dest"
uname -v | grep -q '^#126 '
test "$(cat /proc/sys/kernel/random/boot_id)" != "$(cat /var/lib/samurai/k126-preflash/boot-id-private.txt)"
grep -q '^/dev/sda16 / f2fs rw' /proc/mounts
mkdir -m700 "$dest"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
uname -a > "$dest/uname.txt"
cat /proc/uptime /proc/sys/kernel/tainted > "$dest/state.txt"
cat /proc/mounts > "$dest/mounts.txt"
cat /sys/firmware/fdt > "$dest/live-fdt-private.dtb"
cat /sys/class/remoteproc/remoteproc0/state /sys/devices/platform/sensor-power/state > "$dest/sensors.txt"
cat /sys/class/remoteproc/remoteproc1/state /sys/class/remoteproc/remoteproc2/state > "$dest/radio-audio.txt"
rc-status default > "$dest/services.txt"
pgrep -x phosh > "$dest/phosh.txt" || true
pgrep -x phoc > "$dest/phoc.txt" || true
ls -l /dev/dri > "$dest/drm.txt" 2>&1 || true
cat /sys/class/drm/card*-DSI-1/status > "$dest/connector.txt" 2>&1 || true
card=$(basename "$(readlink -f /dev/dri/by-path/platform-ae01000.display-controller-card)")
test -n "$card"
minor=$(cat "/sys/class/drm/$card/dev"); minor=${minor#*:}
printf '%s %s\n' "$card" "$minor" > "$dest/drm-resolved.txt"
cat "/sys/kernel/debug/dri/$minor/state" > "$dest/drm-state.txt" 2>&1 || true
cat /proc/asound/cards > "$dest/soundcards.txt"
for pcm in pcm0p pcm1c; do cat "/proc/asound/card0/$pcm/sub0/status" || true; done > "$dest/pcm.txt" 2>&1
cat /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status > "$dest/amps.txt"
cat /proc/swaps > "$dest/swaps.txt"
cat /sys/block/zram0/comp_algorithm /sys/block/zram0/disksize > "$dest/zram.txt" 2>&1 || true
cat /sys/class/net/wlan0/operstate > "$dest/wlan-state.txt" 2>&1 || true
ip -details link show rmnet_ipa0 > "$dest/ipa-net.txt" 2>&1 || true
timeout 10 mmcli -L > "$dest/modem-list-private.txt" 2>&1 || true
timeout 10 mmcli -m 0 -J > "$dest/modem-private.json" 2>&1 || true
sha256sum /lib/modules/7.3.0-rc6-rmx1931-samurai-k126+/kernel/drivers/net/ipa/ipa.ko > "$dest/ipa-module.sha256"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-check.txt"
sha256sum -c /var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256 > "$dest/source-check.txt"
sha256sum -c /var/lib/samurai/k115-vendor-camera-source/vendor-before.sha256 > "$dest/vendor-check.txt"
sha256sum /dev/sde11 /dev/sde32 /dev/sda2 > "$dest/partition-check.sha256"
for dev in sda sdb sdc sdd sde sdf; do
    sectors=$(blockdev --getsz "/dev/$dev")
    test "$(blockdev --getss "/dev/$dev")" = 4096
    blocks=$((sectors / 8))
    blockdev --getsz "/dev/$dev" > "$dest/$dev.geometry"
    blockdev --getss "/dev/$dev" >> "$dest/$dev.geometry"
    cat "/sys/block/$dev/device/model" >> "$dest/$dev.geometry"
    dd if="/dev/$dev" of="$dest/$dev.head" bs=4096 count=34 status=none
    dd if="/dev/$dev" of="$dest/$dev.tail" bs=4096 skip=$((blocks - 34)) count=34 status=none
done
for instance in /sys/kernel/tracing/instances/*; do
    test -d "$instance" || continue
    printf '%s ' "${instance##*/}" >> "$dest/traces.txt"
    cat "$instance/tracing_on" >> "$dest/traces.txt"
done
ls -l /dev/media* /dev/video* /dev/v4l-subdev* > "$dest/camera-nodes.txt" 2>&1 || true
cat /sys/module/qcom_camss/parameters/dma_trace > "$dest/dma-trace.txt" 2>&1 || true
cat /proc/interrupts > "$dest/interrupts.txt"
for item in /sys/class/remoteproc/remoteproc*; do printf '%s %s %s\n' "${item##*/}" "$(cat "$item/name")" "$(cat "$item/state")"; done > "$dest/remoteproc-names.txt"
dmesg > "$dest/dmesg.txt"
cp /home/cy122/.local/state/samurai-phosh-session.log "$dest/phosh-session-private.txt" 2>/dev/null || true
sync
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -czf /tmp/k126-first-runtime-private.tar.gz .
sha256sum /tmp/k126-first-runtime-private.tar.gz
echo KERNEL126_FIRST_NATIVE_RUNTIME_CAPTURED
