#!/bin/sh
set -eu
umask 077
[ "$(cat /proc/sys/kernel/random/boot_id)" = 4cc1a6f8-d033-4608-bdd9-98e97a0df439 ]
uname -a | grep -q '#93 SMP PREEMPT'
for attempt in $(seq 1 90); do
    test -e /run/samurai-wifi/ready && break
    sleep 1
done
test -e /run/samurai-wifi/ready
[ "$(cat /sys/class/remoteproc/remoteproc0/state)" = running ]
echo FIRST_MPSS_START_STABLE
cli() { /usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 "$@"; }
cp /tmp/k94-wpa-private.conf /run/samurai-wifi/wpa.conf
cli reconfigure | grep -qx OK
for attempt in $(seq 1 30); do
    cli status > /tmp/k94-2ghz-status.txt
    if grep -qx wpa_state=COMPLETED /tmp/k94-2ghz-status.txt && grep -qx freq=2462 /tmp/k94-2ghz-status.txt; then break; fi
    sleep 2
done
grep -qx wpa_state=COMPLETED /tmp/k94-2ghz-status.txt
grep -qx freq=2462 /tmp/k94-2ghz-status.txt
udhcpc -i wlan0 -s /usr/sbin/samurai-udhcpc-wlan -n -q -t 5 -T 3 > /tmp/k94-2ghz-dhcp.txt 2>&1
echo TWO_GHZ_AUTH_DHCP_PASS
for attempt in $(seq 1 120); do
    grep -q BT_DRIVER_REGISTERED /run/samurai-bluetooth-boot.log && break
    sleep 1
done
grep -q BT_DRIVER_REGISTERED /run/samurai-bluetooth-boot.log
# READ_INFO rejects an unconfigured controller. Wait for its actual index
# in READ_UNCONF_INDEX_LIST instead of treating that status as setup failure.
for attempt in $(seq 1 30); do
    if /tmp/k94-bt-mgmt-probe info > /tmp/k94-bt-info-before.txt; then break; fi
    if grep -qx 'command=0x0036 status=0x00 payload=01000000' /tmp/k94-bt-info-before.txt &&
       grep -qx 'command=0x0004 status=0x11 payload=' /tmp/k94-bt-info-before.txt; then break; fi
    sleep 1
done
grep -qx 'command=0x0036 status=0x00 payload=01000000' /tmp/k94-bt-info-before.txt
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
