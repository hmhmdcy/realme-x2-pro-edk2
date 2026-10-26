#!/bin/sh
set -eu
umask 077
prefix=${1:?fresh prefix required}
case "$prefix" in *[!a-z0-9-]*|'') exit 2;; esac
uname -v | grep -q '^#115 '
grep -q '^/dev/sda16 / f2fs rw' /proc/mounts
dest=/var/lib/samurai/k115-$prefix
test ! -e "$dest"
mkdir -m700 "$dest"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
uname -a > "$dest/uname.txt"
cat /proc/uptime /proc/sys/kernel/tainted > "$dest/state.txt"
cat /proc/mounts > "$dest/mounts.txt"
cat /etc/samurai-rootfs-release /var/lib/samurai/persistence-test.txt > "$dest/rootfs-release.txt"
dmesg > "$dest/dmesg.txt"
rc-status -a > "$dest/openrc.txt"
ps -eo pid,user,args > "$dest/processes.txt"
test ! -f /var/log/rc.log || cp /var/log/rc.log "$dest/"
for node in /sys/class/remoteproc/*; do
    cat "$node/name" "$node/state"
    cat "$node/firmware"
done > "$dest/remoteprocs.txt"
sha256sum /dev/sde11 /dev/sde32 /dev/sda2 > "$dest/partition-check.sha256"
cp /run/samurai-wifi/nv-source-hashes.txt "$dest/"
sha256sum -c "$dest/nv-source-hashes.txt" > "$dest/nv-check.txt"
sha256sum -c /var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256 > "$dest/source-check.txt"
cat /sys/devices/platform/sensor-power/state > "$dest/power-state.txt"
cat /sys/kernel/debug/regulator/regulator_summary > "$dest/regulators.txt"
cat /sys/firmware/fdt > "$dest/live-fdt-private.dtb"
cat /sys/kernel/debug/devices_deferred > "$dest/deferred.txt" 2>/dev/null || true
for node in /sys/class/drm/card*-DSI-*; do
    test -d "$node" || continue
    cat "$node/status" "$node/enabled" "$node/modes" > "$dest/$(basename "$node").txt"
done
for file in /sys/kernel/debug/dri/*/state; do
    test -f "$file" || continue
    cat "$file" > "$dest/drm-$(basename "$(dirname "$file")")-state.txt"
done
test ! -f /home/cy122/.local/state/samurai-phosh-session.log || cp /home/cy122/.local/state/samurai-phosh-session.log "$dest/phosh-session.txt"
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -cf "/tmp/k115-$prefix.tar" .
sha256sum "/tmp/k115-$prefix.tar"
echo KERNEL115_RUNTIME_CHECKPOINT_SAVED
