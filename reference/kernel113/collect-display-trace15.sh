#!/bin/sh
set -eu
umask 077
uname -v | grep -q '^#113 '
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k113-reboot-audio-clean-15/boot-id-private.txt)"
test "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline
test "$(cat /sys/devices/platform/sensor-power/state)" = 'vdd=0 vddio=0'
dest=/var/lib/samurai/k113-display-trace15
trace=/sys/kernel/tracing/instances/display
test ! -e "$dest"
mkdir -m700 "$dest"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
uname -a > "$dest/uname.txt"
cat /proc/uptime /proc/sys/kernel/tainted > "$dest/state.txt"
for name in tracing_on trace_clock buffer_size_kb current_tracer set_event; do
    cat "$trace/$name" > "$dest/$name.txt"
done
for name in trace snapshot; do
    set +e
    timeout -s TERM -k 2 12 cat "$trace/$name" > "$dest/$name.txt"
    printf '%s\n' "$?" > "$dest/$name-exit.txt"
    set -e
done
cat "$trace/events/dpu/dpu_enc_frame_done_timeout/trigger" > "$dest/timeout-trigger.txt"
cat "$trace/events/dpu/dpu_enc_frame_watchdog/enable" > "$dest/watchdog-enable.txt"
for stat in "$trace"/per_cpu/cpu*/stats; do
    cat "$stat" > "$dest/$(basename "$(dirname "$stat")")-stats.txt"
done
cat /sys/kernel/debug/dri/1/encoder-0/status > "$dest/encoder.txt"
cat /sys/kernel/debug/dri/1/state > "$dest/drm-state.txt"
cat /proc/interrupts > "$dest/interrupts.txt"
dmesg > "$dest/dmesg.txt"
cat /sys/class/remoteproc/remoteproc0/state > "$dest/slpi.txt"
cat /sys/devices/platform/sensor-power/state > "$dest/power.txt"
cat /sys/class/vtconsole/vtcon1/bind > "$dest/fbcon.txt"
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -cf /tmp/k113-display-trace15.tar .
sha256sum /tmp/k113-display-trace15.tar
echo DISPLAY_EXISTING_TRACE_AND_SNAPSHOT_PRESERVED_READ_ONLY
