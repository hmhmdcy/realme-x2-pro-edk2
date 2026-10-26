#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k128-postflash-wifi-5ghz
baseline=/var/lib/samurai/k128-postflash-wifi-baseline
test ! -e "$dest"
test "$(uname -r)" = 7.3.0-rc6-rmx1931-samurai-k128+
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat "$baseline/boot-id-private.txt")"
test "$(cat /proc/sys/kernel/tainted)" = 0
original=$(cat "$baseline/active-uuid-private.txt")
test "$(nmcli -g GENERAL.CON-UUID device show wlan0)" = "$original"
sha256sum -c "$baseline/profile-files-before-private.sha256" >/dev/null
mkdir -m700 "$dest"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
nmcli -g LEVEL general logging > "$dest/old-log-level.txt"
nmcli -g DOMAINS general logging > "$dest/old-log-domains.txt"
sha256sum /sys/class/net/wlan0/address > "$dest/mac-before-private.sha256"
iw dev wlan0 link > "$dest/link-before-private.txt"
dmesg > "$dest/dmesg-before-private.txt"
logread -b 0 -n 16000 > "$dest/logread-before-private.txt"
clone=''
cleanup() {
    rc=$?
    trap - EXIT HUP INT TERM
    set +e
    echo "$rc" > "$dest/test-exit.txt"
    logread -b 0 -n 30000 > "$dest/logread-after-private.txt"
    if test "$(nmcli -g GENERAL.CON-UUID device show wlan0)" != "$original"; then
        timeout -k 3 50 nmcli --wait 40 connection up uuid "$original" ifname wlan0 > "$dest/restore-original-private.txt" 2>&1
        echo "$?" > "$dest/restore-exit.txt"
    else
        echo 0 > "$dest/restore-exit.txt"
    fi
    if test -n "$clone"; then
        nmcli connection delete uuid "$clone" > "$dest/remove-clone-private.txt" 2>&1
        echo "$?" > "$dest/remove-exit.txt"
    fi
    nmcli general logging level "$(cat "$dest/old-log-level.txt")" domains "$(cat "$dest/old-log-domains.txt")" > "$dest/restore-logging.txt" 2>&1
    echo "$?" > "$dest/logging-restore-exit.txt"
    iw dev wlan0 link > "$dest/link-restored-private.txt"
    nmcli -g GENERAL.CON-UUID device show wlan0 > "$dest/restored-uuid-private.txt"
    sha256sum /sys/class/net/wlan0/address > "$dest/mac-after-private.sha256"
    sha256sum -c "$baseline/profile-files-before-private.sha256" > "$dest/profile-files-check.txt"
    sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-check.txt"
    sha256sum -c /var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256 > "$dest/source-check.txt"
    sha256sum -c /var/lib/samurai/k115-vendor-camera-source/vendor-before.sha256 > "$dest/vendor-check.txt"
    dmesg > "$dest/dmesg-after-private.txt"
    cat /proc/sys/kernel/tainted > "$dest/taint-after.txt"
    cat /sys/class/remoteproc/remoteproc1/state > "$dest/modem-after.txt"
    pgrep -x phosh > "$dest/phosh-after.txt"
    pgrep -x phoc > "$dest/phoc-after.txt"
    (cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
    tar -C "$dest" -czf /tmp/k128-postflash-wifi-5ghz-private.tar.gz .
    echo K128_BOUNDED_5GHZ_TEST_FINISHED_RESTORE_EVIDENCE_PRIVATE
    exit "$rc"
}
trap cleanup EXIT HUP INT TERM
nmcli general logging level TRACE domains ALL > "$dest/set-trace.txt"
nmcli connection clone --temporary uuid "$original" 'Samurai k128 postflash temporary 5GHz' > "$dest/clone-private.txt"
clone=$(nmcli -g connection.uuid connection show id 'Samurai k128 postflash temporary 5GHz')
test -n "$clone"
printf '%s\n' "$clone" > "$dest/clone-uuid-private.txt"
nmcli connection modify --temporary uuid "$clone" connection.autoconnect no 802-11-wireless.band a 802-11-wireless.channel 36
nmcli --show-secrets connection show uuid "$clone" > "$dest/clone-profile-private.txt"
timeout -k 3 50 nmcli --wait 40 connection up uuid "$clone" ifname wlan0 > "$dest/activate-private.txt" 2>&1
nmcli -f GENERAL,IP4 device show wlan0 > "$dest/device-5ghz-private.txt"
iw dev wlan0 link > "$dest/link-5ghz-private.txt"
grep -Eq 'freq: 5180([.]0)?$' "$dest/link-5ghz-private.txt"
gateway=$(ip -4 route show default dev wlan0 | awk '/^default via / {print $3;exit}')
test -n "$gateway"
ping -I wlan0 -c 3 -W 3 "$gateway" > "$dest/gateway-private.txt"
curl -4 --noproxy '*' --interface wlan0 --fail --connect-timeout 10 --max-time 30 -D "$dest/https-headers-private.txt" -w '%{http_code} %{size_download} %{time_total} %{remote_ip}\n' https://example.com/ -o "$dest/https-body.txt" > "$dest/https-result-private.txt" 2> "$dest/https-stderr.txt"
curl -4 --noproxy '*' --interface wlan0 --fail --connect-timeout 10 --max-time 40 -D "$dest/index-headers-private.txt" -w '%{http_code} %{size_download} %{time_total} %{remote_ip}\n' https://dl-cdn.alpinelinux.org/alpine/edge/main/aarch64/APKINDEX.tar.gz -o "$dest/APKINDEX.tar.gz" > "$dest/index-result-private.txt" 2> "$dest/index-stderr.txt"
gzip -t "$dest/APKINDEX.tar.gz"
tar -tzf "$dest/APKINDEX.tar.gz" > "$dest/index-members.txt"
grep -qx APKINDEX "$dest/index-members.txt"
tar -xOzf "$dest/APKINDEX.tar.gz" APKINDEX | grep -c '^P:' > "$dest/index-package-count.txt"
for sample in 0 1 2 3 4 5 6 7 8 9; do
    test "$(cat /proc/sys/kernel/tainted)" = 0
    test "$(cat /sys/class/remoteproc/remoteproc1/state)" = running
    test "$(nmcli -g GENERAL.CON-UUID device show wlan0)" = "$clone"
    iw dev wlan0 link > "$dest/link-sample-$sample-private.txt"
    grep -Eq 'freq: 5180([.]0)?$' "$dest/link-sample-$sample-private.txt"
    cat /proc/uptime >> "$dest/samples.txt"
    if test "$sample" != 9; then sleep 5; fi
done
echo PASS > "$dest/network-result.txt"
