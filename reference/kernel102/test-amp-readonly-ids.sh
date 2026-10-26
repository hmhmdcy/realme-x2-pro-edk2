#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#101 SMP PREEMPT'
grep -q -- '--- no soundcards ---' /proc/asound/cards
[ "$(cat /proc/sys/kernel/tainted)" = 0 ]
dir=/tmp/k102-amp-readonly-ids
test ! -e "$dir"
count=0
left=
right=
for p in /sys/bus/i2c/drivers/max98927/*-0039; do
    test -L "$p" || continue
    node=$(readlink -f "$p/of_node")
    [ "$node" = /sys/firmware/devicetree/base/soc@0/geniqup@8c0000/i2c@890000/amplifier@39 ]
    left=${p##*/};count=$((count+1))
done
[ "$count" = 1 ]
bus=${left%-0039}
right=$bus-003a
test -L "/sys/bus/i2c/drivers/max98927/$right"
[ "$(readlink -f /sys/bus/i2c/devices/$right/of_node)" = /sys/firmware/devicetree/base/soc@0/geniqup@8c0000/i2c@890000/amplifier@3a ]
count=0
chip=
for p in /sys/bus/gpio/devices/gpiochip*; do
    test -e "$p" || continue
    if [ "$(readlink -f "$p/of_node")" = /sys/firmware/devicetree/base/soc@0/pinctrl@3100000 ]; then
        chip=/dev/${p##*/};count=$((count+1))
    fi
done
[ "$count" = 1 ]
test -c "$chip" && test -c "/dev/i2c-$bus"
mkdir -m700 "$dir"
cat /sys/kernel/debug/asoc/components > "$dir/components-before.txt"
cat /sys/kernel/debug/pinctrl/3100000.pinctrl/pinmux-pins > "$dir/pinmux-before.txt"
dmesg > "$dir/dmesg-before.txt"
sha256sum /tmp/k102-amp-readonly-ids-private > "$dir/helper.sha"
echo "$left" > /sys/bus/i2c/drivers/max98927/unbind
echo "$right" > /sys/bus/i2c/drivers/max98927/unbind
test ! -L "/sys/bus/i2c/devices/$left/driver"
test ! -L "/sys/bus/i2c/devices/$right/driver"
timeout 5 /tmp/k102-amp-readonly-ids-private "/dev/i2c-$bus" "$chip" > "$dir/id-replies.txt" 2> "$dir/id-error.txt"
cat /sys/kernel/debug/asoc/components > "$dir/components-after.txt"
cat /sys/kernel/debug/pinctrl/3100000.pinctrl/pinmux-pins > "$dir/pinmux-after.txt"
cat /sys/kernel/debug/gpio > "$dir/gpio-after.txt"
cat "$(/tmp/k102-haptics-device)/status" > "$dir/haptics-status.txt"
{
    uname -a
    cat /proc/sys/kernel/random/boot_id /proc/uptime /proc/sys/kernel/tainted
    for p in /sys/class/remoteproc/remoteproc*; do cat "$p/name" "$p/state"; done
} > "$dir/state.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-check.txt"
sha256sum /dev/sda2 > "$dir/persist.sha"
dmesg > "$dir/dmesg-after.txt"
echo OEM_DUAL_REVISION_REGISTERS_READ_AMPS_UNBOUND_RESET_LOW_NO_PCM > "$dir/result.txt"
(cd "$dir" && find . -type f ! -path ./SHA256SUMS -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
tar -C /tmp -cf /tmp/k102-amp-readonly-ids.tar k102-amp-readonly-ids
sha256sum /tmp/k102-amp-readonly-ids.tar
