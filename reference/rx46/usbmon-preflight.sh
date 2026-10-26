#!/bin/bash
set -euo pipefail
test "$(id -u)" = 0
modprobe usbmon
if ! mountpoint -q /sys/kernel/debug; then
    mount -t debugfs none /sys/kernel/debug
fi
test -r /sys/kernel/debug/usb/usbmon/0u
python3 -c 'import usb.core; print("PyUSB and usbmon ready")'
