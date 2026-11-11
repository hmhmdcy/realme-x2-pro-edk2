#!/bin/sh
# SPDX-License-Identifier: BSD-3-Clause
#
# Resolve the USB2 dual-role Kconfig candidate without building an Image.

set -eu

kernel_root=${1:-/home/cy122/standard-arm64-v7.3.1}
base_config=${2:-/home/cy122/samurai-v731-build/.config}
fragment=${3:-"$(dirname "$0")/../configs/v7.3.1/usb2-typec-dual.fragment"}
output_dir=${4:-/mnt/e/edk2-samurai-out/standard-arm64-v731/usb-typec-20261110/config-candidate}
config_build_dir=${5:-/home/cy122/samurai-v731-usb-dual-config}
cross_compile=${CROSS_COMPILE:-aarch64-linux-gnu-}

for path in "$kernel_root" "$base_config" "$fragment"; do
	if [ ! -e "$path" ]; then
		echo "missing input: $path" >&2
		exit 1
	fi
done

mkdir -p "$output_dir" "$config_build_dir"
cp "$base_config" "$output_dir/base.config"
cp "$fragment" "$output_dir/usb2-typec-dual.fragment"

"$kernel_root/scripts/kconfig/merge_config.sh" -m \
	-O "$output_dir" \
	"$output_dir/base.config" \
	"$output_dir/usb2-typec-dual.fragment" \
	>"$output_dir/merge.stdout" 2>"$output_dir/merge.stderr"

make -s -C "$kernel_root" \
	ARCH=arm64 \
	CROSS_COMPILE="$cross_compile" \
	O="$config_build_dir" \
	KCONFIG_CONFIG="$output_dir/.config" \
	olddefconfig \
	>"$output_dir/olddefconfig.stdout" \
	2>"$output_dir/olddefconfig.stderr"

cp "$output_dir/.config" "$output_dir/resolved.config"
sha256sum "$output_dir/resolved.config" >"$output_dir/resolved.config.sha256"
python3 "$kernel_root/scripts/diffconfig" \
	"$output_dir/base.config" \
	"$output_dir/resolved.config" \
	>"$output_dir/diffconfig.txt"

required='CONFIG_ARM64=y
CONFIG_USB_DWC3_DUAL_ROLE=y
CONFIG_USB_ROLE_SWITCH=y
CONFIG_USB_XHCI_HCD=y
CONFIG_USB_XHCI_PLATFORM=y
CONFIG_TYPEC_QCOM_PMIC=y
CONFIG_REGULATOR_QCOM_USB_VBUS=y'

printf '%s\n' "$required" >"$output_dir/usb-options.txt"
if ! grep -Fqx "$required" "$output_dir/resolved.config"; then
	echo "resolved config failed required USB options:" >&2
	printf '%s\n' "$required" >&2
	exit 1
fi
if grep -q '^CONFIG_X86=y$' "$output_dir/resolved.config"; then
	echo "resolved config unexpectedly selected x86" >&2
	exit 1
fi

echo "RESULT: USB2 dual-role config candidate resolved"
echo "config=$output_dir/resolved.config"
cat "$output_dir/resolved.config.sha256"
