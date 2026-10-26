#!/bin/sh
set -eu
prefix=/tmp/k91-preflash
[ ! -e "$prefix.tar.gz" ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = 9141a405-6968-4af3-97d2-e166b957030b ]
[ "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline ]
uname -a | grep -q '#89 SMP PREEMPT'
[ "$(cat /sys/class/block/sde/device/model)" = 'KLUDG4UHDB-B2D1 ' ]
grep -qx PARTNAME=boot /sys/class/block/sde11/uevent
grep -qx PARTNAME=logdump /sys/class/block/sde32/uevent
[ "$(cat /sys/class/block/sde11/size)" = 196608 ]
[ "$(cat /sys/class/block/sde32/size)" = 131072 ]
{
 cat /proc/sys/kernel/random/boot_id
 uname -a
 cat /proc/uptime
 cat /proc/sys/kernel/tainted
 cat /sys/class/remoteproc/remoteproc0/state
 ls /sys/class/net
 cat /sys/kernel/debug/dri/1/encoder-0/status
} > "$prefix-state.txt"
for name in snapshot trace; do
 if [ -f "/sys/kernel/tracing/instances/display/$name" ]; then
  cat "/sys/kernel/tracing/instances/display/$name" > "$prefix-$name.txt"
 elif [ -f "/sys/kernel/tracing/$name" ]; then
  cat "/sys/kernel/tracing/$name" > "$prefix-$name.txt"
 else
  echo 'tracefs/instance not configured in this boot; earlier frozen snapshot retained on host' > "$prefix-$name.txt"
 fi
done
cat /sys/kernel/debug/dri/1/state > "$prefix-drm-state.txt"
cat /sys/kernel/debug/dri/1/kms > "$prefix-kms.txt"
dmesg > "$prefix-dmesg.txt"
cat /tmp/k90-rmtfs-observer.txt > "$prefix-observer.txt"
dd if=/dev/sde11 of=/tmp/k91-boot-partition-before.img bs=1048576
dd if=/dev/sde32 of=/tmp/k91-logdump-before.img bs=1048576
{
 cat /proc/sys/kernel/random/boot_id
 head -c 6682624 /dev/sde11 | sha256sum
 sha256sum /dev/sde11 /dev/sde32 /tmp/k91-boot-partition-before.img /tmp/k91-logdump-before.img
} > "$prefix-partition-hashes.txt"
grep -q '^6a9998fd28a9bf1da414b07363bfed7113532ff0cb6d9b1d2371df23e9010a75 ' "$prefix-partition-hashes.txt"
grep -q '^73c7154f3f221c906a49d8077ae98ca5a08fabf3a9bf29ba2c68615d496b5675 ' "$prefix-partition-hashes.txt"
# Read-only NV snapshots. The daemon will accept these regular RAM files only.
mkdir /tmp/k91-nv
: > /tmp/k91-nv-source-hashes.txt
for spec in sdf4:modemst1:modem_fs1 sdf5:modemst2:modem_fs2 sdf11:fsg:modem_fsg sdf12:fsc:modem_fsc sdf3:oppostanvbk:oem_stanvbk sdf2:oppodycnvbk:oem_dycnvbk; do
 dev=${spec%%:*}; rest=${spec#*:}; label=${rest%%:*}; file=${rest#*:}
 grep -qx "PARTNAME=$label" "/sys/class/block/$dev/uevent"
 sectors=$(cat "/sys/class/block/$dev/size")
 [ "$sectors" -gt 0 ] && [ "$sectors" -le 32768 ]
 dd "if=/dev/$dev" "of=/tmp/k91-nv/$file" bs=512
 [ "$(wc -c < "/tmp/k91-nv/$file")" -eq "$((sectors * 512))" ]
 before=$(sha256sum "/dev/$dev" | cut -d ' ' -f1)
 copy=$(sha256sum "/tmp/k91-nv/$file" | cut -d ' ' -f1)
 [ "$before" = "$copy" ]
 echo "$before  /dev/$dev" >> /tmp/k91-nv-source-hashes.txt
done
(cd /tmp/k91-nv && sha256sum *) > /tmp/k91-nv-SHA256SUMS
tar -cf /tmp/k91-nv-snapshots.tar -C /tmp/k91-nv .
sha256sum /tmp/k91-nv-snapshots.tar /tmp/k91-nv-SHA256SUMS /tmp/k91-nv-source-hashes.txt > /tmp/k91-nv-archive-hashes.txt
sha256sum "$prefix"-*.txt > "$prefix-hashes.txt"
tar -cf "$prefix.tar" "$prefix"-*.txt
gzip -c "$prefix.tar" > "$prefix.tar.gz"
sha256sum "$prefix.tar.gz"
cat "$prefix-state.txt" "$prefix-partition-hashes.txt" /tmp/k91-nv-archive-hashes.txt
