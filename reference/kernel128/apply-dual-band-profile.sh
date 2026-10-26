#!/bin/sh
set -eu
umask 077
test "$#" = 2
before_hash=$1
candidate_hash=$2
dest=/var/lib/samurai/k128-dual-band-profile
profile=/etc/NetworkManager/system-connections/samurai-wifi.nmconnection
candidate=/tmp/k128-wifi-profile-private.nmconnection
test ! -e "$dest"
test "$(uname -r)" = 7.3.0-rc6-rmx1931-samurai-k128+
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k128-first-runtime/boot-id-private.txt)"
test "$(cat /proc/sys/kernel/tainted)" = 0
test ! -L "$profile"
test "$(stat -c '%u:%g:%a' "$profile")" = 0:0:600
test "$(sha256sum "$profile" | cut -d' ' -f1)" = "$before_hash"
test "$(sha256sum "$candidate" | cut -d' ' -f1)" = "$candidate_hash"
original=$(cat /var/lib/samurai/k128-postflash-wifi-baseline/active-uuid-private.txt)
test "$(nmcli -g GENERAL.CON-UUID device show wlan0)" = "$original"
mkdir -m700 "$dest"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
cp -a "$profile" "$dest/before-private.nmconnection"
dmesg > "$dest/dmesg-before-private.txt"
committed=0
installed=0
finish() {
 rc=$?
 trap - EXIT HUP INT TERM
 set +e
 if test "$committed" = 0 && test "$installed" = 1; then
  cp "$dest/before-private.nmconnection" "$profile.k128-rollback"
  chmod 0600 "$profile.k128-rollback"; chown 0:0 "$profile.k128-rollback"
  mv "$profile.k128-rollback" "$profile"
  nmcli connection reload > "$dest/rollback-reload.txt" 2>&1
  timeout -k 3 50 nmcli --wait 40 connection up uuid "$original" ifname wlan0 > "$dest/rollback-connect-private.txt" 2>&1
 fi
 echo "$rc" > "$dest/exit.txt"
 echo "$committed" > "$dest/committed.txt"
 cp -a "$profile" "$dest/after-private.nmconnection"
 nmcli --show-secrets connection show uuid "$original" > "$dest/profile-after-private.txt"
 stat -c '%u:%g:%a' "$profile" > "$dest/owner-mode.txt"
 iw dev wlan0 link > "$dest/link-after-private.txt"
 nmcli -g GENERAL.CON-UUID device show wlan0 > "$dest/uuid-after-private.txt"
 cat /proc/sys/kernel/tainted > "$dest/taint.txt"
 pgrep -x phosh > "$dest/phosh.txt"; pgrep -x phoc > "$dest/phoc.txt"
 cat /sys/class/remoteproc/remoteproc1/state /sys/class/remoteproc/remoteproc2/state > "$dest/remoteprocs.txt"
 logread -b 0 -n 22000 > "$dest/logread-after-private.txt"
 dmesg > "$dest/dmesg-after-private.txt"
 (cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
 tar -C "$dest" -czf /tmp/k128-dual-band-profile-private.tar.gz .
 echo K128_DUAL_BAND_PERSISTENT_PROFILE_ATTEMPT_PRIVATE_CAPTURED
 exit "$rc"
}
trap finish EXIT HUP INT TERM
test ! -e "$profile.k128-new"
cp "$candidate" "$profile.k128-new"
chmod 0600 "$profile.k128-new"
chown 0:0 "$profile.k128-new"
mv "$profile.k128-new" "$profile"
installed=1
nmcli connection reload > "$dest/reload.txt" 2>&1
test -z "$(nmcli -g 802-11-wireless.band connection show uuid "$original")"
timeout -k 3 50 nmcli --wait 40 connection up uuid "$original" ifname wlan0 > "$dest/activate-private.txt" 2>&1
test "$(nmcli -g GENERAL.CON-UUID device show wlan0)" = "$original"
iw dev wlan0 link > "$dest/link-active-private.txt"
grep -Eq 'freq: (2462|5180)([.]0)?$' "$dest/link-active-private.txt"
gateway=$(ip -4 route show default dev wlan0 | awk '/^default via / {print $3;exit}')
test -n "$gateway"
ping -I wlan0 -c 3 -W 3 "$gateway" > "$dest/gateway-private.txt"
curl -4 --noproxy '*' --interface wlan0 --fail --connect-timeout 10 --max-time 30 -w '%{http_code} %{size_download} %{time_total}\n' https://example.com/ -o "$dest/https-body.txt" > "$dest/https-result.txt" 2> "$dest/https-stderr.txt"
test "$(cat /proc/sys/kernel/tainted)" = 0
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-check.txt"
sha256sum -c /var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256 > "$dest/source-check.txt"
sha256sum -c /var/lib/samurai/k115-vendor-camera-source/vendor-before.sha256 > "$dest/vendor-check.txt"
test -n "$(pgrep -x phosh)" && test -n "$(pgrep -x phoc)"
sync
committed=1
