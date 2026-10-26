#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k129-reboot-auto-network
test ! -e "$dest"
test "$(uname -r)" = 7.3.0-rc6-rmx1931-samurai-k129+
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k129-first-runtime/boot-id-private.txt)"
original=$(cat /var/lib/samurai/k128-dual-band-profile/uuid-after-private.txt)
test "$(nmcli -g GENERAL.CON-UUID device show wlan0)" = "$original"
test -z "$(nmcli -g 802-11-wireless.band connection show uuid "$original")"
mkdir -m700 "$dest"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
cp /etc/NetworkManager/system-connections/samurai-wifi.nmconnection "$dest/profile-private.nmconnection"
stat -c '%u:%g:%a' /etc/NetworkManager/system-connections/samurai-wifi.nmconnection > "$dest/profile-owner.txt"
nmcli -g GENERAL.CON-UUID device show wlan0 > "$dest/active-uuid-private.txt"
iw dev wlan0 link > "$dest/link-before-private.txt"
grep -Eq 'freq: 5180([.]0)?$' "$dest/link-before-private.txt"
dmesg > "$dest/dmesg-before-private.txt"
logread -b 0 -n 16000 > "$dest/logread-before-private.txt"
finish() {
 rc=$?;trap - EXIT HUP INT TERM;set +e
 echo "$rc" > "$dest/exit.txt"
 dmesg > "$dest/dmesg-after-private.txt"
 logread -b 0 -n 26000 > "$dest/logread-after-private.txt"
 iw dev wlan0 link > "$dest/link-after-private.txt"
 nmcli -g GENERAL.CON-UUID device show wlan0 > "$dest/uuid-after-private.txt"
 cat /proc/sys/kernel/tainted > "$dest/taint.txt"
 sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-check.txt"
 sha256sum -c /var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256 > "$dest/source-check.txt"
 sha256sum -c /var/lib/samurai/k115-vendor-camera-source/vendor-before.sha256 > "$dest/vendor-check.txt"
 (cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
 tar -C "$dest" -czf /tmp/k129-reboot-auto-network-private.tar.gz .
 echo K129_REBOOT_AUTOCONNECT_NETWORK_EVIDENCE_PRIVATE_SAVED
 exit "$rc"
}
trap finish EXIT HUP INT TERM
gateway=$(ip -4 route show default dev wlan0 | awk '/^default via / {print $3;exit}');test -n "$gateway"
ping -I wlan0 -c 3 -W 3 "$gateway" > "$dest/gateway-private.txt"
curl -4 --noproxy '*' --interface wlan0 --fail --connect-timeout 10 --max-time 30 -w '%{http_code} %{size_download} %{time_total}\n' https://example.com/ -o "$dest/https-body.txt" > "$dest/https-result.txt" 2> "$dest/https-stderr.txt"
curl -4 --noproxy '*' --interface wlan0 --fail --connect-timeout 10 --max-time 40 -w '%{http_code} %{size_download} %{time_total}\n' https://dl-cdn.alpinelinux.org/alpine/edge/main/aarch64/APKINDEX.tar.gz -o "$dest/APKINDEX.tar.gz" > "$dest/index-result.txt" 2> "$dest/index-stderr.txt"
gzip -t "$dest/APKINDEX.tar.gz";tar -tzf "$dest/APKINDEX.tar.gz" > "$dest/index-members.txt";grep -qx APKINDEX "$dest/index-members.txt"
tar -xOzf "$dest/APKINDEX.tar.gz" APKINDEX | grep -c '^P:' > "$dest/index-packages.txt"
for sample in 0 1 2 3 4 5; do
 test "$(nmcli -g GENERAL.CON-UUID device show wlan0)" = "$original"
 test "$(cat /proc/sys/kernel/tainted)" = 0
 test -n "$(pgrep -x phosh)" && test -n "$(pgrep -x phoc)"
 iw dev wlan0 link > "$dest/link-$sample-private.txt";grep -Eq 'freq: 5180([.]0)?$' "$dest/link-$sample-private.txt"
 cat /proc/uptime >> "$dest/samples.txt"
 if test "$sample" != 5;then sleep 10;fi
done
echo PASS > "$dest/result.txt"
