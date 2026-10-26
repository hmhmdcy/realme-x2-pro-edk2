#!/bin/sh
set -eu
umask 077
[ "$#" = 2 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
case "$2" in *[!a-z0-9-]*|'') exit 2;; esac
uname -a | grep -q '#109 SMP PREEMPT'
grep -q '^/dev/sda16 / f2fs rw' /proc/mounts
dir=/var/lib/samurai/k111-$2
test ! -e "$dir"
mkdir -m700 "$dir"
cleanup() {
    for name in vendor dsp persist modem; do
        if grep -q " $dir/mount-$name " /proc/mounts; then
            umount "$dir/mount-$name"
        fi
    done
}
trap cleanup EXIT HUP INT TERM
find_part() {
    found=
    for node in /sys/class/block/sd*; do
        if grep -qx "PARTNAME=$1" "$node/uevent"; then
            test -z "$found"
            found=/dev/$(basename "$node")
        fi
    done
    test -n "$found"
    printf '%s\n' "$found"
}
modem=$(find_part modem)
persist=$(find_part persist)
dsp=$(find_part dsp)
vendor=$(find_part vendor)
printf '%s\n' "$modem" "$persist" "$dsp" "$vendor" > "$dir/source-nodes.txt"
sha256sum "$modem" "$persist" "$dsp" "$vendor" > "$dir/sources-before.sha256"
# The known source partitions have been independently checked in prior stages.
grep -q '^88af46265a4f23c634b2a3c0a4be6815caf796f4b3bb398a6223a565c9e132f0 ' "$dir/sources-before.sha256"
grep -q '^7e085ef3264e212da7009099113b86ad1f6ec44176840f03f9b85d0e632412f3 ' "$dir/sources-before.sha256"
grep -wq ext4 /proc/filesystems || modprobe ext4
for name in modem persist dsp vendor; do mkdir -m700 "$dir/mount-$name"; done
mount -t vfat -o ro "$modem" "$dir/mount-modem"
mount -t ext4 -o ro,noload "$persist" "$dir/mount-persist"
for name in dsp vendor; do
    case "$name" in dsp) source=$dsp;; vendor) source=$vendor;; esac
    type=$(blkid -s TYPE -o value "$source")
    case "$type" in
        ext4) mount -t ext4 -o ro,noload "$source" "$dir/mount-$name";;
        vfat) mount -t vfat -o ro "$source" "$dir/mount-$name";;
        *) echo 'Unexpected source filesystem' >&2; exit 2;;
    esac
done
mount > "$dir/mounts.txt"
for name in modem persist dsp vendor; do
    grep -q " $dir/mount-$name .* ro," /proc/mounts
done
mkdir -m700 "$dir/firmware" "$dir/sdsp" "$dir/sensors-persist" "$dir/sensors-vendor" "$dir/socinfo"
for path in "$dir"/mount-modem/image/slpi.mdt "$dir"/mount-modem/image/slpi.b* "$dir"/mount-modem/image/slpi*.jsn; do
    test -f "$path"; test ! -L "$path"
    cp -p "$path" "$dir/firmware/"
done
test -f "$dir/firmware/slpi.mdt"
find "$dir/mount-dsp" -type d -name sdsp > "$dir/sdsp-directories.txt"
test "$(wc -l < "$dir/sdsp-directories.txt")" = 1
sdspdir=$(cat "$dir/sdsp-directories.txt")
cp -a "$sdspdir/." "$dir/sdsp/"
test -f "$dir/sdsp/fastrpc_shell_2"
test -d "$dir/mount-persist/sensors"
test -d "$dir/mount-vendor/etc/sensors"
cp -a "$dir/mount-persist/sensors/." "$dir/sensors-persist/"
cp -a "$dir/mount-vendor/etc/sensors/." "$dir/sensors-vendor/"
for path in /sys/devices/soc0/*; do
    test ! -f "$path" || cat "$path" > "$dir/socinfo/$(basename "$path")" 2>/dev/null || true
done
cleanup
sha256sum -c "$dir/sources-before.sha256" > "$dir/sources-after-check.txt"
for name in modem persist dsp vendor; do
    ! grep -q " $dir/mount-$name " /proc/mounts
    rmdir "$dir/mount-$name"
done
dmesg > "$dir/dmesg.txt"
cat /proc/sys/kernel/random/boot_id > "$dir/boot-id-private.txt"
(cd "$dir" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
sync
tar -C /var/lib/samurai -cf "/tmp/k111-$2.tar" "k111-$2"
sha256sum "/tmp/k111-$2.tar"
echo SENSOR_SOURCES_READ_ONLY_COMPLETE
