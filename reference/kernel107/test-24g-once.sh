#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#106 SMP PREEMPT'
grep -qx 0 /run/samurai-wifi/boot-finished
grep -qx AUTOMATIC_FIRST_BOOT_5G_AUTH_DHCP_GATEWAY_DNS_HTTP_PASS /tmp/k107-auto-network/result.txt
mpss=$(/usr/sbin/samurai-modem-remoteproc)
[ "$(cat "$mpss/state")" = running ]
dir=/tmp/k107-24g-once
test ! -e "$dir"
mkdir -m700 "$dir"
test -f /tmp/k107-wpa-2g-private.conf
test ! -L /tmp/k107-wpa-2g-private.conf
chmod 600 /tmp/k107-wpa-2g-private.conf
cp /run/samurai-wifi/wpa.conf "$dir/wpa-5g-before-private.conf"
dmesg > "$dir/dmesg-before.txt"
cp /tmp/k107-wpa-2g-private.conf /run/samurai-wifi/wpa.conf
chmod 600 /run/samurai-wifi/wpa.conf
attempt() {
    /usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 reconfigure > "$dir/reconfigure.txt" || return 1
    grep -qx OK "$dir/reconfigure.txt" || return 1
    for count in $(seq 1 30); do
        [ "$(cat "$mpss/state")" = running ] || return 1
        /usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status > "$dir/status.txt" || return 1
        if grep -qx wpa_state=COMPLETED "$dir/status.txt" && grep -q '^freq=24[0-9][0-9]$' "$dir/status.txt"; then break; fi
        sleep 1
    done
    grep -qx wpa_state=COMPLETED "$dir/status.txt" || return 1
    grep -q '^freq=24[0-9][0-9]$' "$dir/status.txt" || return 1
    udhcpc -i wlan0 -s /usr/sbin/samurai-udhcpc-wlan -n -q -t 5 -T 3 > "$dir/dhcp.txt" 2>&1 || return 1
    gateway=$(sed -n 's/^router=//p' /run/samurai-wifi/dhcp-lease.txt | awk '{print $1}')
    test -n "$gateway" || return 1
    ip route get 1.1.1.1 > "$dir/route.txt" || return 1
    grep -q 'dev wlan0' "$dir/route.txt" || return 1
    ping -I wlan0 -c3 -W3 "$gateway" > "$dir/gateway.txt" 2>&1 || return 1
    timeout 15 nslookup kernel.org > "$dir/dns.txt" 2>&1 || return 1
    unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY all_proxy
    timeout 20 wget -O "$dir/http.txt" http://example.com/ > "$dir/http.log" 2>&1 || return 1
}
if attempt; then
    echo SINGLE_24G_AUTH_DHCP_GATEWAY_DNS_HTTP_PASS > "$dir/result.txt"
else
    echo SINGLE_24G_ATTEMPT_FAILED > "$dir/result.txt"
fi
/usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status > "$dir/status-after.txt" || true
cp /run/samurai-wifi/wpa.log "$dir/"
dmesg > "$dir/dmesg-after.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-check.txt"
cat /proc/uptime /proc/sys/kernel/tainted > "$dir/state.txt"
cat "$mpss/state" >> "$dir/state.txt"
(cd "$dir" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
tar -C /tmp -cf /tmp/k107-24g-once.tar k107-24g-once
sha256sum /tmp/k107-24g-once.tar
echo SINGLE_24G_ATTEMPT_ARCHIVED_USE_SEPARATE_FINAL_5G_TEST
