#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k119-pixel-validation
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat "$dest/boot-id-private.txt")"
test ! -e "$dest/validation.txt"
test "$(cat /proc/sys/kernel/tainted)" = 0
pgrep -x phosh >/dev/null
pgrep -x phoc >/dev/null
test -S /run/user/10000/wayland-0
test "$(stat -c %u /run/user/10000/wayland-0)" = 10000
sha256sum -c "$dest/binary.sha256" > "$dest/binary-before-check.txt"
dmesg > "$dest/dmesg-before.txt"
cat /proc/uptime > "$dest/uptime-before.txt"
set +e
timeout -s TERM -k 2 30 su -s /bin/sh cy122 -c 'ulimit -t 25; ulimit -v 786432; exec env XDG_RUNTIME_DIR=/run/user/10000 WAYLAND_DISPLAY=wayland-0 /tmp/k119-glmark2/usr/bin/glmark2-es2-wayland --off-screen --validate --data-path /tmp/k119-glmark2/usr/share/glmark2' > "$dest/validation.txt" 2>&1
result=$?
set -e
printf '%s\n' "$result" > "$dest/validation-exit.txt"
cat /proc/uptime > "$dest/uptime-after.txt"
dmesg > "$dest/dmesg-after.txt"
cat /proc/sys/kernel/tainted > "$dest/taint.txt"
pgrep -x phosh > "$dest/phosh.txt"
pgrep -x phoc > "$dest/phoc.txt"
if pgrep -f '^/tmp/k119-glmark2/usr/bin/glmark2-es2-wayland' > "$dest/remaining-processes.txt"; then
    echo BENCHMARK_PROCESS_REMAINS_STOP_AND_INSPECT
    exit 2
fi
sha256sum -c /var/lib/samurai/k119-benchmark-source/package-db-before.sha256 > "$dest/package-db-final-check.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-check.txt"
sha256sum -c /var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256 > "$dest/source-check.txt"
cat /proc/asound/card0/pcm0p/sub0/status /proc/asound/card0/pcm1c/sub0/status > "$dest/pcm.txt"
cat /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status > "$dest/amps.txt"
cd "$dest"
find . -type f ! -name SHA256SUMS -exec sha256sum {} \; > SHA256SUMS
tar -czf /tmp/k119-pixel-validation-private.tar.gz .
echo BOUNDED_NONROOT_GPU_PIXEL_VALIDATION_FINISHED_RESULT_REQUIRES_AUDIT
