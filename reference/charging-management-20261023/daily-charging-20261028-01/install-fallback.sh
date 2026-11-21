#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
test "$(id -u)" -eq 0
install -m 0755 "$root/fallback/samurai-charging" /etc/init.d/samurai-charging
install -m 0755 "$root/fallback/samurai-charging-runtime.py" \
    /usr/sbin/samurai-charging
rc-update add samurai-charging boot >/dev/null 2>&1 || true
rc-update add samurai-charging default >/dev/null 2>&1 || true
sync
echo "fallback charging health service installed"
