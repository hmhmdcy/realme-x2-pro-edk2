#!/bin/sh
set -eu
umask 077
before=/var/lib/samurai/k143-first-runtime
dest=/var/lib/samurai/k143-rollback-quiesce
uname -v | grep -q '^#143 '
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat "$before/boot-id-private.txt")"
test "$(cat /proc/sys/kernel/tainted)" = 0
test "$(readlink -f /dev/dri/by-path/platform-ae01000.display-controller-card)" = /dev/dri/card1
test "$(uname -r)" = 7.3.0-rc6-rmx1931-samurai-k132+
test ! -e "$dest"
mkdir -m700 "$dest"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
dmesg > "$dest/dmesg-before.txt"
for name in display radio; do
 path=/sys/kernel/tracing/instances/$name
 echo 0 > "$path/tracing_on"
 timeout -k 2 10 cat "$path/trace" > "$dest/$name-trace-private.txt"
 test "$(cat "$path/tracing_on")" = 0
done
if test -d /sys/module/qcom_camss; then
 test "$(cat /sys/module/qcom_camss/parameters/dma_trace)" = N
 rmmod qcom_camss
 test ! -e /dev/media0
fi
test ! -d /sys/module/qcom_camss
for service in bluetooth greetd chronyd networkmanager iio-sensor-proxy nfcd neard; do
 if rc-service "$service" status >/dev/null 2>&1; then timeout -s TERM -k 2 25 rc-service "$service" stop >> "$dest/services.txt" 2>&1; fi
done
for pid in $(pgrep -u 10000 || true); do kill -TERM "$pid" 2>/dev/null || true; done
sleep 2
for pid in $(pgrep -u 10000 || true); do kill -KILL "$pid" 2>/dev/null || true; done
test -z "$(pgrep -u 10000 || true)"
test -z "$(pgrep -x phosh || true)"
test -z "$(pgrep -x phoc || true)"
if rc-service elogind status >/dev/null 2>&1; then timeout -s TERM -k 2 25 rc-service elogind stop >> "$dest/services.txt" 2>&1; fi
cat /sys/kernel/debug/dri/1/clients > "$dest/drm-clients-after-gui.txt"
test "$(wc -l < "$dest/drm-clients-after-gui.txt")" = 1
cat /sys/kernel/debug/dri/1/state > "$dest/drm-before-blank.txt"
if test "$(grep -c 'active=1' "$dest/drm-before-blank.txt" || true)" != 0; then
 test "$(cat /sys/class/graphics/fb0/name)" = msmdrmfb
 test "$(readlink -f /sys/class/graphics/fb0/device)" = /sys/devices/platform/soc@0/ae00000.display-subsystem/ae01000.display-controller
 grep -q 'allocated by = \[fbcon\]' "$dest/drm-before-blank.txt"
 timeout -s TERM -k 2 20 sh -c 'echo 4 > /sys/class/graphics/fb0/blank' > "$dest/fbcon-blank.txt" 2>&1
 sleep 1
fi
cat /sys/kernel/debug/dri/1/state > "$dest/drm-final-state.txt"
test "$(grep -c 'active=1' "$dest/drm-final-state.txt" || true)" = 0
test "$(grep -c 'active=0' "$dest/drm-final-state.txt")" -gt 0
dmesg > "$dest/dmesg-at-blank.txt"
echo K143_REJECTED143_DESKTOP_QUIESCED
