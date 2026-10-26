#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k134-original-initial-session
test ! -e "$dest"
test "$(uname -r)" = 7.3.0-rc6-rmx1931-samurai-k134+
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k134-panel-reprobe-once/boot-id-private.txt)"
test "$(cat /proc/sys/kernel/tainted)" = 0
test "$(readlink -f /dev/dri/by-path/platform-ae01000.display-controller-card)" = /dev/dri/card0
test -f /run/greetd.run && test ! -L /run/greetd.run && test ! -s /run/greetd.run
mkdir -m700 "$dest"
sha256sum /etc/greetd/samurai-phosh.toml /usr/local/bin/samurai-phosh-session > "$dest/config-before.sha256"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
dmesg > "$dest/dmesg-before-private.txt"
if test -e /sys/class/vtconsole/vtcon1/bind; then
    cat /sys/class/vtconsole/vtcon1/name /sys/class/vtconsole/vtcon1/bind > "$dest/fbcon-before.txt"
    if test "$(cat /sys/class/vtconsole/vtcon1/name)" = '(M) frame buffer device' && test "$(cat /sys/class/vtconsole/vtcon1/bind)" = 1; then
        timeout -s TERM -k 2 10 sh -c 'echo 0 > /sys/class/vtconsole/vtcon1/bind' > "$dest/fbcon-unbind.txt" 2>&1
        test "$(cat /sys/class/vtconsole/vtcon1/bind)" = 0
    fi
fi
rc-service greetd stop > "$dest/greetd-stop.txt" 2>&1
sleep 2
test -z "$(pgrep -x phoc || true)"
mv /run/greetd.run "$dest/initial-session-marker-private"
rc-service greetd start > "$dest/greetd-start.txt" 2>&1
sleep 12
pgrep -x phosh > "$dest/phosh.txt"
pgrep -x phoc > "$dest/phoc.txt"
cat /proc/sys/kernel/tainted > "$dest/final-taint.txt"
sha256sum -c "$dest/config-before.sha256" > "$dest/config-final-check.txt"
dmesg > "$dest/dmesg-after-private.txt"
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -czf /tmp/k134-initial-session-private.tar.gz .
echo K134_ORIGINAL_UNCHANGED_CONFIG_PHOSH_INITIAL_SESSION_RESTORED
