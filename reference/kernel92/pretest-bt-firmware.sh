#!/bin/sh
set -eu
umask 077
[ "$(cat /proc/sys/kernel/random/boot_id)" = 7198e2c9-17e4-42af-ac12-71a2013b5ea8 ]
dmesg | grep -q 'QCA SOC Version  :0x40010224'
dmesg | grep -q 'QCA ROM Version  :0x00001001'
test -e /sys/bus/serial/drivers/hci_uart_qca/serial0-0
sha256sum /lib/firmware/qca/crbtfw21.tlv /lib/firmware/qca/crnv21.bin > /tmp/k92-bt-stock-selected-sha.txt
grep -q '^46a09f53f93c4e6e0d03cac8e69b3653216b2f1df86de0dbed62fc003e61a6f7 ' /tmp/k92-bt-stock-selected-sha.txt
mkdir -p /run/samurai-wifi/firmware/qca
test ! -e /run/samurai-wifi/firmware/qca/crbtfw01.tlv
cp /lib/firmware/qca/crbtfw21.tlv /run/samurai-wifi/firmware/qca/crbtfw01.tlv
cp /lib/firmware/qca/crnv21.bin /run/samurai-wifi/firmware/qca/crnv01.bin
cmp /lib/firmware/qca/crbtfw21.tlv /run/samurai-wifi/firmware/qca/crbtfw01.tlv
cmp /lib/firmware/qca/crnv21.bin /run/samurai-wifi/firmware/qca/crnv01.bin
echo serial0-0 > /sys/bus/serial/drivers/hci_uart_qca/unbind
echo serial0-0 > /sys/bus/serial/drivers/hci_uart_qca/bind
sleep 5
/tmp/bt-mgmt-probe3 configure
