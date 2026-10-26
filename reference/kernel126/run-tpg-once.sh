#!/bin/sh
set -eu
umask 077
uname -v | grep -q '^#126 '
test "$(uname -r)" = 7.3.0-rc6-rmx1931-samurai-k126+
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k126-embedded-runtime/boot-id-private.txt)"
test "$(cat /proc/sys/kernel/tainted)" = 0
test -c /dev/media0
test -r /sys/module/qcom_camss/parameters/dma_trace
test "$(cat /sys/module/qcom_camss/parameters/dma_trace)" = N
test "$(cat /sys/devices/platform/sensor-power/state)" = 'vdd=0 vddio=0'
dest=/var/lib/samurai/k126-tpg-once
test ! -e "$dest"
mkdir -m700 "$dest"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
dmesg > "$dest/dmesg-before.txt"
cat /proc/interrupts > "$dest/interrupts-before.txt"
cat /sys/kernel/debug/pm_genpd/pm_genpd_summary > "$dest/power-before.txt"
chmod 700 /tmp/k126-tpg-capture
/tmp/k126-tpg-capture --self-test > "$dest/tool-self-test.txt"
cleanup() { echo 0 > /sys/module/qcom_camss/parameters/dma_trace; }
trap cleanup EXIT HUP INT TERM
echo 1 > /sys/module/qcom_camss/parameters/dma_trace
set +e
timeout -s TERM -k 5 30 /tmp/k126-tpg-capture --capture "$dest/first-frame-private.raw" > "$dest/capture.txt" 2>&1
code=$?
set -e
printf '%s\n' "$code" > "$dest/capture-exit.txt"
cleanup
cat /sys/module/qcom_camss/parameters/dma_trace > "$dest/dma-trace-after.txt"
dmesg > "$dest/dmesg-after.txt"
cat /proc/interrupts > "$dest/interrupts-after.txt"
cat /sys/kernel/debug/pm_genpd/pm_genpd_summary > "$dest/power-after.txt"
cat /proc/sys/kernel/tainted > "$dest/taint-after.txt"
cat /sys/class/remoteproc/remoteproc0/state /sys/devices/platform/sensor-power/state > "$dest/sensor-after.txt"
if test -e "$dest/first-frame-private.raw"; then sha256sum "$dest/first-frame-private.raw" > "$dest/frame.sha256"; fi
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -cf /tmp/k126-tpg-once-private.tar .
cat "$dest/capture.txt"
printf 'K126_TPG_CAPTURE_EXIT=%s\n' "$code"
echo K126_TPG_ONE_ATTEMPT_CAPTURED_WITH_DMA_TRACE_DISABLED
