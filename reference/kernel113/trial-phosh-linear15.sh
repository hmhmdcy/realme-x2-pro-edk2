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
dest=/var/lib/samurai/k113-display-linear15
trace=/sys/kernel/tracing/instances/display-linear15
test ! -e "$dest" && test ! -e "$trace"
mkdir -m700 "$dest"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
cp -p /usr/local/bin/samurai-phosh-session "$dest/launcher-before-private.sh"
sha256sum /etc/greetd/samurai-phosh.toml > "$dest/greetd-before.sha256"
cat /proc/uptime /proc/sys/kernel/tainted > "$dest/state-before.txt"
dmesg > "$dest/dmesg-before.txt"
cat /sys/kernel/debug/dri/1/state > "$dest/drm-before.txt"
mkdir "$trace"
echo mono > "$trace/trace_clock"
echo 1024 > "$trace/buffer_size_kb"
for event in dpu_enc_frame_done_timeout dpu_enc_frame_watchdog dpu_enc_frame_done_cb dpu_enc_rc dpu_enc_rc_enable dpu_enc_rc_disable dpu_enc_phys_cmd_pp_tx_done dpu_enc_phys_cmd_pdone_timeout dpu_enc_prepare_kickoff_reset; do
    echo 1 > "$trace/events/dpu/$event/enable"
done
echo 'snapshot:1' > "$trace/events/dpu/dpu_enc_frame_done_timeout/trigger"
complete=0
cleanup() {
    echo 0 > "$trace/tracing_on" || true
    if test "$complete" = 0; then
        cp -p "$dest/launcher-before-private.sh" /usr/local/bin/samurai-phosh-session
        rc-service greetd stop >> "$dest/rollback.txt" 2>&1 || true
        if test -f /run/greetd.run; then mv /run/greetd.run "$dest/rollback-session-marker-private"; fi
        rc-service greetd start >> "$dest/rollback.txt" 2>&1 || true
        echo ORIGINAL_LAUNCHER_RESTORED_AFTER_INCOMPLETE_TRIAL >> "$dest/rollback.txt"
    fi
}
trap cleanup EXIT
python3 - <<'PY'
from pathlib import Path
p=Path('/usr/local/bin/samurai-phosh-session')
old=p.read_bytes()
assert old.startswith(b'#!/bin/sh\numask 077\n')
assert old.endswith(b'exec /usr/bin/phosh-session\n')
assert b'WLR_DRM_NO_MODIFIERS' not in old
p.write_bytes(old.replace(b'#!/bin/sh\n',b'#!/bin/sh\nexport WLR_DRM_NO_MODIFIERS=1\n',1))
PY
cp -p /usr/local/bin/samurai-phosh-session "$dest/launcher-trial-private.sh"
echo 1 > "$trace/tracing_on"
rc-service greetd stop > "$dest/greetd-stop.txt" 2>&1
sleep 2
test -z "$(pgrep -x phoc || true)"
mv /run/greetd.run "$dest/initial-session-marker-private"
rc-service greetd start > "$dest/greetd-start.txt" 2>&1
sleep 12
pgrep -u 10000 -x phoc > "$dest/phoc-after.txt"
pgrep -u 10000 -x phosh > "$dest/phosh-after.txt"
python3 - <<'PY'
from pathlib import Path
import subprocess
pids=subprocess.check_output(['pgrep','-u','10000','-x','phoc'],text=True).split()
assert len(pids)==1
values=(Path('/proc')/pids[0]/'environ').read_bytes().split(b'\0')
assert b'WLR_DRM_NO_MODIFIERS=1' in values
Path('/var/lib/samurai/k113-display-linear15/phoc-no-modifiers.txt').write_text('WLR_DRM_NO_MODIFIERS=1\n')
PY
for second in 0 10 30 60; do
    case "$second" in 0) ;; 10) sleep 10 ;; 30) sleep 20 ;; 60) sleep 30 ;; esac
    cat /proc/uptime > "$dest/uptime-$second.txt"
    cat /sys/kernel/debug/dri/1/state > "$dest/drm-$second.txt"
    cat /sys/kernel/debug/dri/1/encoder-0/status > "$dest/encoder-$second.txt"
    dmesg > "$dest/dmesg-$second.txt"
done
echo 0 > "$trace/tracing_on"
cat "$trace/trace" > "$dest/trace-private.txt"
cat "$trace/snapshot" > "$dest/snapshot-private.txt"
for stat in "$trace"/per_cpu/cpu*/stats; do cat "$stat" > "$dest/$(basename "$(dirname "$stat")")-stats.txt"; done
cp /home/cy122/.local/state/samurai-phosh-session.log "$dest/phosh-session-private.txt"
cat /sys/kernel/debug/clk/clk_summary > "$dest/clocks-private.txt"
sha256sum -c "$dest/greetd-before.sha256" > "$dest/greetd-unchanged.txt"
cat /proc/uptime /proc/sys/kernel/tainted > "$dest/state-after.txt"
cat /sys/class/remoteproc/remoteproc0/state > "$dest/slpi-after.txt"
cat /sys/devices/platform/sensor-power/state > "$dest/power-after.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-check.txt"
sha256sum -c /var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256 > "$dest/source-check.txt"
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -cf /tmp/k113-display-linear15.tar .
sha256sum /tmp/k113-display-linear15.tar
complete=1
echo PHOSH_NO_MODIFIERS_TRIAL_ARCHIVED_WITH_HARDWARE_RENDERER
