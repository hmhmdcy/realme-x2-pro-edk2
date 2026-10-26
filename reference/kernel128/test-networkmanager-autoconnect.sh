#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k128-nm-auto-restart
test ! -e "$dest"
test "$(uname -r)" = 7.3.0-rc6-rmx1931-samurai-k128+
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k128-first-runtime/boot-id-private.txt)"
test "$(cat /var/lib/samurai/k128-dual-band-profile/committed.txt)" = 1
original=$(cat /var/lib/samurai/k128-dual-band-profile/uuid-after-private.txt)
test "$(nmcli -g GENERAL.CON-UUID device show wlan0)" = "$original"
mkdir -m700 "$dest"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
dmesg > "$dest/dmesg-before-private.txt"
logread -b 0 -n 22000 > "$dest/logread-before-private.txt"
finish() {
 rc=$?
 trap - EXIT HUP INT TERM
 set +e
 echo "$rc" > "$dest/exit.txt"
 iw dev wlan0 link > "$dest/link-after-private.txt"
 nmcli -g GENERAL.CON-UUID device show wlan0 > "$dest/uuid-after-private.txt"
 dmesg > "$dest/dmesg-after-private.txt"
 logread -b 0 -n 26000 > "$dest/logread-after-private.txt"
 cat /proc/sys/kernel/tainted > "$dest/taint.txt"
 pgrep -x phosh > "$dest/phosh.txt"; pgrep -x phoc > "$dest/phoc.txt"
 cat /sys/class/remoteproc/remoteproc1/state /sys/class/remoteproc/remoteproc2/state > "$dest/remoteprocs.txt"
 (cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
 tar -C "$dest" -czf /tmp/k128-nm-auto-restart-private.tar.gz .
 echo K128_NETWORKMANAGER_RESTART_AUTO_CONNECT_EVIDENCE_PRIVATE_SAVED
 exit "$rc"
}
trap finish EXIT HUP INT TERM
timeout -k 3 40 rc-service networkmanager restart > "$dest/restart.txt" 2>&1
connected=0
for attempt in $(seq 1 60); do
 nmcli -g GENERAL.STATE device show wlan0 > "$dest/state-last.txt" 2>&1 || true
 if grep -q '^100 ' "$dest/state-last.txt"; then connected=1;break;fi
 sleep 1
done
test "$connected" = 1
printf '%s\n' "$attempt" > "$dest/connected-attempt.txt"
test "$(nmcli -g GENERAL.CON-UUID device show wlan0)" = "$original"
test -z "$(nmcli -g 802-11-wireless.band connection show uuid "$original")"
iw dev wlan0 link > "$dest/link-auto-private.txt"
grep -Eq 'freq: (2462|5180)([.]0)?$' "$dest/link-auto-private.txt"
curl -4 --noproxy '*' --interface wlan0 --fail --connect-timeout 10 --max-time 30 -w '%{http_code} %{size_download} %{time_total}\n' https://example.com/ -o "$dest/https-body.txt" > "$dest/https-result.txt" 2> "$dest/https-stderr.txt"
for sample in 0 1 2 3 4 5; do
 test "$(cat /proc/sys/kernel/tainted)" = 0
 test "$(nmcli -g GENERAL.CON-UUID device show wlan0)" = "$original"
 cat /proc/uptime >> "$dest/samples.txt"
 if test "$sample" != 5;then sleep 5;fi
done
echo PASS > "$dest/result.txt"
