#!/bin/sh
set -eu
umask 077
uname -v | grep -q '^#113 '
checkpoint=/var/lib/samurai/k113-reboot-audio-clean-13
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat "$checkpoint/boot-id-private.txt")"
dest=/var/lib/samurai/k113-passive-after-v17-long-host-fetch
test ! -e "$dest"
mkdir -m700 "$dest"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
cat /proc/uptime /proc/sys/kernel/tainted > "$dest/state.txt"
dmesg > "$dest/dmesg.txt"
cat /sys/class/remoteproc/remoteproc0/state /sys/class/remoteproc/remoteproc0/firmware > "$dest/slpi.txt"
cat /sys/devices/platform/sensor-power/state > "$dest/sensor-power.txt"
rc-service greetd status > "$dest/greetd.txt"
ps -eo pid,user,args > "$dest/processes-private.txt"
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -cf /tmp/k113-passive-after-v17-long-host-fetch.tar .
sha256sum /tmp/k113-passive-after-v17-long-host-fetch.tar
echo PASSIVE_CURRENT_BOOT_AND_DISPLAY_LOG_CHECKPOINT_SAVED
