#!/bin/sh
set -eu
umask 077
uname -v | grep -q '^#113 '
dest=/var/lib/samurai/k113-audio-radio-quiesce-12
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k113-reboot-audio-clean-12/boot-id-private.txt)"
cmp "$dest/boot-id-private.txt" /var/lib/samurai/k113-reboot-audio-clean-12/boot-id-private.txt
test ! -e "$dest/SHA256SUMS"
test "$(cat /proc/sys/kernel/tainted)" = 0
test "$(cat "$dest/adsp-stop.txt")" = Terminated
for number in 0 1 2; do test "$(cat /sys/class/remoteproc/remoteproc$number/state)" = offline; done
test "$(cat /sys/devices/platform/sensor-power/state)" = 'vdd=0 vddio=0'
test -z "$(pgrep -u 10000 || true)"
test -z "$(pidof wpa_supplicant || true)"
test ! -e /sys/bus/platform/drivers/ath10k_snoc/18800000.wifi
for service in greetd chronyd networkmanager iio-sensor-proxy; do
    if rc-service "$service" status >/dev/null 2>&1; then exit 1; fi
done
# The native ADSP stop unregisters its sound card.  The pre-stop PCM statuses
# remain in pcm-idle.txt; missing post-stop status nodes are not PCM samples.
test ! -e /proc/asound/card0
test ! -e /sys/class/sound/card0
test ! -e /proc/asound/card0/pcm0p/sub0/status
test ! -e /proc/asound/card0/pcm1c/sub0/status
cat /proc/asound/cards > "$dest/soundcards-after-stop.txt"
grep -q '^--- no soundcards ---$' "$dest/soundcards-after-stop.txt"
echo CARD0_AND_PLAYBACK_CAPTURE_STATUS_NODES_ABSENT_AFTER_NATIVE_ADSP_STOP > "$dest/post-stop-audio-card-absent.txt"
for number in 0 1 2; do
    printf '%s ' "$number"
    tr '\n' ' ' < /sys/class/remoteproc/remoteproc$number/name
    cat /sys/class/remoteproc/remoteproc$number/state
done > "$dest/remoteproc-final-state.txt"
cat /sys/devices/platform/sensor-power/state > "$dest/sensor-power-final-state.txt"
cat /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status > "$dest/amps-final.txt"
test "$(grep -c 'powered=0 muted=1' "$dest/amps-final.txt")" = 2
echo 143 > "$dest/initial-adsp-stop-exit.txt"
echo INDEPENDENT_RECHECK_ALL_REMOTE_PROCESSORS_OFFLINE_AFTER_BOUNDED_STOP_INTERRUPTION > "$dest/finalization.txt"
cat /sys/class/remoteproc/remoteproc2/state > "$dest/adsp-final-state.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-check.txt"
sha256sum -c /var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256 > "$dest/source-check.txt"
cat /proc/uptime /proc/sys/kernel/tainted > "$dest/state.txt"
dmesg > "$dest/dmesg-after.txt"
sync
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -cf /tmp/k113-audio-radio-quiesce-12.tar .
sha256sum /tmp/k113-audio-radio-quiesce-12.tar
echo CURRENT_NATIVE_OFFLINE_STATE_AND_AUDIO_RADIO_CLEANUP_INDEPENDENTLY_VERIFIED
