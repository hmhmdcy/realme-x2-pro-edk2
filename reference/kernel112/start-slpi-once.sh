#!/bin/sh
set -eu
umask 077
uname -v | grep -q '^#112 '
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k112-first-before-slpi/boot-id-private.txt)"
test "$(cat /proc/sys/kernel/tainted)" = 0
grep -q '^/dev/sda16 / f2fs rw' /proc/mounts
test ! -e /dev/fastrpc-sdsp
test -z "$(lsmod | awk '$1=="fastrpc" {print $1}')"
src=/var/lib/samurai/k111-sensor-sources-readonly/firmware
fw=/lib/firmware/qcom/sm8150/realme/samurai
for file in "$src"/*; do
    test -f "$file"; cmp "$file" "$fw/$(basename "$file")"
done
target=
for node in /sys/class/remoteproc/*; do
    test "$(cat "$node/name")" = slpi || continue
    test -z "$target"
    test "$(cat "$node/firmware")" = qcom/sm8150/realme/samurai/slpi.mdt
    test "$(tr -d '\000' < "$node/device/of_node/compatible")" = qcom,sm8150-slpi-pas
    target=$node
done
test -n "$target"
test "$(cat "$target/state")" = offline
dest=/var/lib/samurai/k112-slpi-start-once
test ! -e "$dest"
mkdir -m700 "$dest"
printf '%s\n' "$target" > "$dest/remoteproc-node-private.txt"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
cat "$target/recovery" > "$dest/recovery-before.txt"
cat "$target/coredump" > "$dest/coredump-before.txt"
cat /proc/uptime > "$dest/uptime-before.txt"
dmesg > "$dest/dmesg-before.txt"
qrtr-lookup > "$dest/qrtr-before.txt"
rc-service iio-sensor-proxy stop > "$dest/iio-stop.txt" 2>&1 || true
echo disabled > "$target/recovery"
set +e
timeout -s TERM -k 2 15 sh -c 'echo start > "$1/state"' sh "$target" > "$dest/start-output.txt" 2>&1
result=$?
set -e
printf '%s\n' "$result" > "$dest/start-exit.txt"
cat "$target/state" > "$dest/state-after.txt"
sleep 5
qrtr-lookup > "$dest/qrtr-after.txt"
dmesg > "$dest/dmesg-after.txt"
cat /proc/uptime /proc/sys/kernel/tainted > "$dest/kernel-state-after.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-after.txt"
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -cf /tmp/k112-slpi-start-once.tar .
sha256sum /tmp/k112-slpi-start-once.tar
printf 'SLPI_START_EXIT=%s STATE=%s TAINT=%s\n' "$result" "$(cat "$dest/state-after.txt")" "$(cat /proc/sys/kernel/tainted)"
exit "$result"
