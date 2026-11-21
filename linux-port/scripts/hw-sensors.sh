#!/bin/sh
set -u
pw() { printf '12345678\n' | sudo -S -p '' "$@"; }

echo "== i2c clients and their drivers =="
for d in /sys/bus/i2c/devices/*; do
    case "$(basename "$d")" in i2c-*) continue;; esac
    name=$(cat "$d/name" 2>/dev/null || echo '?')
    if [ -e "$d/driver" ]; then
        drv=$(basename "$(readlink -f "$d/driver")")
    else
        drv='(unbound)'
    fi
    printf '%-10s name=%-24s driver=%s\n' "$(basename "$d")" "$name" "$drv"
done

echo
echo "== sensor-related modules available but not loaded =="
for m in bmi160 bmi260 lsm6dsl ak09918 st_lsm6dsx_bmc150 st_lsm6dsx_i2c \
         bmc150_accel_i2c bmc150_magn_i2c bmg160_i2c ltr501 ltrf216a \
         akm09911 stk3x1x tsl2771 vl6180x st_lsm6dsx_i2c; do
    if [ -e "/lib/modules/$(uname -r)/kernel/drivers/iio" ]; then
        ok=$(find "/lib/modules/$(uname -r)" -name "$m.ko*" 2>/dev/null | head -1)
        printf '%-20s %s\n' "$m" "${ok:-missing}"
    fi
done

echo
echo "== iio config in kernel =="
pw grep -iE '^CONFIG_(IIO|SENSORS_|.*ACCEL|.*MAGN|.*LIGHT|.*PROX)' \
    "/boot/config-$(uname -r)" 2>/dev/null | head -40

echo
echo "== all iio drivers that did attach =="
pw sh -c 'for d in /sys/bus/i2c/devices/*; do
  [ -e "$d/driver" ] || continue
  echo "$(basename "$d") -> $(basename "$(readlink -f "$d/driver")")"
done | grep -iE "iio|accel|magn|light|prox|lsm|bmi|ak" || true'
