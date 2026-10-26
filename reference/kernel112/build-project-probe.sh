#!/bin/bash
set -euo pipefail
stage=/home/cy122/samurai-project-probe-k112
out=/mnt/e/edk2-samurai-out/kernel112
test ! -e "$stage"
mkdir "$stage"
cp '/mnt/e/RealmeX2Pro edk2/reference/kernel112/samurai_project_probe.c' "$stage/"
printf 'obj-m += samurai_project_probe.o\n' > "$stage/Makefile"
make -C /home/cy122/pmos-samurai-kernel112/kernel M="$stage" -j2 W=1 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- modules > "$out/project-probe-build.log" 2>&1
cp "$stage/samurai_project_probe.ko" "$out/"
aarch64-linux-gnu-strip --strip-debug "$out/samurai_project_probe.ko"
test "$(modinfo -F vermagic "$out/samurai_project_probe.ko")" = '7.3.0-rc6-rmx1931-samurai+ SMP preempt mod_unload aarch64'
test -z "$(modinfo -F intree "$out/samurai_project_probe.ko")"
sha256sum "$out/samurai_project_probe.ko" > "$out/project-probe.sha256"
echo READ_ONLY_PROJECT_PROBE_BUILT_WITH_NORMAL_EXTERNAL_MODULE_TAINT
