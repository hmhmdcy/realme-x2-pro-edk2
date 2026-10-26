#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#109 SMP PREEMPT'
grep -q '^/dev/sda16 / f2fs rw' /proc/mounts
src=/var/lib/samurai/k111-sensor-sources-readonly
test -f "$src/firmware/slpi.mdt"
test -f "$src/sdsp/fastrpc_shell_2"
test -d "$src/sensors-persist/registry/registry"
test -d "$src/sensors-vendor/config"
sha256sum -c "$src/sources-before.sha256" > /run/k111-sensor-sources-still-unchanged.txt
dir=/var/lib/samurai/k111-modules-candidate
test ! -e "$dir"
mkdir -m700 "$dir"
tar -C "$dir" -xf /tmp/k111-sensor-modules.tar
(cd "$dir" && sha256sum -c SHA256SUMS) > /run/k111-module-package-check.txt
test -z "$(lsmod | awk '$1=="fastrpc" || $1=="qcom_socinfo" {print $1}')"
firmware=/lib/firmware/qcom/sm8150/realme/samurai
for file in "$src"/firmware/*; do
    test -f "$file"; test ! -L "$file"
    name=$(basename "$file")
    test ! -e "$firmware/$name"
    cp -p "$file" "$firmware/$name"
    cmp "$file" "$firmware/$name"
done
sync
echo SENSOR_FIRMWARE_AND_MODULES_STAGED_NO_DSP_STARTED
