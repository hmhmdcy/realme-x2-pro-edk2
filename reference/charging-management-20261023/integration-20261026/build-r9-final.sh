#!/usr/bin/env bash
set -euo pipefail

base=/home/cy122/charging-management-20261023/charging-integration-20261026-01
localversion='-rmx1931-samurai-k363+'
cd "$base"

touch source/drivers/power/supply/bq27xxx_battery.c
make -C source O="$base/build" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- \
	LOCALVERSION="$localversion" \
	W=1 KCFLAGS=-Werror drivers/power/supply/bq27xxx_battery.o \
	2>&1 | tee r8-module/status-bq-object-r9-final.log

make -C source O="$base/build" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- \
	LOCALVERSION="$localversion" \
	-j8 Image 2>&1 | tee Image-build-status-precharge-r9-final.log

make -C source O="$base/build" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- \
	LOCALVERSION="$localversion" \
	M="$base/r8-module/kernel-module-source" clean
make -C source O="$base/build" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- \
	LOCALVERSION="$localversion" \
	M="$base/r8-module/kernel-module-source" -j8 modules \
	2>&1 | tee r8-module/final-r9-ko.log

aux="$base/../usb-input-irq-wake-r8-module-01/module"
make -C source O="$base/build" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- \
	LOCALVERSION="$localversion" M="$aux" clean
make -C source O="$base/build" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- \
	LOCALVERSION="$localversion" W=1 KCFLAGS=-Werror \
	M="$aux" -j8 modules \
	2>&1 | tee "$aux/../final-r9-aux-ko.log"

printf 'BASE=%s\n' "$base"
printf 'IMAGE_SHA256='; sha256sum build/arch/arm64/boot/Image | awk '{print $1}'
printf 'IMAGE_BYTES='; stat -c '%s' build/arch/arm64/boot/Image
printf 'VMLINUX_SHA256='; sha256sum build/vmlinux | awk '{print $1}'
printf 'SYSTEMMAP_SHA256='; sha256sum build/System.map | awk '{print $1}'
printf 'MODULE_SYMVERS_SHA256='; sha256sum build/Module.symvers | awk '{print $1}'
printf 'MODULE_SHA256='; sha256sum r8-module/kernel-module-source/samurai-mp2650.ko | awk '{print $1}'
printf 'MODULE_BYTES='; stat -c '%s' r8-module/kernel-module-source/samurai-mp2650.ko
printf 'MODULE_VERMAGIC='; modinfo -F vermagic r8-module/kernel-module-source/samurai-mp2650.ko
printf 'AUX_MODULE_SHA256='; sha256sum "$aux/samurai-usb-input.ko" | awk '{print $1}'
printf 'AUX_MODULE_BYTES='; stat -c '%s' "$aux/samurai-usb-input.ko"
printf 'AUX_MODULE_VERMAGIC='; modinfo -F vermagic "$aux/samurai-usb-input.ko"
printf 'KERNEL_VERSION='; make -s -C source O="$base/build" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- \
	LOCALVERSION="$localversion" kernelrelease
