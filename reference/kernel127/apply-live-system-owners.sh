#!/bin/sh
set -eu
umask 077
uname -v | grep -q '^#126 '
test "$(uname -r)" = 7.3.0-rc6-rmx1931-samurai-k126+
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k126-embedded-runtime/boot-id-private.txt)"
test "$(cat /proc/sys/kernel/tainted)" = 0
input=/tmp/k127-system-owner-targets-private.txt
test "$(wc -l < "$input")" = 85
dest=/var/lib/samurai/k127-system-owner-r2
test ! -e "$dest"
mkdir -m700 "$dest"
cp "$input" "$dest/targets-private.txt"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
while read -r kind mode hash path; do
 case "$path" in /usr/lib/firmware/*|/etc/samurai-wifi|/etc/samurai-wifi/*) ;; *) exit 2;; esac
 test ! -L "$path"
 if test "$kind" = f; then
  test -f "$path"
  test "$(sha256sum "$path" | cut -d' ' -f1)" = "$hash"
 else test "$kind" = d; test -d "$path"; fi
 test "$(stat -c %a "$path")" = "$mode"
 case "$(stat -c '%u:%g' "$path")" in
  0:0|1000:1000) ;;
  10000:10000) case "$path" in /usr/lib/firmware/qcom/sm8150/realme/samurai-c28-trial/*|/usr/lib/firmware/qcom/sm8150/realme/samurai-c35-trial/*) ;; *) exit 2;; esac ;;
  *) exit 2;;
 esac
 stat -c '%u:%g %a %n' "$path" >> "$dest/before-private.txt"
done < "$input"
echo ALL85_PATH_CONTENT_MODE_OWNER_PREFLIGHT_PASS > "$dest/preflight.txt"
while read -r kind mode hash path; do
 chown 0:0 "$path"
 chmod "$mode" "$path"
 test "$(stat -c '%u:%g' "$path")" = 0:0
 test "$(stat -c %a "$path")" = "$mode"
 if test "$kind" = f; then test "$(sha256sum "$path" | cut -d' ' -f1)" = "$hash"; fi
 stat -c '%u:%g %a %n' "$path" >> "$dest/after-private.txt"
done < "$input"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-check.txt"
sha256sum -c /var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256 > "$dest/source-check.txt"
sha256sum -c /var/lib/samurai/k115-vendor-camera-source/vendor-before.sha256 > "$dest/vendor-check.txt"
cat /proc/sys/kernel/tainted > "$dest/taint.txt"
pgrep -x phosh > "$dest/phosh.txt"
pgrep -x phoc > "$dest/phoc.txt"
stat -c '%u:%g %a' /home/cy122 /home/cy122/.local > "$dest/home-unchanged.txt"
sync
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -cf /tmp/k127-system-owner-private.tar .
echo K127_LIVE85_SYSTEM_OWNERS_ROOT_FILE_BYTES_AND_MODES_PRESERVED
