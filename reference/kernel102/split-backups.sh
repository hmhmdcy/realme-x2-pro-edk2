#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#100 SMP PREEMPT'
dir=/tmp/k102-backup-chunks
test ! -e "$dir"
mkdir -m700 "$dir"
for spec in boot:48 logdump:32; do
    name=${spec%%:*};count=${spec#*:}
    if [ "$name" = boot ]; then source=/tmp/k102-boot-partition-before.img; else source=/tmp/k102-logdump-before.img; fi
    [ "$(wc -c < "$source")" = "$((count*2097152))" ]
    for index in $(seq 0 "$((count-1))"); do
        suffix=$(printf '%03d' "$index")
        dd "if=$source" "of=$dir/$name-$suffix.bin" bs=2097152 skip="$index" count=1 2>/dev/null
        [ "$(wc -c < "$dir/$name-$suffix.bin")" = 2097152 ]
    done
done
(cd "$dir" && sha256sum *.bin) > "$dir/SHA256SUMS"
echo COMPLETE_BACKUPS_SPLIT_IN_RAM
