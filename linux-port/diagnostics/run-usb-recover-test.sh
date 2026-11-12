#!/bin/sh
set -eu

truncate -s 0 /root/test-samurai-usb-recover.log
truncate -s 0 /root/test-samurai-usb-recover.out
mkdir -p /run/test-samurai-usb-recover
printf '0\n' >/run/test-samurai-usb-recover/attempts
printf '0\n' >/run/test-samurai-usb-recover/armed
printf '1\n' >/run/test-samurai-usb-recover/online

SAMURAI_USB_RECOVER_GRACE=4 \
SAMURAI_USB_RECOVER_INTERVAL=1 \
SAMURAI_USB_RECOVER_MAX=2 \
SAMURAI_USB_RECOVER_RUN_DIR=/run/test-samurai-usb-recover \
SAMURAI_USB_RECOVER_LOG=/root/test-samurai-usb-recover.log \
nohup /root/samurai-usb-recover-test monitor \
	>/root/test-samurai-usb-recover.out 2>&1 &

sleep 3
echo MONITOR_PID=$!
cat /root/test-samurai-usb-recover.log
