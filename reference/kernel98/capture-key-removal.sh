#!/bin/sh
# Bounded trace-only baseline: no firmware/key data, kernel or NV modification.
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#96 SMP PREEMPT'
dir=/tmp/k98-key-removal
instance=/sys/kernel/tracing/instances/k98-key-removal
test ! -e "$dir" && test ! -e "$instance"
/usr/sbin/samurai-radio-address bt > /tmp/k98-key-removal-bt-check.txt
grep -qx 'BT_ADDRESS_VERIFIED index=0 powered=0 connectable=0 bondable=0' /tmp/k98-key-removal-bt-check.txt
mkdir -m700 "$dir"
mkdir "$instance"
finish()
{
    result=$?
    set +e
    echo 0 > "$instance/tracing_on"
    cat "$instance/trace" > "$dir/trace.txt"
    for file in "$instance"/per_cpu/cpu*/stats; do echo "$file"; cat "$file"; done > "$dir/trace-stats.txt"
    dmesg > "$dir/dmesg-after.txt"
    cp /run/samurai-wifi/wpa.log "$dir/wpa-after.log"
    cat /sys/kernel/debug/dri/1/encoder-0/status > "$dir/display-after.txt"
    echo "$result" > "$dir/exit-status.txt"
    (cd "$dir" && find . -type f ! -path './SHA256SUMS' -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
    tar -C /tmp -cf /tmp/k98-key-removal.tar k98-key-removal
    sha256sum /tmp/k98-key-removal.tar
    echo 0 > "$instance/events/enable"
    rmdir "$instance"
    exit "$result"
}
trap finish EXIT
echo 0 > "$instance/tracing_on"
echo 1024 > "$instance/buffer_size_kb"
echo mono > "$instance/trace_clock"
for event in mac80211/drv_set_key dpu/dpu_enc_frame_done_timeout dpu/dpu_enc_frame_watchdog; do
    cp "$instance/events/$event/format" "$dir/$(echo "$event" | tr / _)-format.txt"
    echo 1 > "$instance/events/$event/enable"
done
cli() { /usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 "$@"; }
cli status > "$dir/wpa-before.txt"
grep -qx wpa_state=COMPLETED "$dir/wpa-before.txt"
grep -qx freq=5180 "$dir/wpa-before.txt"
dmesg > "$dir/dmesg-before.txt"
cp /run/samurai-wifi/wpa.log "$dir/wpa-before.log"
cat /sys/kernel/debug/dri/1/encoder-0/status > "$dir/display-before.txt"
echo 1 > "$instance/tracing_on"
echo 'K98_BT_OFF_WIFI_DISCONNECT_REQUEST' > "$instance/trace_marker"
cli disconnect | grep -qx OK
for attempt in $(seq 1 15); do
    cli status > "$dir/wpa-disconnected.txt"
    grep -qx wpa_state=DISCONNECTED "$dir/wpa-disconnected.txt" && break
    sleep 1
done
grep -qx wpa_state=DISCONNECTED "$dir/wpa-disconnected.txt"
sleep 4
echo 'K98_BT_OFF_WIFI_RECONNECT_REQUEST' > "$instance/trace_marker"
cli reconnect | grep -qx OK
for attempt in $(seq 1 30); do
    cli status > "$dir/wpa-after.txt"
    grep -qx wpa_state=COMPLETED "$dir/wpa-after.txt" && break
    sleep 2
done
grep -qx wpa_state=COMPLETED "$dir/wpa-after.txt"
grep -qx freq=5180 "$dir/wpa-after.txt"
udhcpc -i wlan0 -s /usr/sbin/samurai-udhcpc-wlan -n -q -t 5 -T 3 > "$dir/dhcp.txt" 2>&1
gateway=$(ip route show dev wlan0 | awk '/^default / {print $3; exit}')
test -n "$gateway"
ping -I wlan0 -c2 -W2 "$gateway" > "$dir/gateway.txt"
echo 'K98_WIFI_AUTH_DHCP_GATEWAY_RESTORED' > "$instance/trace_marker"
cat /proc/sys/kernel/random/boot_id /proc/uptime /proc/sys/kernel/tainted /sys/class/remoteproc/remoteproc0/state > "$dir/state.txt"
echo KEY_REMOVAL_BASELINE_CAPTURE_PASS > "$dir/result.txt"
