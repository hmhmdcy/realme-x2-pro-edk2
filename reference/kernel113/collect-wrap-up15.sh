#!/bin/sh
set -eu
umask 077
uname -v | grep -q '^#113 '
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k113-reboot-audio-clean-15/boot-id-private.txt)"
dest=/var/lib/samurai/k113-wrap-up15
test ! -e "$dest"
mkdir -m700 "$dest"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
uname -a > "$dest/uname.txt"
cat /proc/mounts > "$dest/mounts-private.txt"
cat /proc/uptime /proc/sys/kernel/tainted > "$dest/state-before.txt"
dmesg > "$dest/dmesg-before-private.txt"
for node in /sys/class/devcoredump/devcd*; do
    test -d "$node" || continue
    source=$(readlink -f "$node/failing_device")
    printf '%s %s\n' "$(basename "$node")" "$source" >> "$dest/dump-sources.txt"
    case "$source" in */2c00000.gpu|*/ae01000.display-controller)
        set +e
        timeout -s TERM -k 2 20 cat "$node/data" > "$dest/$(basename "$node")-private.bin"
        printf '%s\n' "$?" > "$dest/$(basename "$node")-read-exit.txt"
        set -e
        ;;
    esac
done
for instance in /sys/kernel/tracing/instances/*; do
    test -d "$instance" || continue
    name=$(basename "$instance")
    case "$name" in display|radio|display-clock15|display-clock15b|display-linear15) ;; *) continue;; esac
    cat "$instance/tracing_on" > "$dest/$name-tracing-before.txt"
    cat "$instance/set_event" > "$dest/$name-events-before.txt"
    echo 0 > "$instance/tracing_on"
    if test "$name" = display || test "$name" = radio; then
        timeout -s TERM -k 2 15 cat "$instance/trace" > "$dest/$name-trace-private.txt"
        timeout -s TERM -k 2 15 cat "$instance/snapshot" > "$dest/$name-snapshot-private.txt"
    else
        cat "$instance/events/dpu/dpu_enc_frame_done_timeout/trigger" > "$dest/$name-trigger-before.txt"
        echo '!snapshot' > "$instance/events/dpu/dpu_enc_frame_done_timeout/trigger"
    fi
    echo 0 > "$instance/events/enable"
    cat "$instance/tracing_on" > "$dest/$name-tracing-after.txt"
    cat "$instance/set_event" > "$dest/$name-events-after.txt"
done
test -z "$(pidof hexagonrpcd || true)"
test -z "$(pgrep -f '^python3 .*/ssc-.*census' || true)"
test -z "$(pgrep -x drm-clock-probe15 || true)"
test -z "$(pgrep -x drm-clock-probe15b || true)"
test "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline
test "$(cat /sys/devices/platform/sensor-power/state)" = 'vdd=0 vddio=0'
test "$(cat /sys/class/remoteproc/remoteproc0/firmware)" = qcom/sm8150/realme/samurai/slpi.mdt
cmp /usr/local/bin/samurai-phosh-session /var/lib/samurai/k113-display-linear15/launcher-before-private.sh
echo ORIGINAL_LAUNCHER_MATCH > "$dest/launcher-restored.txt"
cat /sys/class/vtconsole/vtcon1/bind > "$dest/fbcon.txt"
cat /sys/class/remoteproc/remoteproc0/state > "$dest/slpi.txt"
cat /sys/devices/platform/sensor-power/state > "$dest/sensor-power.txt"
cat /sys/class/remoteproc/remoteproc0/firmware > "$dest/slpi-firmware.txt"
pgrep -u 10000 -x phoc > "$dest/phoc.txt"
pgrep -u 10000 -x phosh > "$dest/phosh.txt"
rc-service greetd status > "$dest/greetd-status.txt"
cat /sys/kernel/debug/dri/1/state > "$dest/drm-private.txt"
cat /sys/kernel/debug/dri/1/encoder-0/status > "$dest/encoder.txt"
cat /proc/asound/card0/pcm0p/sub0/status /proc/asound/card0/pcm1c/sub0/status > "$dest/pcm.txt"
cat /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status > "$dest/amps.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-check.txt"
sha256sum -c /var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256 > "$dest/source-check.txt"
cp /var/lib/samurai/k113-display-idle-restored15/result.json "$dest/idle-restoration.json"
ps -eo pid,comm,args > "$dest/processes-private.txt"
dmesg > "$dest/dmesg-after-private.txt"
cat /proc/uptime /proc/sys/kernel/tainted > "$dest/state-after.txt"
sync
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -czf /tmp/k113-wrap-up15.tar.gz .
sha256sum /tmp/k113-wrap-up15.tar.gz
echo CURRENT_BOOT_LOGS_DUMPS_PRESERVED_DIAGNOSTIC_TRACING_STOPPED_PHOSH_RETAINED
