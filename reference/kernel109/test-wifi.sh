#!/bin/sh
set -eu
umask 077
dir=/var/lib/samurai/k109-wifi-first
test ! -e "$dir"
mkdir -m700 "$dir"
[ "$(cat /run/samurai-wifi/boot-finished)" = 0 ]
[ "$(cat "$(/usr/sbin/samurai-modem-remoteproc)/state")" = running ]
test -f /run/samurai-wifi/wpa-5g-private.conf
chmod 600 /run/samurai-wifi/wpa-5g-private.conf
cp /run/samurai-wifi/wpa-5g-private.conf /run/samurai-wifi/wpa.conf
cli='/usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0'
$cli reconfigure > "$dir/reconfigure.txt"
connected=0
for n in $(seq 1 90); do
    $cli status > "$dir/status.txt"
    if grep -qx wpa_state=COMPLETED "$dir/status.txt"; then connected=1; break; fi
    sleep 1
done
if [ "$connected" = 1 ]; then
    /usr/libexec/samurai/busybox udhcpc -iwlan0 -s/usr/sbin/samurai-udhcpc-wlan -f -n -q -t6 -T3 > "$dir/dhcp.txt" 2>&1 || true
    ip -4 addr > "$dir/addr.txt"
    ip -4 route > "$dir/routes.txt"
    gateway=$(ip -4 route show default dev wlan0 | awk '/^default via / {print $3; exit}')
    if [ -n "$gateway" ]; then
        ping -c3 -W3 "$gateway" > "$dir/gateway.txt" 2>&1 || true
        curl --interface wlan0 --connect-timeout 8 --max-time 20 --fail --location --output "$dir/http.txt" http://example.com/ > "$dir/curl-http.txt" 2>&1 || true
        curl --interface wlan0 --connect-timeout 8 --max-time 30 --fail --output "$dir/apk-index.tar.gz" https://dl-cdn.alpinelinux.org/alpine/edge/main/aarch64/APKINDEX.tar.gz > "$dir/curl-https.txt" 2>&1 || true
    fi
else
    echo ASSOCIATION_90_SECOND_WINDOW_FAILED > "$dir/result.txt"
fi
dmesg > "$dir/dmesg.txt"
cp /run/samurai-wifi/wpa.log "$dir/"
cat /proc/uptime /proc/sys/kernel/tainted > "$dir/state.txt"
(cd "$dir" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
tar -C /var/lib/samurai -cf /tmp/k109-wifi-first.tar k109-wifi-first
sha256sum /tmp/k109-wifi-first.tar
echo PMOS_WIFI_FIRST_BOUNDED_TEST_COMPLETE
