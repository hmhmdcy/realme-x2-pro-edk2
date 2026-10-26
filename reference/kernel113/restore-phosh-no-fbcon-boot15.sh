#!/bin/sh
set -eu
umask 077
uname -v | grep -q '^#113 '
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k113-reboot-audio-clean-15/boot-id-private.txt)"
test "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline
test "$(cat /sys/devices/platform/sensor-power/state)" = 'vdd=0 vddio=0'
test -f /var/lib/samurai/k113-display-session-reset-boot15/SHA256SUMS
test "$(cat /sys/class/vtconsole/vtcon1/name)" = '(M) frame buffer device'
test "$(cat /sys/class/vtconsole/vtcon1/bind)" = 1
test -f /run/greetd.run && test ! -L /run/greetd.run
dest=/var/lib/samurai/k113-display-no-fbcon-boot15
test ! -e "$dest"
mkdir -m700 "$dest"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
cat /proc/uptime /proc/sys/kernel/tainted > "$dest/state-before.txt"
sha256sum /etc/greetd/samurai-phosh.toml > "$dest/config-before.sha256"
dmesg > "$dest/dmesg-before.txt"
cat /sys/class/vtconsole/vtcon1/name /sys/class/vtconsole/vtcon1/bind > "$dest/fbcon-before.txt"
set +e
timeout -s TERM -k 2 10 sh -c 'echo 0 > /sys/class/vtconsole/vtcon1/bind' > "$dest/fbcon-unbind.txt" 2>&1
code=$?
set -e
printf '%s\n' "$code" > "$dest/fbcon-unbind-exit.txt"
test "$code" = 0 && test "$(cat /sys/class/vtconsole/vtcon1/bind)" = 0
rc-service greetd stop > "$dest/greetd-stop.txt" 2>&1
sleep 2
ps -eo pid,user,args > "$dest/processes-stopped-private.txt"
mv /run/greetd.run "$dest/initial-session-marker-private"
test ! -e /run/greetd.run
rc-service greetd start > "$dest/greetd-start.txt" 2>&1
sleep 10
rc-service greetd status > "$dest/greetd-status.txt"
ps -eo pid,user,args > "$dest/processes-after-private.txt"
test -n "$(pgrep -u 10000 phoc || true)"
test -n "$(pgrep -u 10000 phosh || true)"
test -f /run/greetd.run
cat /sys/class/vtconsole/vtcon1/bind > "$dest/fbcon-after.txt"
cat /proc/uptime /proc/sys/kernel/tainted > "$dest/state-after.txt"
sha256sum /etc/greetd/samurai-phosh.toml > "$dest/config-after.sha256"
cmp "$dest/config-before.sha256" "$dest/config-after.sha256"
dmesg > "$dest/dmesg-after.txt"
cat /sys/class/remoteproc/remoteproc0/state > "$dest/slpi-after.txt"
cat /sys/devices/platform/sensor-power/state > "$dest/power-after.txt"
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -cf /tmp/k113-display-no-fbcon-boot15.tar .
sha256sum /tmp/k113-display-no-fbcon-boot15.tar
echo PHOSH_ORIGINAL_INITIAL_SESSION_RESTORED_FBCON_UNBOUND_CURRENT_BOOT_ONLY
