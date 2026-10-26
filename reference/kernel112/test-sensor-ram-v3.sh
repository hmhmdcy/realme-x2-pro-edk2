#!/bin/sh
set -eu
umask 077
uname -v | grep -q '^#112 '
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k112-reboot-radio-clean-1/boot-id-private.txt)"
test "$(cat /proc/sys/kernel/tainted)" = 0
grep -q '^/dev/sda16 / f2fs rw' /proc/mounts
test "$(cat /sys/class/remoteproc/remoteproc0/name)" = slpi
test "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline
test ! -e /dev/fastrpc-sdsp
test -z "$(pidof hexagonrpcd)"
test "$(cat /var/lib/samurai/k112-project-metadata/modemType)" = 4
src=/var/lib/samurai/k111-sensor-sources-readonly
root=/run/samurai-sensors-ram-v3
dest=/var/lib/samurai/k112-sensor-ram-v3
test ! -e "$root" && test ! -e "$dest"
mkdir -m700 "$root" "$dest"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
cat /proc/uptime > "$dest/uptime-before.txt"
dmesg > "$dest/dmesg-before.txt"
sha256sum -c "$src/sources-before.sha256" > "$dest/source-before.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-before.txt"
for file in "$src/firmware"/*; do cmp "$file" "/lib/firmware/qcom/sm8150/realme/samurai/$(basename "$file")"; done
modules=/var/lib/samurai/k111-modules-candidate
insmod "$modules/socinfo.ko"
test "$(cat /sys/devices/soc0/soc_id)" = 339
test "$(cat /sys/kernel/debug/qcom_socinfo/hardware_platform)" = 8
test "$(cat /sys/kernel/debug/qcom_socinfo/hardware_platform_subtype)" = 0
test "$(cat /sys/kernel/debug/qcom_socinfo/platform_version)" = 65536
mkdir -p "$root/dsp/sdsp" "$root/sensors/config" "$root/sensors/registry" "$root/socinfo" "$root/oppoVersion"
cp -a "$src/sdsp/." "$root/dsp/sdsp/"
cp -a "$src/sensors-vendor/config/." "$root/sensors/config/"
cp -a "$src/sensors-persist/registry/." "$root/sensors/registry/"
chown -R 0:0 "$root/sensors/registry"
chmod 700 "$root/sensors/registry"
test -z "$(find "$root" -type l -print)"
cp -p "$src/sensors-vendor/sns_reg_config" "$root/sensors/sns_reg.conf"
cp /var/lib/samurai/k112-project-metadata/modemType "$root/oppoVersion/modemType"
for name in soc_id revision family machine; do cat "/sys/devices/soc0/$name" > "$root/socinfo/$name"; done
printf 'MTP\n' > "$root/socinfo/hw_platform"
printf 'Unknown\n' > "$root/socinfo/platform_subtype"
cat /sys/kernel/debug/qcom_socinfo/hardware_platform_subtype > "$root/socinfo/platform_subtype_id"
cat /sys/kernel/debug/qcom_socinfo/platform_version > "$root/socinfo/platform_version"
(cd "$root" && find . -type f -exec sha256sum '{}' ';') > "$dest/ram-tree-before.sha256"
rc-service iio-sensor-proxy stop > "$dest/iio-stop.txt" 2>&1 || true
node=/sys/class/remoteproc/remoteproc0
cat "$node/recovery" > "$dest/recovery-before.txt"
echo disabled > "$node/recovery"
set +e
timeout -s TERM -k 2 15 sh -c 'echo start > "$1/state"' sh "$node" > "$dest/start.txt" 2>&1
started=$?
set -e
printf '%s\n' "$started" > "$dest/start-exit.txt"
if [ "$started" != 0 ] || [ "$(cat "$node/state")" != running ]; then
    dmesg > "$dest/dmesg-after.txt"
    cat /proc/uptime /proc/sys/kernel/tainted > "$dest/kernel-state-after.txt"
    cat "$node/state" > "$dest/slpi-final-state.txt"
    sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-after.txt"
    sha256sum -c "$src/sources-before.sha256" > "$dest/source-after.txt"
    echo QUERY_NOT_RUN_START_FAILED > "$dest/result.txt"
    (cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
    tar -C "$dest" -cf /tmp/k112-sensor-ram-v3.tar .
    sha256sum /tmp/k112-sensor-ram-v3.tar
    exit 1
fi
sleep 5
qrtr-lookup > "$dest/qrtr-start.txt"
insmod "$modules/fastrpc.ko"
test -c /dev/fastrpc-sdsp
test "$(cat /proc/sys/kernel/tainted)" = 0
sync
timeout -s TERM -k 3 35 /var/lib/samurai/k112-rpcd-ram-trial/hexagonrpcd-v2 -f /dev/fastrpc-sdsp -d sdsp -R "$root" -s > "$dest/rpcd.txt" 2>&1 &
owner=$!
sleep 3
set +e
timeout -s TERM -k 2 18 ssccli --debug --sensor accelerometer --timeout 10 > "$dest/accelerometer.txt" 2>&1
query=$?
wait "$owner"
daemon=$?
set -e
printf '%s\n' "$query" > "$dest/query-exit.txt"
printf '%s\n' "$daemon" > "$dest/daemon-exit.txt"
cat "$node/state" > "$dest/slpi-state-after.txt"
dmesg > "$dest/dmesg-after.txt"
qrtr-lookup > "$dest/qrtr-after.txt"
set +e
timeout -s TERM -k 2 12 sh -c 'echo stop > "$1/state"' sh "$node" > "$dest/stop.txt" 2>&1
stopped=$?
set -e
printf '%s\n' "$stopped" > "$dest/stop-exit.txt"
cat "$node/state" > "$dest/slpi-final-state.txt"
cat /proc/uptime /proc/sys/kernel/tainted > "$dest/kernel-state-after.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-after.txt"
sha256sum -c "$src/sources-before.sha256" > "$dest/source-after.txt"
(cd "$root" && find . -type f -exec sha256sum '{}' ';') > "$dest/ram-tree-after.sha256"
dmesg > "$dest/dmesg-final.txt"
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -cf /tmp/k112-sensor-ram-v3.tar .
sha256sum /tmp/k112-sensor-ram-v3.tar
printf 'SENSOR_QUERY_EXIT=%s RPCD_EXIT=%s STOP_EXIT=%s FINAL_STATE=%s TAINT=%s\n' "$query" "$daemon" "$stopped" "$(cat "$node/state")" "$(cat /proc/sys/kernel/tainted)"
