#!/bin/sh
set -eu
umask 077
uname -v | grep -q '^#129 '
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k130-quiesce/boot-id-private.txt)"
test "$(cat /proc/sys/kernel/tainted)" = 0
test "$(cat /sys/devices/platform/sensor-power/state)" = 'vdd=0 vddio=0'
test -z "$(pgrep -u 10000 || true)"
test -z "$(pgrep -x bluetoothd || true)"
test ! -e /proc/asound/card0
for number in 0 1 2; do test "$(cat /sys/class/remoteproc/remoteproc$number/state)" = offline; done
test -f /var/lib/samurai/k130-quiesce/SHA256SUMS
test "$(readlink /etc/runlevels/default/bluetooth)" = /etc/init.d/bluetooth
test ! -e /var/lib/samurai/k130-normal-reboot-requested
sync
echo REQUESTED > /var/lib/samurai/k130-normal-reboot-requested
sync
nohup /bin/sh -c 'sleep 2; exec /sbin/reboot' > /run/k130-normal-reboot-private.log 2>&1 < /dev/null &
echo K130_QUIESCED_NORMAL_OPENRC_WARM_REBOOT_REQUESTED
