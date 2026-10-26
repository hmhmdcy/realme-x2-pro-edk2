#!/bin/sh
set -eu
umask 077
uname -v | grep -q '^#112 '
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k112-first-before-slpi/boot-id-private.txt)"
test "$(cat /proc/sys/kernel/tainted)" = 0
test -c /dev/fastrpc-sdsp
test "$(cat /sys/class/remoteproc/remoteproc0/name)" = slpi
test "$(cat /sys/class/remoteproc/remoteproc0/state)" = running
test "$(cat /sys/devices/soc0/soc_id)" = 339
# Stock Realme socinfo.c maps hardware-platform 8 to MTP. Use the live SMEM
# values for the Android-compatible attributes missing from mainline sysfs.
test "$(cat /sys/kernel/debug/qcom_socinfo/hardware_platform)" = 8
test "$(cat /sys/kernel/debug/qcom_socinfo/hardware_platform_subtype)" = 0
test "$(cat /sys/kernel/debug/qcom_socinfo/platform_version)" = 65536
src=/var/lib/samurai/k111-sensor-sources-readonly
root=/run/samurai-sensors-root
dest=/run/k112-sensor-rpc-once
test ! -e "$root" && test ! -e "$dest"
mkdir -m700 "$root" "$dest"
mkdir -p "$root/dsp/sdsp" "$root/sensors/config" "$root/sensors/registry" "$root/socinfo"
cp -a "$src/sdsp/." "$root/dsp/sdsp/"
cp -a "$src/sensors-vendor/config/." "$root/sensors/config/"
cp -a "$src/sensors-persist/registry/registry/." "$root/sensors/registry/"
cp -p "$src/sensors-vendor/sns_reg_config" "$root/sensors/sns_reg.conf"
for name in soc_id revision family machine; do cat "/sys/devices/soc0/$name" > "$root/socinfo/$name"; done
printf 'MTP\n' > "$root/socinfo/hw_platform"
cat /sys/kernel/debug/qcom_socinfo/hardware_platform_subtype > "$root/socinfo/platform_subtype_id"
cat /sys/kernel/debug/qcom_socinfo/platform_version > "$root/socinfo/platform_version"
(cd "$root" && find . -type f -exec sha256sum '{}' ';') > "$dest/ram-tree-before.sha256"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
cat /proc/uptime > "$dest/uptime-before.txt"
dmesg > "$dest/dmesg-before.txt"
sync
timeout -s TERM -k 3 35 hexagonrpcd -f /dev/fastrpc-sdsp -d sdsp -R "$root" -s > "$dest/rpcd.txt" 2>&1 &
owner=$!
printf '%s\n' "$owner" > "$dest/timeout-owner-private.txt"
sleep 3
set +e
timeout -s TERM -k 2 18 ssccli --debug --sensor accelerometer --timeout 10 > "$dest/accelerometer.txt" 2>&1
query=$?
wait "$owner"
daemon=$?
set -e
printf '%s\n' "$query" > "$dest/query-exit.txt"
printf '%s\n' "$daemon" > "$dest/daemon-exit.txt"
dmesg > "$dest/dmesg-after.txt"
cat /proc/uptime /proc/sys/kernel/tainted > "$dest/kernel-state-after.txt"
cat /sys/class/remoteproc/remoteproc0/state > "$dest/slpi-state-after.txt"
qrtr-lookup > "$dest/qrtr-after.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-after.txt"
(cd "$root" && find . -type f -exec sha256sum '{}' ';') > "$dest/ram-tree-after.sha256"
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -cf /tmp/k112-sensor-rpc-once.tar .
sha256sum /tmp/k112-sensor-rpc-once.tar
printf 'SENSOR_QUERY_EXIT=%s RPCD_EXIT=%s TAINT=%s\n' "$query" "$daemon" "$(cat /proc/sys/kernel/tainted)"
