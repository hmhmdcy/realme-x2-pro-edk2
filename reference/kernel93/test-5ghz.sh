#!/bin/sh
set -eu
umask 077
[ "$(cat /proc/sys/kernel/random/boot_id)" = b65a234f-44f4-4ad3-9d40-ecafdeb233b1 ]
cli()
{
    /usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 "$@"
}
cli list_networks > /tmp/k93-5ghz-network-before.txt
grep -q '^0[[:space:]]*TP-LINK_156D' /tmp/k93-5ghz-network-before.txt
cli status > /tmp/k93-5ghz-status-before.txt
grep -qx wpa_state=COMPLETED /tmp/k93-5ghz-status-before.txt
cli set_network 0 freq_list 5180 | grep -qx OK
cli select_network 0 | grep -qx OK
cli reassociate | grep -qx OK
success=0
for attempt in $(seq 1 20); do
    cli status > /tmp/k93-5ghz-current-status.txt
    if grep -qx wpa_state=COMPLETED /tmp/k93-5ghz-current-status.txt && grep -qx freq=5180 /tmp/k93-5ghz-current-status.txt; then success=1; break; fi
    printf 'attempt=%s uptime=%s ' "$attempt" "$(cut -d ' ' -f1 /proc/uptime)"
    sed -n '/^wpa_state=/p;/^freq=/p' /tmp/k93-5ghz-current-status.txt
    sleep 3
done
cp /tmp/k93-5ghz-current-status.txt /tmp/k93-5ghz-final-status.txt
dmesg > /tmp/k93-5ghz-dmesg.txt
cp /run/samurai-wifi/wpa-retry.log /tmp/k93-5ghz-wpa-log.txt
if [ "$success" = 1 ]; then
    udhcpc -i wlan0 -s /usr/sbin/samurai-udhcpc-wlan -n -q -t 5 -T 3 > /tmp/k93-5ghz-dhcp.txt 2>&1
    echo FIVE_GHZ_AUTH_DHCP_PASS
else
    echo FIVE_GHZ_AUTH_NOT_COMPLETED
    cli set_network 0 freq_list 2462 | grep -qx OK
    cli select_network 0 | grep -qx OK
fi
