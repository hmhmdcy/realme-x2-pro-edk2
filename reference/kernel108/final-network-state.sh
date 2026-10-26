#!/bin/sh
set -eu
umask 077
test "$#" = 1
test "$(cat /proc/sys/kernel/random/boot_id)" = "$1"
uname -v | grep -q '^#106 '
failed=/tmp/k108-auto-network
test -d "$failed"
test ! -e "$failed/result.txt"
echo ASSOCIATION_NOT_COMPLETED_WITHIN_60_SECONDS > "$failed/result.txt"
cp /run/samurai-wifi/wpa.log "$failed/wpa-after-failed-window.log"
dmesg > "$failed/dmesg-after-failed-window.txt"
(cd "$failed" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$failed/SHA256SUMS"
tar -cf "$failed.tar" -C /tmp k108-auto-network
out=/tmp/k108-final-network
test ! -e "$out"
mkdir -m 700 "$out"
rc=0
wpa=/usr/sbin/wpa_cli
"$wpa" -p/run/samurai-wifi/wpa-control -iwlan0 status > "$out/status.txt"
grep -qx wpa_state=COMPLETED "$out/status.txt" || rc=1
grep -qx freq=5180 "$out/status.txt" || rc=1
if test "$rc" = 0; then
    udhcpc -i wlan0 -s /usr/sbin/samurai-udhcpc-wlan -n -q -t 5 -T 3 > "$out/dhcp.txt" 2>&1 || rc=1
fi
if test "$rc" = 0; then
    gateway=$(sed -n 's/^router=//p' /run/samurai-wifi/dhcp-lease.txt | awk '{print $1}')
    test -n "$gateway" || rc=1
    ip route get 1.1.1.1 > "$out/route.txt"
    grep -q 'dev wlan0' "$out/route.txt" || rc=1
    ping -I wlan0 -c3 -W3 "$gateway" > "$out/gateway.txt" 2>&1 || rc=1
    timeout 15 nslookup kernel.org > "$out/dns.txt" 2>&1 || rc=1
    unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY all_proxy
    timeout 20 wget -O "$out/http.txt" http://example.com/ > "$out/http.log" 2>&1 || rc=1
fi
if test "$rc" = 0; then
    echo EXISTING_5G_CONNECTION_DHCP_GATEWAY_DNS_HTTP_PASS > "$out/result.txt"
else
    echo FINAL_NETWORK_TEST_FAILED > "$out/result.txt"
fi
"$wpa" -p/run/samurai-wifi/wpa-control -iwlan0 status > "$out/status-after.txt"
cp /run/samurai-wifi/wpa.log "$out/wpa.log"
dmesg > "$out/dmesg.txt"
cat /proc/uptime /proc/sys/kernel/tainted > "$out/runtime.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$out/nv-check.txt"
(cd "$out" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$out/SHA256SUMS"
tar -cf "$out.tar" -C /tmp k108-final-network
cat "$out/result.txt"
exit "$rc"
