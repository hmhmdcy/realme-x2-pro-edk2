#!/bin/sh
# Export package/configuration state; the running root is never unmounted or flashed.
set -eu
umask 077
uname -v | grep -q '^#113 '
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k113-reboot-audio-clean-15/boot-id-private.txt)"
test "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline
test "$(cat /sys/devices/platform/sensor-power/state)" = 'vdd=0 vddio=0'
dest=/var/lib/samurai/k114-rootfs-export
test ! -e "$dest"
mkdir -m700 "$dest"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
cat /proc/mounts > "$dest/mounts-private.txt"
apk info > "$dest/packages.txt"
cat /proc/sys/kernel/tainted > "$dest/taint.txt"
rc-status -a > "$dest/services.txt"
dmesg > "$dest/dmesg-before.txt"
# Check installed payload and system settings before and after export.
(cd / && find usr etc -type f -exec sha256sum '{}' ';') > "$dest/static-before.sha256"
command -v getcap >/dev/null && getcap -r /usr > "$dest/capabilities.txt" || :
tar -C / -czf "$dest/rootfs-payload-private.tar.gz" \
    --exclude=home/cy122/.cache --exclude=home/cy122/.local/state \
    --exclude=home/cy122/.config/pulse --exclude=home/cy122/.config/gnome-software \
    usr etc bin sbin lib boot root home var/lib/AccountsService var/lib/dbus var/lib/alsa
(cd / && sha256sum -c "$dest/static-before.sha256") > "$dest/static-after-check.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-after-check.txt"
sha256sum -c /var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256 > "$dest/sources-after-check.txt"
dmesg > "$dest/dmesg-after.txt"
(cd "$dest" && sha256sum rootfs-payload-private.tar.gz > archive.sha256)
echo ROOTFS114_PACKAGE_AND_CONFIG_EXPORT_COMPLETE
