#!/bin/sh
# Direct CDC NCM + public-key SSH for the diagnostic initramfs.
# No storage export, routing, EUD register writes, or charging controls.
set -eu
g=/sys/kernel/config/usb_gadget/samurai
udc_dir=${SAMURAI_UDC_DIR:-/sys/class/udc}
udc=
address=169.254.42.1
pidfile=/run/samurai-dropbear.pid

discover_udc() {
    if [ -n "${SAMURAI_UDC:-}" ]; then
        udc=$SAMURAI_UDC
        [ -e "$udc_dir/$udc" ] ||
            { echo "[usb] selected UDC unavailable: $udc" >&2; exit 1; }
        return
    fi
    if [ -e "$udc_dir/a600000.usb" ]; then
        udc=a600000.usb
        return
    fi
    selected=
    for candidate in "$udc_dir"/*; do
        [ -e "$candidate" ] || continue
        [ -z "$selected" ] ||
            { echo "[usb] multiple UDCs; set SAMURAI_UDC" >&2; exit 1; }
        selected=${candidate##*/}
    done
    [ -n "$selected" ] ||
        { echo "[usb] no UDC found in $udc_dir" >&2; exit 1; }
    udc=$selected
}

discover_udc

status() {
    cat "$udc_dir/$udc/state" "$udc_dir/$udc/current_speed"
    [ ! -d "$g" ] || cat "$g/UDC"
    ip addr show usb0
    [ ! -f "$pidfile" ] || cat "$pidfile"
}

case ${1:-start} in
discover) printf '%s\n' "$udc"; exit ;;
status) status; exit ;;
start) ;;
*) echo 'Usage: samurai-usb start|status|discover' >&2; exit 2 ;;
esac

mkdir -p /run /dev/pts /etc/dropbear
mkdir /run/samurai-usb.lock || { echo '[usb] another initializer owns the lock'; exit 1; }
trap 'rmdir /run/samurai-usb.lock' EXIT
if [ -f "$pidfile" ] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then
    echo '[usb] NCM/SSH already started'
    status
    exit
fi
count=0
while [ ! -e "$udc_dir/$udc" ]; do
    count=$((count + 1))
    [ "$count" -le 30 ] || { echo '[usb] UDC unavailable'; exit 1; }
    sleep 1
done
[ -d /sys/kernel/config/usb_gadget ] || mount -t configfs configfs /sys/kernel/config
if [ ! -e /dev/pts/ptmx ]; then mount -t devpts devpts /dev/pts; fi
if [ ! -d "$g" ]; then
    mkdir "$g"
    echo 0x0525 >"$g/idVendor"
    echo 0xa4a1 >"$g/idProduct"
    echo 0xef >"$g/bDeviceClass"
    echo 2 >"$g/bDeviceSubClass"
    echo 1 >"$g/bDeviceProtocol"
    mkdir "$g/strings/0x409"
    echo 62bc28a1 >"$g/strings/0x409/serialnumber"
    echo samurai >"$g/strings/0x409/manufacturer"
    echo SamuraiNCM >"$g/strings/0x409/product"
    mkdir "$g/configs/c.1"
    echo 500 >"$g/configs/c.1/MaxPower"
    mkdir "$g/functions/ncm.usb0"
    echo 02:62:bc:28:a1:01 >"$g/functions/ncm.usb0/dev_addr"
    echo 02:62:bc:28:a1:02 >"$g/functions/ncm.usb0/host_addr"
    ln -s "$g/functions/ncm.usb0" "$g/configs/c.1/ncm.usb0"
fi
test "$(cat "$g/idVendor")" = 0x0525
test "$(cat "$g/idProduct")" = 0xa4a1
test "$(cat "$g/strings/0x409/serialnumber")" = 62bc28a1
test -L "$g/configs/c.1/ncm.usb0"
# MaxPower is also consumed by composite_resume. Retire the old USB
# configuration before changing it, then let the host authorize the new one.
power=$(cat "$g/configs/c.1/MaxPower")
if [ "$power" != 500 ]; then
    bound=$(cat "$g/UDC")
    if [ -n "$bound" ]; then printf '\n' >"$g/UDC"; fi
    bound=$(cat "$g/UDC")
    test -z "$bound"
    echo 500 >"$g/configs/c.1/MaxPower"
    sleep 2
fi
bound=$(cat "$g/UDC")
if [ -z "$bound" ]; then echo "$udc" >"$g/UDC"; fi
bound=$(cat "$g/UDC")
test "$bound" = "$udc"
interface=$(cat "$g/functions/ncm.usb0/ifname")
ip link set "$interface" up
if ! ip -4 addr show dev "$interface" | grep -q "inet $address/16 "; then
    ip addr add "$address/16" dev "$interface"
fi
key=/etc/dropbear/dropbear_ed25519_host_key
if [ ! -f "$key" ]; then dropbearkey -t ed25519 -f "$key"; fi
chmod 600 "$key"
dropbear -E -s -j -k -p "$address:22" -r "$key" -P "$pidfile"
echo "[usb] CDC NCM $interface/$address with public-key SSH started"
