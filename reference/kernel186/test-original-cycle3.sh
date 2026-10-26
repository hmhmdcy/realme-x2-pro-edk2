#!/bin/sh
set -eu
umask 077
uname -v | grep -q '^#183 '
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k186-reboot-runtime/boot-id-private.txt)"
test "$(cat /proc/sys/kernel/tainted)" = 0
grep -q '^/dev/sda16 / f2fs rw' /proc/mounts
test "$(cat /sys/class/remoteproc/remoteproc0/name)" = slpi
test "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline
test -z "$(pidof hexagonrpcd hexagonrpcd-v5)"
test "$(cat /var/lib/samurai/k112-project-metadata/modemType)" = 4
src=/var/lib/samurai/k111-sensor-sources-readonly
root=/run/samurai-sensors-ram-k186-original-cycle3
dest=/var/lib/samurai/k186-original-cycle3
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
original_fw=qcom/sm8150/realme/samurai/slpi.mdt
original_recovery=$(cat "$node/recovery")
owner=
recover_owner=
finish() {
    code=$?
    trap - EXIT
    set +e
    if [ "$(cat "$node/state")" != offline ]; then
        timeout -s TERM -k 2 12 sh -c 'echo stop > "$1/state"' sh "$node" > "$dest/stop.txt" 2>&1
        printf '%s\n' "$?" > "$dest/stop-exit.txt"
    else
        echo ALREADY_OFFLINE > "$dest/stop.txt"
        echo 0 > "$dest/stop-exit.txt"
    fi
    if [ -n "$owner" ]; then
        if kill -0 "$owner" 2>/dev/null; then kill -TERM "$owner"; fi
        wait "$owner"
        printf '%s\n' "$?" > "$dest/daemon-exit.txt"
        cat /proc/uptime > "$dest/daemon-uptime-end.txt"
        owner=
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
    if [ "$(cat "$node/state")" = offline ]; then echo "$original_recovery" > "$node/recovery"; fi
    if [ "$(cat "$node/state")" = offline ]; then
        printf '%s\n' "$original_fw" > "$node/firmware"
    fi
    cat "$node/firmware" > "$dest/firmware-final.txt"
    cat "$power" > "$dest/power-final.txt"
    cat /sys/kernel/debug/regulator/regulator_summary > "$dest/regulators-final.txt"
    cat /proc/uptime /proc/sys/kernel/tainted > "$dest/kernel-state-after.txt"
    sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-after.txt"
    sha256sum -c "$src/sources-before.sha256" > "$dest/source-after.txt"
    (cd "$root" && find . -type f -exec sha256sum '{}' ';') > "$dest/ram-tree-after.sha256"
    dmesg > "$dest/dmesg-final.txt"
    printf '%s\n' "$code" > "$dest/trial-exit.txt"
    (cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
    tar -C "$dest" -cf /tmp/k186-original-cycle3.tar .
    sha256sum /tmp/k186-original-cycle3.tar
    printf 'RAM_ATTRIBUTES15_FINAL_SLPI=%s POWER=%s TAINT=%s\n' "$(cat "$node/state")" "$(cat "$power")" "$(cat /proc/sys/kernel/tainted)"
    exit "$code"
}
trap finish EXIT
test "$(cat "$node/firmware")" = "$original_fw"
cat "$node/firmware" > "$dest/firmware-before.txt"
cat "$node/firmware" > "$dest/firmware-selected.txt"
sha256sum "$src/firmware"/* > "$dest/original-firmware.sha256"
modprobe socinfo
test "$(cat /sys/devices/soc0/soc_id)" = 339
test "$(cat /sys/kernel/debug/qcom_socinfo/hardware_platform)" = 8
test "$(cat /sys/kernel/debug/qcom_socinfo/hardware_platform_subtype)" = 0
test "$(cat /sys/kernel/debug/qcom_socinfo/platform_version)" = 65536
mkdir -p "$root/dsp/sdsp" "$root/sensors/config" "$root/sensors/registry" "$root/socinfo" "$root/oppoVersion"
cp -a "$src/sdsp/." "$root/dsp/sdsp/"
cp -a "$src/sensors-vendor/config/." "$root/sensors/config/"
echo '9fe3391f86ef0b70b3a6b696d4d353a594bc27b5765434c7d9ede489ac6a0535  /var/lib/samurai/k113-tools/magnetometer-config-escaped-control-private.json' | sha256sum -c - > "$dest/config-candidate-check.txt"
echo "f84bee57583cdc8b8eec7c8cc0d2aea477ac20932ac1cde4e2b5b670fb091fe4  $root/sensors/config/msmnile_mmc5603nj.json" | sha256sum -c - > "$dest/config-original-check.txt"
cp /var/lib/samurai/k113-tools/magnetometer-config-escaped-control-private.json "$root/sensors/config/msmnile_mmc5603nj.json"
echo "9fe3391f86ef0b70b3a6b696d4d353a594bc27b5765434c7d9ede489ac6a0535  $root/sensors/config/msmnile_mmc5603nj.json" | sha256sum -c - > "$dest/config-patched-check.txt"
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
modprobe fastrpc
test -c /dev/fastrpc-sdsp
test "$(cat /proc/sys/kernel/tainted)" = 0
sync
echo '1902f1b62aea2d0038a9138ae1cd996941f0d0deaa3804d9317ebdc69836e270  /var/lib/samurai/k113-tools/hexagonrpcd-v5' | sha256sum -c - > "$dest/daemon-check.txt"
cat /proc/uptime > "$dest/daemon-uptime-start.txt"
timeout -s TERM -k 3 110 /var/lib/samurai/k113-tools/hexagonrpcd-v5 -f /dev/fastrpc-sdsp -d sdsp -R "$root" -s > "$dest/rpcd.txt" 2>&1 &
owner=$!
sleep 20
kill -0 "$owner"
set +e
timeout -s TERM -k 2 55 python3 -B /var/lib/samurai/k186-tools/ssc-light-probe.py --output "$dest/light" --duration 20 > "$dest/light-host-private.txt" 2>&1
query=$?
printf '%s\n' "$query" > "$dest/light-exit.txt"
set -e
test "$(cat "$node/state")" = running
kill -0 "$owner"
exit "$query"
