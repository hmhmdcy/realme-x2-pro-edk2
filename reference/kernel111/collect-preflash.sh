#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#109 SMP PREEMPT'
grep -q '^/dev/sda16 / f2fs rw' /proc/mounts
dir=/var/lib/samurai/k111-preflash
test ! -e "$dir"
mkdir -m700 "$dir"
cat /proc/sys/kernel/random/boot_id > "$dir/boot-id-private.txt"
cat /proc/uptime /proc/sys/kernel/tainted > "$dir/state.txt"
cat /proc/mounts > "$dir/mounts.txt"
grep -q ' /run tmpfs rw' "$dir/mounts.txt"
sha256sum /dev/sde11 /dev/sde32 /dev/sda2 > "$dir/boot-logdump-persist.sha256"
grep -q '^d1f81ebc4dc9687b705cffe38ecde93b8c4cd60a4c37463901b7cf7b900e1278 ' "$dir/boot-logdump-persist.sha256"
grep -q '^f2d073047a3b719ff8dd5ef0fa2adae13a92478f13bf23031f88f91cbf496707 ' "$dir/boot-logdump-persist.sha256"
grep -q '^7e085ef3264e212da7009099113b86ad1f6ec44176840f03f9b85d0e632412f3 ' "$dir/boot-logdump-persist.sha256"
cp /run/samurai-wifi/nv-source-hashes.txt "$dir/"
sha256sum -c "$dir/nv-source-hashes.txt" > "$dir/nv-check.txt"
dmesg > "$dir/dmesg.txt"
ps -eo pid,user,args > "$dir/processes.txt"
rc-status -a > "$dir/openrc.txt"
cp /var/log/rc.log "$dir/"
for node in /sys/class/remoteproc/*; do cat "$node/name" "$node/state"; done > "$dir/remoteproc.txt"
cp /run/k111-sensor-sources-still-unchanged.txt /run/k111-module-package-check.txt "$dir/"
cp /home/cy122/.local/state/samurai-phosh-session.log "$dir/phosh-session.txt"
sync
(cd "$dir" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
tar -C /var/lib/samurai -cf /tmp/k111-preflash.tar k111-preflash
sha256sum /tmp/k111-preflash.tar
echo KERNEL111_CURRENT_BACKUPS_MATCH_PERSIST_NV_CHECKPOINT_COMPLETE
