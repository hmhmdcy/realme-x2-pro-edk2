#!/bin/sh
set -eu
[ "$(cat /proc/sys/kernel/random/boot_id)" = 9141a405-6968-4af3-97d2-e166b957030b ]
[ "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline ]
[ "$(cat /sys/class/remoteproc/remoteproc0/recovery)" = disabled ]
[ "$(cat /sys/module/firmware_class/parameters/path)" = /tmp/k90-firmware ]
kill -0 "$(cat /tmp/k90-tqftpserv.pid)"
[ ! -e /tmp/k90-rmtfs-observer.txt ]
echo 'a30391685526feabcf81a6c5f517d70de1f0a452e3c45dbdcd4441f95e8f6fb0  /tmp/k90-rmtfs-observe' | sha256sum -c -
chmod 755 /tmp/k90-rmtfs-observe
observer_pid=
cleanup() {
    [ "$(cat /sys/class/remoteproc/remoteproc0/state)" != running ] || echo stop > /sys/class/remoteproc/remoteproc0/state
    [ -z "$observer_pid" ] || kill "$observer_pid" 2>/dev/null || true
}
trap cleanup EXIT HUP INT TERM
/tmp/k90-rmtfs-observe > /tmp/k90-rmtfs-observer.txt 2>&1 &
observer_pid=$!
sleep 1
kill -0 "$observer_pid"
grep -q 'RMTFS observer published' /tmp/k90-rmtfs-observer.txt
date -u > /tmp/k90-rmtfs-observer-state.txt
cat /proc/uptime >> /tmp/k90-rmtfs-observer-state.txt
echo start > /sys/class/remoteproc/remoteproc0/state
cat /sys/class/remoteproc/remoteproc0/state >> /tmp/k90-rmtfs-observer-state.txt
sleep 5
/tmp/k90-qrtr-lookup > /tmp/k90-qrtr-observer.txt
wait "$observer_pid"
observer_pid=
echo stop > /sys/class/remoteproc/remoteproc0/state
cat /sys/class/remoteproc/remoteproc0/state >> /tmp/k90-rmtfs-observer-state.txt
cat /proc/sys/kernel/tainted >> /tmp/k90-rmtfs-observer-state.txt
dmesg > /tmp/k90-rmtfs-observer-dmesg.txt
sha256sum /tmp/k90-rmtfs-observer*.txt /tmp/k90-qrtr-observer.txt
cat /tmp/k90-rmtfs-observer-state.txt /tmp/k90-rmtfs-observer.txt /tmp/k90-qrtr-observer.txt
