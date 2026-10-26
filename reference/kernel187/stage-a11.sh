#!/bin/sh
set -eu
umask 077
uname -v | grep -q '^#183 '
cmp /proc/sys/kernel/random/boot_id /var/lib/samurai/k186-reboot-runtime-r2/boot-id-private.txt
test "$(cat /proc/sys/kernel/tainted)" = 0
test "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline
test "$(cat /sys/devices/platform/sensor-power/state)" = 'vdd=0 vddio=0'
test "$(cat /sys/class/remoteproc/remoteproc0/firmware)" = qcom/sm8150/realme/samurai/slpi.mdt
dest=/lib/firmware/qcom/sm8150/realme/samurai-a11-r187
test ! -e "$dest"
echo 'ecf83aaf1143b7f55657fed051e12e2375859f052f84f60e5ad10a17dd143712  /tmp/k187-a11-slpi-candidate-private.tar' | sha256sum -c - >/run/k187-staging-private.txt
mkdir -m700 "$dest"
tar -C "$dest" -xf /tmp/k187-a11-slpi-candidate-private.tar
(cd "$dest" && sha256sum -c SHA256SUMS) >>/run/k187-staging-private.txt
test -z "$(find "$dest" -type l -print)"
find "$dest" -type f -exec chmod 440 '{}' ';'
chmod 550 "$dest"
sync
echo A11_SEPARATE_FILES_STAGED_NO_DSP_START
