#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#105 SMP PREEMPT'
grep -qx closed /proc/asound/card0/pcm0p/sub0/status
grep -qx closed /proc/asound/card0/pcm1c/sub0/status
for p in /sys/bus/i2c/devices/1-0039 /sys/bus/i2c/devices/1-003a; do
    cat "$p/status" | grep -q 'global=00 amp=80 .*powered=0 muted=1 .*failed=0'
done
dir=/tmp/k106-core-rebind-once
test ! -e "$dir"
mkdir -m700 "$dir"
test -f /tmp/k106-first-radio-trace/SHA256SUMS
(cd /tmp/k106-first-radio-trace && sha256sum -c SHA256SUMS) > "$dir/first-trace-source-check.txt"
radio=/sys/kernel/tracing/instances/radio
test "$(cat "$radio/tracing_on")" = 0
echo > "$radio/trace"
echo 1 > "$radio/tracing_on"
count=0
for f in /sys/bus/aprbus/devices/*/samurai_api; do
    test -r "$f" || continue
    count=$((count+1)); core=${f%/samurai_api}
done
[ "$count" = 1 ]
[ "$(readlink -f "$core/of_node")" = /sys/firmware/devicetree/base/soc@0/remoteproc@17300000/glink-edge/apr/service@3 ]
driver=$(readlink -f "$core/driver")
[ "$driver" = /sys/bus/aprbus/drivers/qcom-q6core ]
name=${core##*/}
if cat "$core/samurai_api" > "$dir/api-before.txt" 2> "$dir/api-before-error.txt"; then
    echo 0 > "$dir/api-before-exit.txt"
else
    echo 1 > "$dir/api-before-exit.txt"
fi
dmesg > "$dir/dmesg-before.txt"
cat /proc/uptime > "$dir/start.txt"
# One normal driver detach/attach while all PCMs are closed. No DSP restart.
printf '%s' "$name" > "$driver/unbind"
printf '%s' "$name" > "$driver/bind"
if cat "$core/samurai_api" > "$dir/api-after.txt" 2> "$dir/api-after-error.txt"; then
    echo 0 > "$dir/api-after-exit.txt"
else
    echo 1 > "$dir/api-after-exit.txt"
fi
cat /proc/uptime > "$dir/end.txt"
cat /proc/asound/cards > "$dir/alsa-after.txt"
for p in /sys/class/remoteproc/remoteproc*; do cat "$p/name" "$p/state"; done > "$dir/remoteproc-after.txt"
cat /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status > "$dir/amps-after.txt"
echo 0 > "$radio/tracing_on"
cat "$radio/trace" > "$dir/trace.txt"
for cpu in "$radio"/per_cpu/cpu*; do
    cat "$cpu/stats" > "$dir/${cpu##*/}-stats.txt"
done
dmesg > "$dir/dmesg-after.txt"
(cd "$dir" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
tar -C /tmp -cf /tmp/k106-core-rebind-once.tar k106-core-rebind-once
sha256sum /tmp/k106-core-rebind-once.tar
echo SINGLE_CORE_CACHE_DIAGNOSTIC_CAPTURED
