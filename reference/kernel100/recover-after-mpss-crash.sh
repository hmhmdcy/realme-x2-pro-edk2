#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#99 SMP PREEMPT'
[ "$(cat /sys/class/remoteproc/remoteproc0/state)" = crashed ]
grep -qx 1 /run/samurai-wifi/boot-finished
test -f /tmp/k100-first-boot-failure/SHA256SUMS
dir=/tmp/k100-radio-recovery-first
test ! -e "$dir"
mkdir -m700 "$dir"
dmesg > "$dir/dmesg-before.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-before.txt"
for spec in tftp:samurai-tqftpserv rmtfs:samurai-rmtfs-cow; do
    file=${spec%%:*};name=${spec#*:}
    pid=$(cat "/run/samurai-wifi/$file.pid")
    case "$pid" in ''|*[!0-9]*) exit 1;; esac
    tr '\0' ' ' < "/proc/$pid/cmdline" | grep -q "^/usr/sbin/$name"
    kill -0 "$pid"
done
/usr/sbin/samurai-bluetooth stop > "$dir/bt-stop.txt" 2>&1
if test -e /sys/bus/platform/drivers/ath10k_snoc/18800000.wifi; then
    echo 18800000.wifi > /sys/bus/platform/drivers/ath10k_snoc/unbind
    echo WLAN_UNBOUND > "$dir/wlan-stop.txt"
fi
echo stop > /sys/class/remoteproc/remoteproc0/state
[ "$(cat /sys/class/remoteproc/remoteproc0/state)" = offline ]
echo MPSS_STOPPED > "$dir/mpss-stop.txt"
if ! test -e /sys/bus/platform/drivers/ath10k_snoc/18800000.wifi; then
    echo 18800000.wifi > /sys/bus/platform/drivers/ath10k_snoc/bind
fi
echo start > /sys/class/remoteproc/remoteproc0/state
for attempt in $(seq 1 60); do
    [ "$(cat /sys/class/remoteproc/remoteproc0/state)" = running ]
    test ! -e /sys/class/net/wlan0 || break
    sleep 1
done
test -e /sys/class/net/wlan0
for attempt in $(seq 1 45); do
    [ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
    [ "$(cat /sys/class/remoteproc/remoteproc0/state)" = running ]
    [ "$(cat /proc/sys/kernel/tainted)" = 0 ]
    sleep 1
done
/usr/sbin/samurai-radio-address wlan > "$dir/wlan-address.txt"
ip link set wlan0 up
cp /etc/samurai-wifi/wpa-empty.conf /run/samurai-wifi/wpa.conf
nohup /usr/sbin/wpa_supplicant -Dnl80211 -iwlan0 -c/run/samurai-wifi/wpa.conf > /run/samurai-wifi/wpa.log 2>&1 < /dev/null &
echo $! > /run/samurai-wifi/wpa.pid
for attempt in $(seq 1 10); do
    if /usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 ping | grep -qx PONG; then break; fi
    sleep 1
done
/usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 ping | grep -qx PONG
touch /run/samurai-wifi/ready
# Preserve the failed automatic boot-finished=1 and both original boot logs.
/usr/sbin/samurai-bluetooth start > "$dir/bt-start.txt" 2>&1
/usr/sbin/samurai-radio-address status > "$dir/address-status.txt"
/tmp/k100-bt-mgmt-probe info > "$dir/bt-info.txt"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-after.txt"
dmesg > "$dir/dmesg-after.txt"
{
    cat /proc/sys/kernel/random/boot_id /proc/uptime /proc/sys/kernel/tainted
    cat /sys/class/remoteproc/remoteproc0/state
} > "$dir/state.txt"
echo BOUNDED_MANUAL_RECOVERY_AFTER_AUTO_MPSS_CRASH_PASS > "$dir/result.txt"
(cd "$dir" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
tar -C /tmp -cf /tmp/k100-radio-recovery-first.tar k100-radio-recovery-first
sha256sum /tmp/k100-radio-recovery-first.tar
