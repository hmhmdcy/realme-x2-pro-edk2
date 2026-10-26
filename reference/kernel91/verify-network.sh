#!/bin/sh
set -eu
umask 077
/tmp/k91-wpa_cli -p/tmp/k91-wpa-ctrl -iwlan0 status > /tmp/k91-network-status.txt
grep -q '^wpa_state=COMPLETED$' /tmp/k91-network-status.txt
gateway=$(sed -n 's/^router=//p' /tmp/k91-dhcp-lease.txt | awk '{print $1}')
test -n "$gateway"
ip route get 1.1.1.1 > /tmp/k91-network-route.txt
grep -q 'dev wlan0' /tmp/k91-network-route.txt
if ping -I wlan0 -c 3 -W 3 "$gateway" > /tmp/k91-ping-gateway.txt 2>&1; then
    echo GATEWAY_PING=PASS
else
    echo GATEWAY_PING=FAIL
fi
if ping -I wlan0 -c 3 -W 3 1.1.1.1 > /tmp/k91-ping-internet.txt 2>&1; then
    echo INTERNET_PING=PASS
else
    echo INTERNET_PING=FAIL
fi
if timeout 15 nslookup kernel.org > /tmp/k91-dns-test.txt 2>&1; then
    echo DNS_LOOKUP=PASS
else
    echo DNS_LOOKUP=FAIL
fi
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY all_proxy
if timeout 20 wget -O /tmp/k91-http-test.txt http://example.com/ > /tmp/k91-http-test.log 2>&1; then
    echo HTTP_FETCH=PASS
    wc -c < /tmp/k91-http-test.txt
    sha256sum /tmp/k91-http-test.txt
else
    echo HTTP_FETCH=FAIL
fi
cat /proc/sys/kernel/tainted /sys/class/remoteproc/remoteproc0/state /proc/uptime
