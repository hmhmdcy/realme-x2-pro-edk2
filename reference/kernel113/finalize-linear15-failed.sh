#!/bin/sh
set -eu
umask 077
uname -v | grep -q '^#113 '
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k113-reboot-audio-clean-15/boot-id-private.txt)"
dest=/var/lib/samurai/k113-display-linear15
test -s "$dest/rollback.txt" && test ! -e "$dest/SHA256SUMS"
grep -q ORIGINAL_LAUNCHER_RESTORED_AFTER_INCOMPLETE_TRIAL "$dest/rollback.txt"
test ! -e "$dest/phoc-no-modifiers.txt"
cmp "$dest/launcher-before-private.sh" /usr/local/bin/samurai-phosh-session
echo ORIGINAL_LAUNCHER_MATCH > "$dest/launcher-restored.txt"
echo 1 > "$dest/trial-exit.txt"
echo NO_MODIFIERS_ENVIRONMENT_NOT_CONFIRMED_TRIAL_INCOMPLETE > "$dest/result.txt"
cat /sys/kernel/tracing/instances/display-linear15/trace > "$dest/trace-private.txt"
cat /sys/kernel/tracing/instances/display-linear15/snapshot > "$dest/snapshot-private.txt"
cat /sys/kernel/tracing/instances/display-linear15/tracing_on > "$dest/tracing-on.txt"
cat /sys/kernel/debug/dri/1/state > "$dest/drm-after-rollback.txt"
cat /proc/uptime /proc/sys/kernel/tainted > "$dest/state-after-rollback.txt"
dmesg > "$dest/dmesg-after-rollback.txt"
pgrep -u 10000 -x phoc > "$dest/phoc-after-rollback.txt"
pgrep -u 10000 -x phosh > "$dest/phosh-after-rollback.txt"
cat /sys/class/remoteproc/remoteproc0/state > "$dest/slpi-after.txt"
cat /sys/devices/platform/sensor-power/state > "$dest/power-after.txt"
sha256sum -c "$dest/greetd-before.sha256" > "$dest/greetd-unchanged.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-check.txt"
sha256sum -c /var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256 > "$dest/source-check.txt"
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -cf /tmp/k113-display-linear15-failed.tar .
sha256sum /tmp/k113-display-linear15-failed.tar
echo INCOMPLETE_NO_MODIFIERS_TRIAL_ARCHIVED_WITH_ROLLBACK_PROOF
