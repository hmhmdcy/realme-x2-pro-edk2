#!/bin/sh
set -eu
umask 077
[ "$(cat /proc/sys/kernel/random/boot_id)" = 02ba5ffd-9768-43e4-9c6e-511bb1aeccd1 ]
cli()
{
    /usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 "$@"
}
cli list_networks > /tmp/k95-5ghz-network-before.txt
grep -q '^0[[:space:]]*TP-LINK_156D' /tmp/k95-5ghz-network-before.txt
cli status > /tmp/k95-5ghz-status-before.txt
grep -qx wpa_state=COMPLETED /tmp/k95-5ghz-status-before.txt
cli set_network 0 freq_list 5180 | grep -qx OK
cli select_network 0 | grep -qx OK
cli reassociate | grep -qx OK
success=0
for attempt in $(seq 1 20); do
    cli status > /tmp/k95-5ghz-current-status.txt
    if grep -qx wpa_state=COMPLETED /tmp/k95-5ghz-current-status.txt && grep -qx freq=5180 /tmp/k95-5ghz-current-status.txt; then success=1; break; fi
    printf 'attempt=%s uptime=%s ' "$attempt" "$(cut -d ' ' -f1 /proc/uptime)"
    sed -n '/^wpa_state=/p;/^freq=/p' /tmp/k95-5ghz-current-status.txt
    sleep 3
done
cp /tmp/k95-5ghz-current-status.txt /tmp/k95-5ghz-final-status.txt
dmesg > /tmp/k95-5ghz-dmesg.txt
cp /run/samurai-wifi/wpa.log /tmp/k95-5ghz-wpa-log.txt
if [ "$success" = 1 ]; then
    udhcpc -i wlan0 -s /usr/sbin/samurai-udhcpc-wlan -n -q -t 5 -T 3 > /tmp/k95-5ghz-dhcp.txt 2>&1
    echo FIVE_GHZ_AUTH_DHCP_PASS
else
    echo FIVE_GHZ_AUTH_NOT_COMPLETED
    cli set_network 0 freq_list 2462 | grep -qx OK
    cli select_network 0 | grep -qx OK
fi
