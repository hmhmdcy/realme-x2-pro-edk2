#!/bin/sh
set -eu
umask 077
[ "$(cat /proc/sys/kernel/random/boot_id)" = 02ba5ffd-9768-43e4-9c6e-511bb1aeccd1 ]
for attempt in $(seq 1 60); do
    grep -q COEXISTENCE_OBSERVATION_PASS /tmp/k95-coexistence.log && break
    sleep 1
done
grep -q COEXISTENCE_OBSERVATION_PASS /tmp/k95-coexistence.log
test ! -e /tmp/k95-2ghz-traffic.bin
test ! -e /tmp/k95-2ghz-traffic-upload.bin
mv /tmp/k93-5ghz-traffic.bin /tmp/k95-2ghz-traffic.bin
mv /tmp/k93-5ghz-traffic-upload.bin /tmp/k95-2ghz-traffic-upload.bin
sh /tmp/k95-test-5ghz.sh > /tmp/k95-5ghz-test.log 2>&1
grep -q FIVE_GHZ_AUTH_DHCP_PASS /tmp/k95-5ghz-test.log
sh /tmp/k95-verify-5ghz.sh > /tmp/k95-5ghz-network-test.txt 2>&1
grep -qx GATEWAY_PING=PASS /tmp/k95-5ghz-network-test.txt
grep -qx DNS_LOOKUP=PASS /tmp/k95-5ghz-network-test.txt
grep -qx HTTP_FETCH=PASS /tmp/k95-5ghz-network-test.txt
nohup sh /tmp/k95-coexistence-5ghz.sh > /tmp/k95-5ghz-coexistence.log 2>&1 < /dev/null &
dd if=/dev/urandom of=/tmp/k93-5ghz-traffic.bin bs=1048576 count=4 > /tmp/k95-5ghz-traffic-dd.txt 2>&1
nohup /tmp/k95-wifi-traffic-server "$(sed -n 's/^ip=//p' /run/samurai-wifi/dhcp-lease.txt)" > /tmp/k95-5ghz-traffic-server.log 2>&1 < /dev/null &
echo FIVE_GHZ_TRAFFIC_PHASE_READY
