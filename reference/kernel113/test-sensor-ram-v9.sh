#!/bin/sh
set -eu
umask 077
uname -v | grep -q '^#113 '
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k113-reboot-radio-clean-4/boot-id-private.txt)"
test "$(cat /proc/sys/kernel/tainted)" = 0
grep -q '^/dev/sda16 / f2fs rw' /proc/mounts
test "$(cat /sys/class/remoteproc/remoteproc0/name)" = slpi
test "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline
test ! -e /dev/fastrpc-sdsp
test -z "$(pidof hexagonrpcd)"
test "$(cat /var/lib/samurai/k112-project-metadata/modemType)" = 4
src=/var/lib/samurai/k111-sensor-sources-readonly
root=/run/samurai-sensors-ram-v9
dest=/var/lib/samurai/k113-sensor-ram-v9
test ! -e "$root" && test ! -e "$dest"
mkdir -m700 "$root" "$dest"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
cat /proc/uptime > "$dest/uptime-before.txt"
dmesg > "$dest/dmesg-before.txt"
sha256sum -c "$src/sources-before.sha256" > "$dest/source-before.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-before.txt"
for file in "$src/firmware"/*; do cmp "$file" "/lib/firmware/qcom/sm8150/realme/samurai/$(basename "$file")"; done
node=/sys/class/remoteproc/remoteproc0
power=/sys/devices/platform/sensor-power/state
test "$(cat "$power")" = 'vdd=0 vddio=0'
cat "$power" > "$dest/power-before.txt"
cat /sys/kernel/debug/regulator/regulator_summary > "$dest/regulators-before.txt"
owner=
recover_owner=
finish() {
    code=$?
    trap - EXIT
    set +e
    if [ -n "$owner" ] && kill -0 "$owner" 2>/dev/null; then
        kill -TERM "$owner"
        wait "$owner"
    fi
    if [ "$(cat "$node/state")" != offline ]; then
        timeout -s TERM -k 2 12 sh -c 'echo stop > "$1/state"' sh "$node" > "$dest/stop.txt" 2>&1
        printf '%s\n' "$?" > "$dest/stop-exit.txt"
    else
        echo ALREADY_OFFLINE > "$dest/stop.txt"
        echo 0 > "$dest/stop-exit.txt"
    fi
    if [ -n "$recover_owner" ]; then
        wait "$recover_owner"
        recover_owner=
    fi
    cat "$node/state" > "$dest/slpi-final-state.txt"
    if [ "$(cat "$node/state")" = offline ]; then
        timeout -s TERM -k 2 5 sh -c 'echo 0 > "$1"' sh "$power" > "$dest/power-off.txt" 2>&1
        printf '%s\n' "$?" > "$dest/power-off-exit.txt"
    else
        echo RETAINED_REFS_DSP_NOT_OFFLINE > "$dest/power-off.txt"
        echo NOT_ATTEMPTED > "$dest/power-off-exit.txt"
    fi
    if [ "$(cat "$node/state")" = offline ]; then echo disabled > "$node/coredump"; fi
    cat "$power" > "$dest/power-final.txt"
    cat /sys/kernel/debug/regulator/regulator_summary > "$dest/regulators-final.txt"
    cat /proc/uptime /proc/sys/kernel/tainted > "$dest/kernel-state-after.txt"
    sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-after.txt"
    sha256sum -c "$src/sources-before.sha256" > "$dest/source-after.txt"
    (cd "$root" && find . -type f -exec sha256sum '{}' ';') > "$dest/ram-tree-after.sha256"
    dmesg > "$dest/dmesg-final.txt"
    printf '%s\n' "$code" > "$dest/trial-exit.txt"
    (cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
    tar -C "$dest" -cf /tmp/k113-sensor-ram-v9.tar .
    sha256sum /tmp/k113-sensor-ram-v9.tar
    printf 'RAM_V9_FINAL_SLPI=%s POWER=%s TAINT=%s\n' "$(cat "$node/state")" "$(cat "$power")" "$(cat /proc/sys/kernel/tainted)"
    exit "$code"
}
trap finish EXIT
modules=/var/lib/samurai/k113-modules-candidate
(cd "$modules" && sha256sum -c SHA256SUMS) > "$dest/module-check.txt"
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
echo 1 > "$power"
test "$(cat "$power")" = 'vdd=1 vddio=1'
cat "$power" > "$dest/power-enabled.txt"
cat /sys/kernel/debug/regulator/regulator_summary > "$dest/regulators-enabled.txt"
cat "$node/recovery" > "$dest/recovery-before.txt"
echo disabled > "$node/recovery"
set +e
timeout -s TERM -k 2 15 sh -c 'echo start > "$1/state"' sh "$node" > "$dest/start.txt" 2>&1
started=$?
set -e
printf '%s\n' "$started" > "$dest/start-exit.txt"
if [ "$started" != 0 ] || [ "$(cat "$node/state")" != running ]; then
    echo QUERY_NOT_RUN_START_FAILED > "$dest/result.txt"
    exit 1
fi

sleep 5
qrtr-lookup > "$dest/qrtr-start.txt"
insmod "$modules/fastrpc.ko"
test -c /dev/fastrpc-sdsp
test "$(cat /proc/sys/kernel/tainted)" = 0
sync
echo '1902f1b62aea2d0038a9138ae1cd996941f0d0deaa3804d9317ebdc69836e270  /var/lib/samurai/k113-tools/hexagonrpcd-v5' | sha256sum -c - > "$dest/daemon-check.txt"
cat /proc/uptime > "$dest/daemon-uptime-start.txt"
timeout -s TERM -k 3 240 /var/lib/samurai/k113-tools/hexagonrpcd-v5 -f /dev/fastrpc-sdsp -d sdsp -R "$root" -s > "$dest/rpcd.txt" 2>&1 &
owner=$!
sleep 20
printf 'PROXIMITY_COVER_WINDOW_OPEN_120_SECONDS\n'
cat /proc/uptime > "$dest/proximity-window-uptime.txt"
set +e
timeout -s TERM -k 2 128 ssccli --debug --sensor proximity --timeout 120 > "$dest/proximity.txt" 2>&1
printf '%s\n' "$?" > "$dest/proximity-exit.txt"
printf 'PROXIMITY_COVER_WINDOW_CLOSED\n'
timeout -s TERM -k 2 18 ssccli --debug --sensor accelerometer --timeout 10 > "$dest/accelerometer.txt" 2>&1
query=$?
for kind in light magnetometer; do
    if ! kill -0 "$owner" 2>/dev/null; then break; fi
    timeout -s TERM -k 2 18 ssccli --debug --sensor "$kind" --timeout 10 > "$dest/$kind.txt" 2>&1
    printf '%s\n' "$?" > "$dest/$kind-exit.txt"
done
wait "$owner"
daemon=$?
cat /proc/uptime > "$dest/daemon-uptime-end.txt"
owner=
set -e
printf '%s\n' "$query" > "$dest/query-exit.txt"
printf '%s\n' "$daemon" > "$dest/daemon-exit.txt"
cat "$node/state" > "$dest/slpi-state-after.txt"
dmesg > "$dest/dmesg-after.txt"
qrtr-lookup > "$dest/qrtr-after.txt"
printf 'SENSOR_QUERY_EXIT=%s RPCD_EXIT=%s\n' "$query" "$daemon"
test "$(cat "$node/state")" = running
test "$(cat "$node/recovery")" = disabled
test -z "$(find /sys/class/devcoredump -maxdepth 1 -name 'devcd*' -print)"
echo enabled > "$node/coredump"
cat "$node/coredump" > "$dest/coredump-mode.txt"
sync
printf 'SLPI_COREDUMP_CAPTURE_BEGIN\n'
echo 1 > /sys/kernel/debug/remoteproc/remoteproc0/crash
i=0
while [ "$(cat "$node/state")" != crashed ] && [ "$i" -lt 40 ]; do
    sleep 0.25; i=$((i+1))
done
test "$(cat "$node/state")" = crashed
timeout -s TERM -k 3 60 sh -c 'echo recover > "$1/recovery"' sh "$node" > "$dest/recover.txt" 2>&1 &
recover_owner=$!
i=0
while [ -z "$(find /sys/class/devcoredump -maxdepth 1 -name 'devcd*' -print)" ] && [ "$i" -lt 100 ]; do
    sleep 0.25; i=$((i+1))
done
dump_node=$(find /sys/class/devcoredump -maxdepth 1 -name 'devcd*' -print)
if [ -n "$dump_node" ] && [ "$(printf '%s\n' "$dump_node" | wc -l)" = 1 ]; then
    readlink -f "$dump_node/failing_device" > "$dest/coredump-device-private.txt"
    case "$(cat "$dest/coredump-device-private.txt")" in
        */2400000.remoteproc/remoteproc/remoteproc0) ;;
        *) echo WRONG_COREDUMP_DEVICE > "$dest/coredump-error.txt"; exit 1 ;;
    esac
    timeout -s TERM -k 2 25 cat "$dump_node/data" > "$dest/slpi-coredump.elf"
    printf '%s\n' "$?" > "$dest/coredump-read-exit.txt"
    test "$(head -c 4 "$dest/slpi-coredump.elf" | od -An -tx1 | tr -d ' \n')" = 7f454c46
    wc -c < "$dest/slpi-coredump.elf" > "$dest/coredump-size.txt"
    sha256sum "$dest/slpi-coredump.elf" > "$dest/coredump.sha256"
    echo 1 > "$dump_node/data"
else
    echo NO_SINGLE_COREDUMP > "$dest/coredump-error.txt"
fi
set +e
wait "$recover_owner"
printf '%s\n' "$?" > "$dest/recover-exit.txt"
recover_owner=
set -e
cat "$node/state" > "$dest/slpi-state-after-coredump.txt"
echo disabled > "$node/recovery"
if [ "$(cat "$node/state")" != crashed ]; then echo disabled > "$node/coredump"; fi
printf 'SLPI_COREDUMP_CAPTURE_FINISHED\n'

exit 0
