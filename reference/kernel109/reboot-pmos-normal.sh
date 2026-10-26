#!/bin/sh
set -eu
test "$(cat /etc/samurai-rootfs-stage)" = kernel109
test -f /var/lib/samurai/k109-before-persistent-reboot-nv.txt
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k109-before-persistent-reboot-boot-id.txt)"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > /run/k109-final-nv-check.txt
sync
nohup /bin/sh -c 'sleep 2; exec /sbin/reboot' > /run/k109-normal-reboot.log 2>&1 < /dev/null &
echo NORMAL_OPENRC_PERSISTENT_REBOOT_REQUESTED
