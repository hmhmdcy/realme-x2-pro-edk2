#!/bin/sh
set -eu
umask 077
uname -v | grep -q '^#113 '
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k113-reboot-audio-clean-15/boot-id-private.txt)"
dest=/var/lib/samurai/k113-wrap-up15-trace-final
test ! -e "$dest"
mkdir -m700 "$dest"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
dmesg > "$dest/dmesg-before-private.txt"
for name in display radio display-clock15 display-clock15b display-linear15; do
    instance=/sys/kernel/tracing/instances/$name
    test -d "$instance"
    cat "$instance/tracing_on" > "$dest/$name-tracing-before.txt"
    cat "$instance/set_event" > "$dest/$name-events-before.txt"
    cat "$instance/events/dpu/dpu_enc_frame_done_timeout/trigger" > "$dest/$name-trigger-before.txt"
    echo 0 > "$instance/tracing_on"
    if test "$name" = display; then
        sha256sum "$instance/snapshot" | cut -d ' ' -f 1 > "$dest/display-snapshot-before.sha256"
        echo '!snapshot' > "$instance/events/dpu/dpu_enc_frame_done_timeout/trigger"
    fi
    echo 0 > "$instance/events/enable"
    cat "$instance/tracing_on" > "$dest/$name-tracing-after.txt"
    cat "$instance/set_event" > "$dest/$name-events-after.txt"
    cat "$instance/events/dpu/dpu_enc_frame_done_timeout/trigger" > "$dest/$name-trigger-after.txt"
    test "$(cat "$instance/tracing_on")" = 0
    test -z "$(cat "$instance/set_event")"
done
sha256sum /sys/kernel/tracing/instances/display/snapshot | cut -d ' ' -f 1 > "$dest/display-snapshot-after.sha256"
cmp "$dest/display-snapshot-before.sha256" "$dest/display-snapshot-after.sha256"
echo SNAPSHOT_BYTES_PRESERVED > "$dest/snapshot-preserved.txt"
for node in /sys/class/devcoredump/devcd*; do
    test -d "$node" || continue
    readlink -f "$node/failing_device" >> "$dest/devcoredump-sources.txt"
done
test "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline
test "$(cat /sys/devices/platform/sensor-power/state)" = 'vdd=0 vddio=0'
cat /sys/class/remoteproc/remoteproc0/state > "$dest/slpi.txt"
cat /sys/devices/platform/sensor-power/state > "$dest/sensor-power.txt"
pgrep -u 10000 -x phosh > "$dest/phosh.txt"
cat /proc/uptime /proc/sys/kernel/tainted > "$dest/state-after.txt"
dmesg > "$dest/dmesg-after-private.txt"
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -czf /tmp/k113-wrap-up15-trace-final.tar.gz .
sha256sum /tmp/k113-wrap-up15-trace-final.tar.gz
echo ALL_FIVE_TRACES_AND_EVENTS_DISABLED_ORIGINAL_SNAPSHOT_PRESERVED
