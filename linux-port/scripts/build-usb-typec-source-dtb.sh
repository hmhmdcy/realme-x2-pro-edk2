#!/bin/sh
#
# Build a compact source-level USB Type-C DTB for RMX1931.
#
set -eu

KERNEL_ROOT=${KERNEL_ROOT:-/home/cy122/standard-arm64-v7.3.1}
BUILD_ROOT=${BUILD_ROOT:-/home/cy122/samurai-v731-build}
OUTPUT_DIR=${1:?usage: build-usb-typec-source-dtb.sh OUTPUT_DIR}
PROFILE=${2:-sink}
WRAPPER=${3:-linux-port/dts/experiments/sm8150-samurai-usb-typec-${PROFILE}.dts}

QCOM=${KERNEL_ROOT}/arch/arm64/boot/dts/qcom
INCLUDE=${KERNEL_ROOT}/scripts/dtc/include-prefixes
DTC=${BUILD_ROOT}/scripts/dtc/dtc
EXPERIMENTS=linux-port/dts/experiments

test -x "${DTC}"
test -f "${WRAPPER}"
mkdir -p "${OUTPUT_DIR}"

gcc -E -Wp,-MMD,"${OUTPUT_DIR}/${PROFILE}.pre.tmp" \
	-nostdinc -I "${QCOM}" -I "${INCLUDE}" -undef -D__DTS__ \
	-x assembler-with-cpp -o "${OUTPUT_DIR}/${PROFILE}.dts.tmp" \
	"${WRAPPER}"

"${DTC}" -o "${OUTPUT_DIR}/sm8150-samurai-usb-typec-${PROFILE}.dtb" \
	-b 0 -i "${EXPERIMENTS}" -i "${QCOM}" -i "${INCLUDE}" \
	-Wno-unique_unit_address -Wno-unit_address_vs_reg \
	-Wno-avoid_unnecessary_addr_size -Wno-alias_paths \
	-Wno-interrupt_map -Wno-simple_bus_reg \
	"${OUTPUT_DIR}/${PROFILE}.dts.tmp" \
	2>"${OUTPUT_DIR}/dtc.stderr"

wc -c "${OUTPUT_DIR}/sm8150-samurai-usb-typec-${PROFILE}.dtb"
sha256sum "${OUTPUT_DIR}/sm8150-samurai-usb-typec-${PROFILE}.dtb"
