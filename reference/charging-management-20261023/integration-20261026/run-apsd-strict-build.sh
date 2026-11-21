#!/usr/bin/env bash
set -euo pipefail

root=/home/cy122/charging-management-20261023/charging-integration-20261026-01
src="$root/source/drivers/usb/typec/tcpm/qcom/qcom_pmic_typec_apsd.c"
obj="$root/build/drivers/usb/typec/tcpm/qcom/qcom_pmic_typec_apsd.o"
log="$root/apsd-strict-build-r1.log"

cd "$root"
touch "$src"
: >"$log"

set +e
make -C source O="$root/build" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- \
    LOCALVERSION=+ W=1 KCFLAGS=-Werror -j4 \
    drivers/usb/typec/tcpm/qcom/qcom_pmic_typec_apsd.o 2>&1 | tee "$log"
rc=${PIPESTATUS[0]}
set -e

printf 'STRICT_RC=%s\n' "$rc"
sha256sum "$obj"
exit "$rc"
