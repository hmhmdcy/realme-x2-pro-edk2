#!/bin/sh
set -eu
umask 077
test "$#" = 1
test "$(cat /proc/sys/kernel/random/boot_id)" = "$1"
uname -v | grep -q '^#157 '
test "$(cat /proc/sys/kernel/tainted)" = 0
test "$(awk '$2 == "/" {print $3}' /proc/mounts)" = rootfs
test "$(grep -Ec ' - (f2fs|ext4|vfat) ' /proc/self/mountinfo || true)" = 0
test -z "$(pidof phoc phosh || true)"
out=/tmp/k158-ram-switch
if test -e "$out"; then
 test "$(cat "$out/boot-id-private.txt")" = "$1"
else
 mkdir -m700 "$out"
 cat /proc/sys/kernel/random/boot_id > "$out/boot-id-private.txt"
fi
cat /proc/self/mountinfo > "$out/mounts-private.txt"
cat /proc/cmdline > "$out/cmdline-private.txt"
dmesg > "$out/dmesg-private.txt"
cat /proc/uptime > "$out/uptime.txt"
echo K158_CURRENT157_RAM_ONLY_NO_DISK_FILESYSTEM_VERIFIED
