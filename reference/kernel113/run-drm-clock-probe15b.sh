#!/bin/sh
set -eu
umask 077
uname -v | grep -q '^#113 '
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k113-reboot-audio-clean-15/boot-id-private.txt)"
test "$(cat /proc/sys/kernel/tainted)" = 512
test "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline
test "$(cat /sys/devices/platform/sensor-power/state)" = 'vdd=0 vddio=0'
test "$(cat /sys/class/vtconsole/vtcon1/bind)" = 0
test -n "$(pgrep -u 10000 -x phosh || true)"
test -f /run/greetd.run
test -s /var/lib/samurai/k113-display-trace15/SHA256SUMS
binary=/var/lib/samurai/k113-tools/drm-clock-probe15b
test "$(sha256sum "$binary" | cut -d ' ' -f 1)" = "$(cat /var/lib/samurai/k113-tools/drm-clock-probe15b.sha256)"
dest=/var/lib/samurai/k113-display-clock15b
trace=/sys/kernel/tracing/instances/display-clock15b
test ! -e "$dest" && test ! -e "$trace"
mkdir -m700 "$dest"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
cat /proc/uptime /proc/sys/kernel/tainted > "$dest/state-before.txt"
sha256sum /etc/greetd/samurai-phosh.toml > "$dest/greetd-before.sha256"
dmesg > "$dest/dmesg-before.txt"
restored=0
restore_gui() {
    if test "$restored" = 0; then
        if test -f /run/greetd.run; then mv /run/greetd.run "$dest/initial-session-marker-private"; fi
        rc-service greetd start >> "$dest/greetd-restore.txt" 2>&1 || true
        restored=1
    fi
}
trap 'echo 0 > "$trace/tracing_on" 2>/dev/null || true; restore_gui' EXIT
mkdir "$trace"
echo mono > "$trace/trace_clock"
echo 1024 > "$trace/buffer_size_kb"
for event in dpu_enc_frame_done_timeout dpu_enc_frame_watchdog dpu_enc_frame_done_cb dpu_enc_frame_done_cb_not_busy dpu_enc_rc dpu_enc_rc_enable dpu_enc_rc_disable dpu_enc_trigger_start dpu_enc_phys_cmd_pp_tx_done dpu_enc_irq_wait_success dpu_enc_wait_event_timeout dpu_crtc_frame_event_cb dpu_enc_phys_cmd_pdone_timeout dpu_enc_prepare_kickoff_reset; do
    echo 1 > "$trace/events/dpu/$event/enable"
done
echo 'snapshot:1' > "$trace/events/dpu/dpu_enc_frame_done_timeout/trigger"
rc-service greetd stop > "$dest/greetd-stop.txt" 2>&1
sleep 2
test -z "$(pgrep -x phoc || true)"
cat /sys/kernel/debug/dri/1/state > "$dest/drm-stopped.txt"
echo 1 > "$trace/tracing_on"
set +e
(cd "$dest" && timeout -s TERM -k 10 75 "$binary") > "$dest/probe.txt" 2>&1
result=$?
set -e
printf '%s\n' "$result" > "$dest/probe-exit.txt"
echo 0 > "$trace/tracing_on"
cat "$trace/trace" > "$dest/trace-private.txt"
cat "$trace/snapshot" > "$dest/snapshot-private.txt"
for stat in "$trace"/per_cpu/cpu*/stats; do cat "$stat" > "$dest/$(basename "$(dirname "$stat")")-stats.txt"; done
restore_gui
sleep 8
pgrep -u 10000 -x phoc > "$dest/phoc-after.txt"
pgrep -u 10000 -x phosh > "$dest/phosh-after.txt"
sha256sum -c "$dest/greetd-before.sha256" > "$dest/greetd-unchanged.txt"
dmesg > "$dest/dmesg-after.txt"
cat /proc/uptime /proc/sys/kernel/tainted > "$dest/state-after.txt"
cat /sys/class/vtconsole/vtcon1/bind > "$dest/fbcon-after.txt"
cat /sys/class/remoteproc/remoteproc0/state > "$dest/slpi-after.txt"
cat /sys/devices/platform/sensor-power/state > "$dest/power-after.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-check.txt"
sha256sum -c /var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256 > "$dest/source-check.txt"
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -cf /tmp/k113-display-clock15b.tar .
sha256sum /tmp/k113-display-clock15b.tar
echo BOUNDED_DRM_CLOCK_COMPARISON_ARCHIVED_AND_PHOSH_RESTORED
exit "$result"
