#!/bin/sh
set -eu
umask 077
[ "$(cat /proc/sys/kernel/random/boot_id)" = 4cc1a6f8-d033-4608-bdd9-98e97a0df439 ]
grep -qx 'command=0x0036 status=0x00 payload=01000000' /tmp/k94-bt-info-ready.txt
grep -qx 'command=0x0004 status=0x11 payload=' /tmp/k94-bt-info-ready.txt
grep -q TWO_GHZ_AUTH_DHCP_PASS /tmp/k94-test-connectivity.log
/tmp/k94-bt-mgmt-probe test-address /tmp/k94-temp-bt-address.bin > /tmp/k94-bt-address.txt
for attempt in $(seq 1 30); do
    if /tmp/k94-bt-mgmt-probe info > /tmp/k94-bt-info-configured.txt; then break; fi
    sleep 1
done
grep -qx 'command=0x0003 status=0x00 payload=01000000' /tmp/k94-bt-info-configured.txt
grep -q '^command=0x0004 status=0x00 payload=' /tmp/k94-bt-info-configured.txt
/tmp/k94-bt-mgmt-probe configure > /tmp/k94-bt-configure.txt
/tmp/k94-bt-mgmt-probe info > /tmp/k94-bt-info-after.txt
echo BT_RUNTIME_CONFIGURED
/tmp/k94-nfc-controller-probe > /tmp/k94-nfc-controller.txt
echo NFC_CONTROLLER_PASS
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > /tmp/k94-nv-after-setup.txt
dmesg > /tmp/k94-after-setup-dmesg.txt
cat /sys/kernel/debug/dri/1/encoder-0/status > /tmp/k94-display-after-setup.txt
cat /sys/kernel/debug/dri/1/state > /tmp/k94-drm-after-setup.txt
cat /proc/sys/kernel/random/boot_id /proc/uptime /proc/sys/kernel/tainted
echo CONNECTIVITY_SETUP_PASS
