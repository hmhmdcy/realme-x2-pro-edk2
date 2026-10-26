#!/bin/sh
set -eu
target=/tmp/k86-guard-before-final.txt
[ ! -e "$target" ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = 32bf2d8f-8dde-47dc-9b88-e87db9e95198 ]
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
grep -q '^cf11644e32a138ff1319fe9e44529f1ef7b2a1907c1f8876c597f970a526d286 ' "$target"
cat "$target"
