#!/bin/sh
set -eu
target=/tmp/k84-guard-before-ready.txt
[ ! -e "$target" ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = 26edf78d-fba8-4dd4-9547-7bc65314bbe7 ]
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
grep -q '^8bb97ccb828dc8ccfaeb856be00b9a83f3b9fc57340208a24a7f9a51d88d8abe ' "$target"
cat "$target"
