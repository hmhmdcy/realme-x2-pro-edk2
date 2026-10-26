#!/bin/sh
set -eu
umask 077
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k113-reboot-audio-clean-6/boot-id-private.txt)"
dest=/var/lib/samurai/k113-display-dump-after-v10
test ! -e "$dest"
mkdir -m700 "$dest"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
count=0
for dump_node in /sys/class/devcoredump/devcd*; do
    test -e "$dump_node" || continue
    if [ "$(readlink -f "$dump_node/failing_device")" = /sys/devices/platform/soc@0/ae00000.display-subsystem/ae01000.display-controller ]; then
        count=$((count+1))
        timeout -s TERM -k 2 25 dd if="$dump_node/data" of="$dest/display-$count-private.bin" bs=1M count=64 > "$dest/read-$count.txt" 2>&1
    fi
done
printf '%s\n' "$count" > "$dest/dumps-found.txt"
# Reading a copied dump does not require deleting any kernel dump.
dmesg > "$dest/dmesg.txt"
cat /proc/sys/kernel/tainted > "$dest/tainted.txt"
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -cf /tmp/k113-display-dump-after-v10.tar .
sha256sum /tmp/k113-display-dump-after-v10.tar
echo EXISTING_DISPLAY_DUMPS_PRESERVED_WITHOUT_RELEASE
