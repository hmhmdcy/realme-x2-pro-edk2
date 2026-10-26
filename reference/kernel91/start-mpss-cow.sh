#!/bin/sh
set -eu
[ "$(cat /proc/sys/kernel/random/boot_id)" = dfe8e722-f6b7-4ce8-85cc-17dfba80f69d ]
[ "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline ]
[ ! -e /tmp/k91-rmtfs-cow.txt ]
echo '38b4d930f50fc02193388cdc4d8fa1146ea6a53f515d3185696551d293ade846  /tmp/k91-rmtfs-cow' | sha256sum -c -
echo 'e4bf2dd89453471849ddee3602ae378602a300c24e62eb46d27c0d14908b8f84  /tmp/k91-nv-snapshots.tar' | sha256sum -c -
echo '2712ab15bc76642a2b918f27cb018af49341873f5d06f64e081412361f6a0850  /tmp/k91-nv-SHA256SUMS' | sha256sum -c -
sha256sum -c /tmp/k91-nv-source-hashes.txt > /tmp/k91-nv-before-start-check.txt
mkdir -m 700 /tmp/k91-nv
tar -xf /tmp/k91-nv-snapshots.tar -C /tmp/k91-nv
(cd /tmp/k91-nv && sha256sum -c /tmp/k91-nv-SHA256SUMS) > /tmp/k91-nv-files-check.txt
chmod 755 /tmp/k91-rmtfs-cow /tmp/k91-iw
echo disabled > /sys/class/remoteproc/remoteproc0/recovery
/tmp/k91-rmtfs-cow > /tmp/k91-rmtfs-cow.txt 2>&1 &
pid=$!
echo "$pid" > /tmp/k91-rmtfs-cow.pid
sleep 1
kill -0 "$pid"
grep -q 'RMTFS RAM COW ready' /tmp/k91-rmtfs-cow.txt
kill -0 "$(cat /tmp/k91-tqftpserv.pid)"
dmesg > /tmp/k91-before-mpss-dmesg.txt
echo start > /sys/class/remoteproc/remoteproc0/state
cat /proc/uptime > /tmp/k91-mpss-start-state.txt
cat /sys/class/remoteproc/remoteproc0/state >> /tmp/k91-mpss-start-state.txt
sleep 5
/tmp/k91-qrtr-lookup > /tmp/k91-qrtr-after-start.txt
dmesg > /tmp/k91-after-mpss-dmesg.txt
sha256sum /tmp/k91-before-mpss-dmesg.txt /tmp/k91-after-mpss-dmesg.txt
cat /tmp/k91-mpss-start-state.txt /tmp/k91-qrtr-after-start.txt
ls /sys/class/net
tail -15 /tmp/k91-rmtfs-cow.txt
tail -15 /tmp/k91-after-mpss-dmesg.txt
