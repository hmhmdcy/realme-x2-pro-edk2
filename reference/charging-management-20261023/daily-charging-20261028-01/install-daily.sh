#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
release=7.3.0-rc6-rmx1931-samurai-k363+
module_dir=/lib/modules/$release/extra/samurai-charging
backup=/root/charging-daily-20261028-02-before

test "$(id -u)" -eq 0
test -r /etc/samurai-charging/backup-done
test -r "$backup/SHA256SUMS"
mkdir -p "$module_dir" /etc/init.d /usr/sbin /usr/share/samurai-charging

install -m 0644 "$root/artifacts/samurai-usb-input.ko" \
    "$module_dir/samurai-usb-input.ko"
install -m 0644 "$root/artifacts/samurai-gauge-protection.ko" \
    "$module_dir/samurai-gauge-protection.ko"
install -m 0644 "$root/artifacts/samurai-mp2650-deferred.ko" \
    "$module_dir/samurai-mp2650.ko"
install -m 0755 "$root/service/samurai-charging" \
    /etc/init.d/samurai-charging
install -m 0755 "$root/service/samurai-charging-runtime.py" \
    /usr/sbin/samurai-charging
install -m 0644 "$root/manifest.json" \
    /usr/share/samurai-charging/manifest.json
# Preserve the historical implementation as inert files. The active command
# and manifest no longer reference control-trial.py or the trial guard.
if [ -d /usr/lib/samurai-charging ]; then
    target="$backup/trial-lib"
    if [ -e "$target" ]; then
        target="$target-$(date +%Y%m%d%H%M%S)"
    fi
    mv /usr/lib/samurai-charging "$target"
fi
depmod "$release"
# Start charging before the default runlevel.  samurai-radio can remain in
# "starting" for a long time on this board; leaving charging only in default
# can delay it until after the battery has already drained.
rc-update add samurai-charging boot >/dev/null 2>&1 || true
rc-update add samurai-charging default >/dev/null 2>&1 || true
sync
echo "daily charging files installed; reboot required for cold-path validation"
