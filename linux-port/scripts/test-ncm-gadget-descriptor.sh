#!/bin/sh
# Create a standard configfs NCM gadget with the same descriptor and endpoint
# tuning as the known-good samurai gadget, without usb-signaller.
set -eu

CONFIGFS=/sys/kernel/config/usb_gadget
G=$CONFIGFS/signaltest
UDC_DIR=${SAMURAI_UDC_DIR:-/sys/class/udc}
UDC=${SAMURAI_UDC:-a600000.usb}
SERIAL=${SERIAL:-62bc28a1}
QMULT=${QMULT:-20}

rc-service samurai-usb-recover stop >/dev/null 2>&1 || true
rc-service usb-signaller stop >/dev/null 2>&1 || true
rc-service samurai-usb stop >/dev/null 2>&1 || true

for gadget in "$CONFIGFS"/*; do
	[ -d "$gadget" ] || continue
	printf '\n' >"$gadget/UDC" 2>/dev/null || true
done

if [ -e "$G" ]; then
	printf '\n' >"$G/UDC" 2>/dev/null || true
	for link in "$G"/configs/*/*; do
		[ -L "$link" ] && rm -f "$link"
	done
	for dir in "$G"/configs/*/strings/0x409 "$G"/configs/*/strings \
		"$G"/configs/* "$G"/functions/* "$G"/strings/0x409 "$G"/strings; do
		[ -d "$dir" ] && rmdir "$dir" 2>/dev/null || true
	done
	rmdir "$G" 2>/dev/null || true
fi

mkdir "$G"
echo 0x0525 >"$G/idVendor"
echo 0xa4a1 >"$G/idProduct"
echo 0xef >"$G/bDeviceClass"
echo 2 >"$G/bDeviceSubClass"
echo 1 >"$G/bDeviceProtocol"
echo 0x0201 >"$G/bcdUSB"
echo 0x0703 >"$G/bcdDevice"
mkdir "$G/strings/0x409"
echo "$SERIAL" >"$G/strings/0x409/serialnumber"
echo samurai >"$G/strings/0x409/manufacturer"
echo SamuraiNCM >"$G/strings/0x409/product"
mkdir "$G/configs/c.1"
mkdir "$G/configs/c.1/strings/0x409"
echo 500 >"$G/configs/c.1/MaxPower"
echo 0x80 >"$G/configs/c.1/bmAttributes"
echo SamuraiNCM >"$G/configs/c.1/strings/0x409/configuration"
mkdir "$G/functions/ncm.usb0"
echo "$QMULT" >"$G/functions/ncm.usb0/qmult"
echo "02:$SERIAL:01" >"$G/functions/ncm.usb0/dev_addr"
echo "02:$SERIAL:02" >"$G/functions/ncm.usb0/host_addr"
ln -s "$G/functions/ncm.usb0" "$G/configs/c.1/ncm.usb0"
echo "$UDC" >"$G/UDC"

count=0
while [ "$count" -lt 20 ]; do
	state=$(cat "$UDC_DIR/$UDC/state" 2>/dev/null || true)
	echo "state=$state"
	[ "$state" = configured ] && exit 0
	count=$((count + 1))
	sleep 1
done
exit 1
