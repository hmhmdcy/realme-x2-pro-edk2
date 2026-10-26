#!/bin/sh
set -eu
target=/tmp/k86-guard-before-flash.txt
[ ! -e "$target" ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = f02d218a-cc7d-4b92-8858-c8eeaeab5777 ]
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
grep -q '^60e183a6780945885a738ac1bd0c7e23ed41515bca662cb50a831ede3b57302b ' "$target"
cat "$target"
