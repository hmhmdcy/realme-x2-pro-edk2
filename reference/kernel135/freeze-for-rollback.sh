#!/bin/sh
set -eu
umask 077
test "$#" = 1
test "$(cat /proc/sys/kernel/random/boot_id)" = "$1"
uname -v | grep -q '^#134 '
before=/var/lib/samurai/k135-first-runtime
quiesce=/var/lib/samurai/k135-rollback-quiesce
test "$(cat "$before/boot-id-private.txt")" = "$1"
test "$(cat "$quiesce/boot-id-private.txt")" = "$1"
test "$(cat /proc/sys/kernel/tainted)" = 512
test "$(readlink -f /dev/dri/by-path/platform-ae01000.display-controller-card)" = /dev/dri/card1
test -z "$(pgrep -u 10000 || true)"
test -z "$(pgrep -x phosh || true)"
test -z "$(pgrep -x phoc || true)"
test -z "$(pidof wpa_supplicant || true)"
test -z "$(pidof ModemManager || true)"
test -z "$(pidof hexagonrpcd || true)"
test ! -e /proc/asound/card0
test "$(wc -l < /sys/kernel/debug/dri/1/clients)" = 1
test "$(grep -c 'active=1' /sys/kernel/debug/dri/1/state || true)" = 0
for number in 0 1 2; do test "$(cat /sys/class/remoteproc/remoteproc$number/state)" = offline; done
for name in display radio; do
 test "$(cat /sys/kernel/tracing/instances/$name/tracing_on)" = 0
done
test "$(cat /sys/devices/platform/sensor-power/state)" = 'vdd=0 vddio=0'
test "$(grep -c 'powered=0 muted=1' /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status | cut -d: -f2 | awk '{s+=$1} END {print s}')" = 2
sha256sum -c "$before/partition-check.sha256" > /run/k135-partition-check.txt
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > /run/k135-nv-check.txt
(cd /usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k134+ && sha256sum -c "/var/lib/samurai/k134-preflash/new-module-tree.sha256") > /run/k135-module-check.txt
(cd /usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k132+ && sha256sum -c /var/lib/samurai/k132-preflash/new-module-tree.sha256) > /run/k135-rollback132-target-module-check.txt
sync
echo QUIESCED > /run/k135-bootloader-state
fsfreeze -f /
echo FROZEN > /run/k135-bootloader-state
echo K135_F2FS_FROZEN_FOR_BOOTLOADER
