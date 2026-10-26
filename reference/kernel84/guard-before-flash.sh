#!/bin/sh
set -eu
target=/tmp/k84-guard-before-flash.txt
[ ! -e "$target" ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = 87753933-4992-45d2-aaf5-d9db9c11d1a3 ]
grep -qx 'PARTNAME=boot' /sys/class/block/sde11/uevent
grep -qx 'PARTNAME=logdump' /sys/class/block/sde32/uevent
[ "$(cat /sys/class/block/sde11/size)" = 196608 ]
[ "$(cat /sys/class/block/sde32/size)" = 131072 ]
{
    cat /proc/sys/kernel/random/boot_id
    cat /proc/uptime
    cat /proc/sys/kernel/tainted
    head -c 6682624 /dev/sde11 | sha256sum
    sha256sum /dev/sde32
} >"$target"
grep -q '^08edf9bcc1c55977169b0a8fd9f963805ba98d0423929e09e17bb9f811ca7405 ' "$target"
grep -q '^607fc6b4b0caba8ca5c7ea6677fd8259c81a216f91b2d6de7603e3f56d9881d0 ' "$target"
cat "$target"
