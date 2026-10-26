#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k119-fbcon-quiesce
test ! -e "$dest"
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k119-preflash/boot-id-private.txt)"
test "$(cat /proc/sys/kernel/tainted)" = 0
test -z "$(pgrep -u 10000 || true)"
test -z "$(pgrep -x phosh || true)"
test -z "$(pgrep -x phoc || true)"
test "$(cat /sys/class/graphics/fb0/name)" = msmdrmfb
test "$(readlink -f /sys/class/graphics/fb0/device)" = /sys/devices/platform/soc@0/ae00000.display-subsystem/ae01000.display-controller
test "$(wc -l < /sys/kernel/debug/dri/0/clients)" = 1
grep -q 'allocated by = \[fbcon\]' /sys/kernel/debug/dri/0/state
mkdir -m700 "$dest"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
cat /sys/kernel/debug/dri/0/state > "$dest/drm-before.txt"
dmesg > "$dest/dmesg-before.txt"
timeout -s TERM -k 2 20 sh -c 'echo 4 > /sys/class/graphics/fb0/blank' > "$dest/blank.out" 2> "$dest/blank.err"
sleep 1
cat /sys/kernel/debug/dri/0/state > "$dest/drm-after.txt"
dmesg > "$dest/dmesg-after.txt"
test "$(grep -c 'active=1' "$dest/drm-after.txt" || true)" = 0
test "$(grep -c 'active=0' "$dest/drm-after.txt")" -gt 0
test "$(cat /proc/sys/kernel/tainted)" = 0
echo FBCON_BLANKED_NATIVE_CRTCS_INACTIVE
