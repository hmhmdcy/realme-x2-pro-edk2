#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k114-live-userspace
test ! -e "$dest"
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k114-rootfs-export/boot-id-private.txt)"
test "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline
test "$(cat /sys/devices/platform/sensor-power/state)" = 'vdd=0 vddio=0'
mkdir -m700 "$dest"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
cp /etc/apk/world "$dest/world-before-private.txt"
cp /lib/apk/db/installed "$dest/packages-before.txt"
sha256sum /usr/local/bin/samurai-phosh-session /etc/greetd/samurai-phosh.toml /usr/share/alsa/ucm2/conf.d/Realme_X2_Pro/*.conf > "$dest/desktop-before.sha256"
dmesg > "$dest/dmesg-before.txt"
apk add --simulate libcamera-tools calls chatty firefox mobile-config-firefox megapixels rsync strace > "$dest/apk-plan-private.txt" 2>&1
apk add libcamera-tools calls chatty firefox mobile-config-firefox megapixels rsync strace > "$dest/apk-install-private.txt" 2>&1
glib-compile-schemas --strict /usr/share/glib-2.0/schemas
sha256sum -c "$dest/desktop-before.sha256" > "$dest/desktop-check.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-check.txt"
sha256sum -c /var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256 > "$dest/source-check.txt"
apk info > "$dest/packages-after.txt"
rc-status -a > "$dest/services-after.txt"
cat /proc/sys/kernel/tainted > "$dest/taint-after.txt"
cat /sys/class/remoteproc/remoteproc0/state /sys/devices/platform/sensor-power/state > "$dest/sensor-after.txt"
pgrep -x phosh > "$dest/phosh-after.txt"
pgrep -x phoc > "$dest/phoc-after.txt"
cat /proc/asound/card0/pcm0p/sub0/status /proc/asound/card0/pcm1c/sub0/status > "$dest/pcm-after.txt"
cat /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status > "$dest/amps-after.txt"
dmesg > "$dest/dmesg-after.txt"
sync
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -czf /tmp/k114-live-userspace-private.tar.gz .
sha256sum /tmp/k114-live-userspace-private.tar.gz
echo ROOTFS114_MOBILE_APPLICATIONS_INSTALLED_ON_CURRENT_F2FS_WITHOUT_FLASH
