#!/bin/sh
set -eu
umask 077
[ "$#" = 2 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
case "$2" in ''|*[!0-9]*) exit 1;; esac
[ "$2" -gt 1000000 ] && [ "$2" -lt 100663296 ]
uname -a | grep -q '#100 SMP PREEMPT'
dir=/tmp/k101-audio-runtime
test ! -e "$dir"
mkdir -m700 "$dir"
mountpoint -q /sys/kernel/debug || mount -t debugfs debugfs /sys/kernel/debug
{
    uname -a
    cat /proc/sys/kernel/random/boot_id /proc/uptime /proc/sys/kernel/tainted
    for p in /sys/class/remoteproc/remoteproc*; do
        echo "$p"
        cat "$p/name" "$p/state" "$p/firmware" "$p/recovery"
        readlink -f "$p/device/of_node"
    done
} > "$dir/state.txt"
adsp=
count=0
for p in /sys/class/remoteproc/remoteproc*; do
    if [ "$(cat "$p/name")" = adsp ]; then
        tr '\0' '\n' < "$p/device/of_node/compatible" | grep -qx qcom,sm8150-adsp-pas
        [ "$(cat "$p/firmware")" = qcom/sm8150/realme/samurai/adsp.mdt ]
        adsp=$p
        count=$((count+1))
    fi
done
[ "$count" = 1 ]
echo "$adsp" > "$dir/adsp-path.txt"
# Observe failures without initiating synthetic crashes or restart loops.
echo disabled > "$adsp/recovery"
cat "$adsp/state" > "$dir/adsp-state.txt"
/usr/sbin/samurai-modem-remoteproc > "$dir/mpss-path.txt"
cat "$(cat "$dir/mpss-path.txt")/state" > "$dir/mpss-state.txt"
cat /proc/modules > "$dir/modules.txt"
ps > "$dir/processes.txt"
find /sys/bus/rpmsg/devices /sys/bus/aprbus/devices -maxdepth 2 -type l -exec ls -l '{}' ';' > "$dir/audio-bus.txt"
# The attribute calls the native bounded GET_FWK_VERSION / legacy fallback.
# A missing service or timeout is retained as a failed query, never readiness.
query=0
for f in /sys/bus/aprbus/devices/*/samurai_api; do
    test -r "$f" || continue
    query=$((query+1))
    if cat "$f" > "$dir/native-api-reply.txt" 2> "$dir/native-api-error.txt"; then
        echo 0 > "$dir/native-api-exit.txt"
    else
        echo 1 > "$dir/native-api-exit.txt"
    fi
done
echo "$query" > "$dir/native-api-attributes.txt"
cat /proc/asound/cards > "$dir/alsa-cards.txt"
cat /sys/bus/i2c/devices/1-005a/status > "$dir/haptics-status.txt"
cp /run/samurai-wifi-boot.log /run/samurai-bluetooth-boot.log "$dir/"
test ! -e /run/samurai-wifi/boot-finished || cp /run/samurai-wifi/boot-finished "$dir/"
test ! -e /run/samurai-wifi/nv-source-hashes.txt || {
    cp /run/samurai-wifi/nv-source-hashes.txt "$dir/"
    sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-source-check.txt"
}
sha256sum /dev/sda2 > "$dir/persist-after.sha"
dd if=/dev/sde11 of=/tmp/k101-boot-readback.img bs=1048576
dd if=/dev/sde32 of=/tmp/k101-logdump-readback.img bs=1048576
sha256sum /tmp/k101-boot-readback.img /tmp/k101-logdump-readback.img > "$dir/partitions.sha"
head -c "$2" /dev/sde11 | sha256sum > "$dir/boot-prefix.sha"
sha256sum /init /usr/sbin/samurai-wifi /usr/sbin/samurai-radio-address /usr/sbin/samurai-modem-remoteproc > "$dir/deployment.sha"
cp /sys/firmware/fdt "$dir/runtime-fdt.bin"
dmesg > "$dir/dmesg.txt"
/usr/sbin/qrtr-lookup > "$dir/qrtr.txt"
(cd "$dir" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
tar -C /tmp -cf /tmp/k101-audio-runtime.tar k101-audio-runtime
sha256sum /tmp/k101-audio-runtime.tar
echo AUDIO_RUNTIME_CAPTURE_COMPLETE
