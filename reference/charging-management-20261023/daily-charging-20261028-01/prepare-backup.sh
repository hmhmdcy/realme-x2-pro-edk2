#!/bin/sh
set -eu

release=7.3.0-rc6-rmx1931-samurai-k363+
root=/root/charging-daily-20261028-02-before
test "$(id -u)" -eq 0
mkdir -p "$root/modules" "$root/service" /etc/samurai-charging
cp -a /usr/share/samurai-charging/manifest.json "$root/manifest.json"
cp -a /etc/init.d/samurai-charging "$root/service/init"
cp -a /usr/sbin/samurai-charging "$root/service/runtime"
cp -a /lib/modules/$release/extra/samurai-charging/samurai-usb-input.ko \
    "$root/modules/samurai-usb-input.ko"
cp -a /lib/modules/$release/extra/samurai-charging/samurai-gauge-protection.ko \
    "$root/modules/samurai-gauge-protection.ko"
cp -a /lib/modules/$release/extra/samurai-charging/samurai-mp2650.ko \
    "$root/modules/samurai-mp2650.ko"
sha256sum "$root"/modules/* "$root"/service/* "$root"/manifest.json \
    > "$root/SHA256SUMS"
touch /etc/samurai-charging/backup-done
sync
cat "$root/SHA256SUMS"
