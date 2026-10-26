#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k128-postflash-wifi-baseline
test ! -e "$dest"
test "$(uname -r)" = 7.3.0-rc6-rmx1931-samurai-k128+
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k128-first-runtime/boot-id-private.txt)"
test "$(cat /proc/sys/kernel/tainted)" = 0
mkdir -m700 "$dest"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
cat /proc/uptime > "$dest/uptime.txt"
uname -a > "$dest/uname.txt"
nmcli --version > "$dest/nm-version.txt"
nmcli -t -f GENERAL device show wlan0 > "$dest/device-private.txt"
nmcli -g GENERAL.CON-UUID device show wlan0 > "$dest/active-uuid-private.txt"
nmcli --show-secrets connection show uuid "$(cat "$dest/active-uuid-private.txt")" > "$dest/profile-private.txt"
nmcli -t -f UUID,TYPE,DEVICE connection show > "$dest/profiles-private.txt"
iw dev wlan0 link > "$dest/link-before-private.txt"
iw reg get > "$dest/regdom.txt"
iw phy > "$dest/phy-private.txt"
iw dev wlan0 get power_save > "$dest/powersave.txt"
ip route > "$dest/routes-private.txt"
ip address show wlan0 > "$dest/address-private.txt"
dmesg > "$dest/dmesg-before-private.txt"
logread -b 0 -n 16000 > "$dest/logread-before-private.txt"
if command -v logbook >/dev/null 2>&1; then
    timeout -k 2 10 logbook > "$dest/logbook-before-private.txt" 2>&1 || echo "$?" > "$dest/logbook-exit.txt"
fi
find /etc/NetworkManager -type f -exec sha256sum '{}' ';' > "$dest/profile-files-before-private.sha256"
timeout -k 2 20 nmcli device wifi rescan ifname wlan0 > "$dest/rescan.txt" 2>&1 || echo "$?" > "$dest/rescan-exit.txt"
sleep 5
nmcli -t --escape yes -f SSID,BSSID,FREQ,CHAN,SIGNAL,SECURITY device wifi list ifname wlan0 --rescan no > "$dest/scan-private.txt"
iw dev wlan0 scan dump > "$dest/bss-private.txt"
iw dev wlan0 link > "$dest/link-after-private.txt"
dmesg > "$dest/dmesg-after-private.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-check.txt"
sha256sum -c /var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256 > "$dest/source-check.txt"
sha256sum -c /var/lib/samurai/k115-vendor-camera-source/vendor-before.sha256 > "$dest/vendor-check.txt"
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -czf /tmp/k128-postflash-wifi-baseline-private.tar.gz .
echo K128_CURRENT_BOOT_WIFI_BASELINE_PRIVATE_CAPTURED
