#!/bin/sh
set -eu
umask 077
uname -v | grep -q '^#113 '
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k113-reboot-audio-clean-10/boot-id-private.txt)"
test "$(cat /proc/sys/kernel/tainted)" = 0
test "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline
test "$(cat /sys/devices/platform/sensor-power/state)" = 'vdd=0 vddio=0'
test "$(cat /sys/class/remoteproc/remoteproc0/firmware)" = qcom/sm8150/realme/samurai/slpi.mdt
echo 'f74a3534b76104d86aca6f50b5a94c2318d7d41aac7271427738c640e3ab99aa  /tmp/k113-c35-slpi-candidate-private.tar' | sha256sum -c - >/run/k113-c35-staging-check.txt
dest=/lib/firmware/qcom/sm8150/realme/samurai-c35-trial
test ! -e "$dest"
mkdir -m700 "$dest"
tar -C "$dest" -xf /tmp/k113-c35-slpi-candidate-private.tar
(cd "$dest" && sha256sum -c SHA256SUMS) >> /run/k113-c35-staging-check.txt
test -z "$(find "$dest" -type l -print)"
find "$dest" -type f -exec chmod 440 '{}' ';'
chmod 550 "$dest"
sync
echo C35_SLPI_SEPARATE_READONLY_FILES_STAGED_NO_DSP_STARTED
