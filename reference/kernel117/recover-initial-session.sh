#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k117-initial-session-recovery
test ! -e "$dest"
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k115-final-health/boot-id-private.txt)"
test "$(cat /proc/sys/kernel/tainted)" = 0
test -c /dev/dri/card0
test -c /dev/dri/renderD128
test -L /sys/bus/mipi-dsi/devices/ae94000.dsi.0/driver
grep -qx '\[initial_session\]' /etc/greetd/samurai-phosh.toml
grep -qx 'command = "/usr/local/bin/samurai-phosh-session"' /etc/greetd/samurai-phosh.toml
grep -qx 'user = "cy122"' /etc/greetd/samurai-phosh.toml
if pgrep -x phosh; then echo PHOSH_ALREADY_RUNNING_ABORT;exit 1;fi
test -f /run/greetd.run
test "$(stat -c %s /run/greetd.run)" = 0
mkdir -m700 "$dest"
cp -p /run/greetd.run "$dest/greetd.run-before"
cp -p /etc/greetd/samurai-phosh.toml "$dest/config-before-private.toml"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
dmesg > "$dest/dmesg-before-private.txt"
timeout 20 rc-service greetd stop > "$dest/stop.out" 2> "$dest/stop.err"
for count in 1 2 3 4 5; do
    pgrep -x phoc >/dev/null || break
    sleep 1
done
if pgrep -x phoc; then echo GREETER_COMPOSITOR_NOT_RELEASED_ABORT;exit 1;fi
# Reset only the marker for the already configured initial session.
rm /run/greetd.run
timeout 20 rc-service greetd start > "$dest/start.out" 2> "$dest/start.err"
for count in 1 2 3 4 5 6 7 8 9 10; do
    pgrep -x phosh >/dev/null && break
    sleep 2
done
pgrep -x phosh > "$dest/phosh.txt" || true
pgrep -x phoc > "$dest/phoc.txt" || true
cat /proc/sys/kernel/tainted > "$dest/taint.txt"
cat /proc/asound/card0/pcm0p/sub0/status /proc/asound/card0/pcm1c/sub0/status > "$dest/pcm.txt"
cat /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status > "$dest/amps.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-check.txt"
sha256sum /etc/greetd/samurai-phosh.toml "$dest/config-before-private.toml" > "$dest/config.sha256"
dmesg > "$dest/dmesg-after-private.txt"
rc-status default > "$dest/services.txt"
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -czf /tmp/k117-initial-session-recovery-private.tar.gz .
sha256sum /tmp/k117-initial-session-recovery-private.tar.gz
echo EXISTING_INITIAL_SESSION_RESTART_EVIDENCE_SAVED
