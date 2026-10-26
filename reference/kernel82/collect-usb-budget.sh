#!/bin/sh
# Gadget descriptors are declarations, not verification of available VBUS current.
set -eu
[ "$(cat /proc/sys/kernel/random/boot_id)" = 87753933-4992-45d2-aaf5-d9db9c11d1a3 ]
[ ! -e /tmp/k82-usb-budget.txt ]
[ -f /sys/kernel/config/usb_gadget/samurai/configs/c.1/MaxPower ]
{
    cat /proc/uptime
    printf 'udc_state='; cat /sys/class/udc/a600000.usb/state
    printf 'udc_speed='; cat /sys/class/udc/a600000.usb/current_speed
    printf 'gadget_MaxPower_mA='; cat /sys/kernel/config/usb_gadget/samurai/configs/c.1/MaxPower
    printf 'gadget_bmAttributes='; cat /sys/kernel/config/usb_gadget/samurai/configs/c.1/bmAttributes
    printf 'typec_class_entries\n'; ls /sys/class/typec
    printf 'power_supply_class_entries\n'; ls /sys/class/power_supply
    printf 'udc_controller='; readlink -f /sys/class/udc/a600000.usb/device
} > /tmp/k82-usb-budget.txt
sha256sum /tmp/k82-usb-budget.txt > /tmp/k82-usb-budget-hashes.txt
cat /tmp/k82-usb-budget.txt
cat /tmp/k82-usb-budget-hashes.txt
