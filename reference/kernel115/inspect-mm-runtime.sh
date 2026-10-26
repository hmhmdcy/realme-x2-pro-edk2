#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k115-mm-diagnostic2
test ! -e "$dest"
mkdir -m700 "$dest"
uname -v | grep -q '^#115 '
qrtr-lookup > "$dest/qrtr.txt"
ldd /usr/sbin/ModemManager > "$dest/libraries.txt"
strings /usr/sbin/ModemManager | grep -i qrtr > "$dest/qrtr-build.txt" || true
ps -eo pid,user,args > "$dest/processes-before-private.txt"
pid=$(pidof ModemManager)
test -n "$pid"
test "$(readlink /proc/$pid/exe)" = "$(readlink -f /usr/sbin/ModemManager)"
kill -TERM "$pid"
for attempt in 1 2 3 4 5; do test ! -d "/proc/$pid" && break; sleep 1; done
test ! -d "/proc/$pid"
/usr/sbin/ModemManager --debug > "$dest/mm-debug-private.txt" 2>&1 &
diagnostic=$!
echo "$diagnostic" > "$dest/pid.txt"
sleep 30
mmcli --list-modems > "$dest/modems-private.txt" 2>&1 || true
kill -TERM "$diagnostic"
wait "$diagnostic" || true
test ! -d "/proc/$diagnostic"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dest/nv-check.txt"
tar -C "$dest" -czf /tmp/k115-mm-diagnostic2-private.tar.gz .
sha256sum /tmp/k115-mm-diagnostic2-private.tar.gz
echo KERNEL115_MM_BOUNDED_DIAGNOSTIC_SAVED
