#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k172-quiesce
# Resume only the unexecuted receipt tail after the checker upload was fixed.
python3 /tmp/k172-check-quiesce.py --record
cat /proc/uptime /proc/sys/kernel/tainted > "$dest/state.txt"
dmesg > "$dest/dmesg-after.txt"
sync
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -cf /tmp/k172-quiesce-private.tar .
echo K172_CURRENT168_PREFLASH_QUIESCE_COMPLETE
