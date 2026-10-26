#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#103 SMP PREEMPT'
mpss=$(/usr/sbin/samurai-modem-remoteproc)
grep -qx 0 /run/samurai-wifi/boot-finished
/usr/sbin/samurai-bluetooth stop
[ "$(cat $mpss/state)" = running ]
dir=/tmp/k104-auto-network
test ! -e "$dir"
mkdir -m700 "$dir"
test -f /tmp/k104-wpa-5g-private.conf
test ! -L /tmp/k104-wpa-5g-private.conf
chmod 600 /tmp/k104-wpa-5g-private.conf
test -S /run/samurai-wifi/wpa-control/wlan0
/usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 ping | grep -qx PONG
cp /run/samurai-wifi/wpa.conf "$dir/wpa-empty-before.conf"
cp /tmp/k104-wpa-5g-private.conf /run/samurai-wifi/wpa.conf
chmod 600 /run/samurai-wifi/wpa.conf
/usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 reconfigure > "$dir/reconfigure.txt"
grep -qx OK "$dir/reconfigure.txt"
for attempt in $(seq 1 30); do
    /usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status > "$dir/status.txt"
    if grep -qx wpa_state=COMPLETED "$dir/status.txt" && grep -qx freq=5180 "$dir/status.txt"; then break; fi
    sleep 2
done
grep -qx wpa_state=COMPLETED "$dir/status.txt"
grep -qx freq=5180 "$dir/status.txt"
udhcpc -i wlan0 -s /usr/sbin/samurai-udhcpc-wlan -n -q -t 5 -T 3 > "$dir/dhcp.txt" 2>&1
gateway=$(sed -n 's/^router=//p' /run/samurai-wifi/dhcp-lease.txt | awk '{print $1}')
test -n "$gateway"
ip route get 1.1.1.1 > "$dir/route.txt"
grep -q 'dev wlan0' "$dir/route.txt"
ping -I wlan0 -c3 -W3 "$gateway" > "$dir/gateway.txt" 2>&1
timeout 15 nslookup kernel.org > "$dir/dns.txt" 2>&1
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY all_proxy
timeout 20 wget -O "$dir/http.txt" http://example.com/ > "$dir/http.log" 2>&1
ls /sys/class/bluetooth > "$dir/bt-class.txt"
test ! -s "$dir/bt-class.txt"
[ "$(cat /proc/sys/kernel/tainted)" = 0 ]
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-check.txt"
dmesg > "$dir/dmesg.txt"
cp /run/samurai-wifi/wpa.log "$dir/"
echo AUTO_BOOT_5G_AUTH_DHCP_GATEWAY_DNS_HTTP_PASS > "$dir/result.txt"
(cd "$dir" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
tar -C /tmp -cf /tmp/k104-auto-network.tar k104-auto-network
sha256sum /tmp/k104-auto-network.tar
