#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#97 SMP PREEMPT'
grep -qx AUTO_INDEPENDENT_ADDRESSES_BOOT_PASS /tmp/k98-automatic-addresses/result.txt
chmod 700 /tmp/k98-bt-mgmt-probe-window
dir=/tmp/k98-trace-connectivity
instance=/sys/kernel/tracing/instances/k98-connectivity
test ! -e "$dir" && test ! -e "$instance"
mkdir -m700 "$dir"
mkdir "$instance"
scan_pid=
finish()
{
    result=$?
    set +e
    if test -n "$scan_pid"; then kill "$scan_pid"; wait "$scan_pid"; fi
    /tmp/k98-bt-mgmt-probe off > "$dir/bt-final-off.txt"
    /tmp/k98-bt-mgmt-probe info > "$dir/bt-final-info.txt"
    echo 0 > "$instance/tracing_on"
    cat "$instance/trace" > "$dir/trace.txt"
    for file in "$instance"/per_cpu/cpu*/stats; do echo "$file"; cat "$file"; done > "$dir/trace-stats.txt"
    dmesg > "$dir/dmesg-after.txt"
    cp /run/samurai-wifi/wpa.log "$dir/wpa-after.log"
    cat /sys/kernel/debug/dri/1/encoder-0/status > "$dir/display-after.txt"
    echo "$result" > "$dir/exit-status.txt"
    (cd "$dir" && find . -type f ! -path './SHA256SUMS' -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
    tar -C /tmp -cf /tmp/k98-trace-connectivity.tar k98-trace-connectivity
    sha256sum /tmp/k98-trace-connectivity.tar
    echo 0 > "$instance/events/enable"
    rmdir "$instance"
    exit "$result"
}
trap finish EXIT
echo 0 > "$instance/tracing_on"
echo 1024 > "$instance/buffer_size_kb"
echo mono > "$instance/trace_clock"
# Exclude raw WMI/HTT packets and key dumps. debug_mask remains zero.
echo 'msg ~ "sec ind*" || msg ~ "wmi tlv vdev install key*"' > "$instance/events/ath10k/ath10k_log_dbg/filter"
for event in ath10k/ath10k_log_dbg mac80211/drv_set_key mac80211/drv_return_int dpu/dpu_enc_frame_done_timeout dpu/dpu_enc_frame_watchdog; do
    cp "$instance/events/$event/format" "$dir/$(echo "$event" | tr / _)-format.txt"
    echo 1 > "$instance/events/$event/enable"
done
cat /sys/module/ath10k_core/parameters/debug_mask > "$dir/debug-mask.txt"
grep -qx 0 "$dir/debug-mask.txt"
cli() { /usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 "$@"; }
connected()
{
    for attempt in $(seq 1 30); do
        cli status > "$dir/$1-status.txt"
        grep -qx wpa_state=COMPLETED "$dir/$1-status.txt" && break
        sleep 2
    done
    grep -qx wpa_state=COMPLETED "$dir/$1-status.txt"
}
network()
{
    udhcpc -i wlan0 -s /usr/sbin/samurai-udhcpc-wlan -n -q -t 5 -T 3 > "$dir/$1-dhcp.txt" 2>&1
    gateway=$(ip route show dev wlan0 | awk '/^default / {print $3; exit}')
    test -n "$gateway"
    ping -I wlan0 -c2 -W2 "$gateway" > "$dir/$1-gateway.txt"
}
dmesg > "$dir/dmesg-before.txt"
cat /sys/kernel/debug/dri/1/encoder-0/status > "$dir/display-before.txt"
echo 1 > "$instance/tracing_on"
echo 'K98_TWO_GHZ_AUTH_BEGIN_BT_OFF' > "$instance/trace_marker"
cp /tmp/k98-wpa-test-private.conf /run/samurai-wifi/wpa.conf
chmod 600 /run/samurai-wifi/wpa.conf
cli reconfigure | grep -qx OK
connected initial
grep -qx freq=2462 "$dir/initial-status.txt"
network initial
echo 'K98_TWO_GHZ_AUTH_DHCP_GATEWAY_PASS' > "$instance/trace_marker"
/tmp/k98-bt-mgmt-probe configure > "$dir/bt-scan-configure.txt"
/tmp/k98-bt-mgmt-probe info > "$dir/bt-scan-info.txt"
echo 'K98_INITIAL_BT_SCAN_BEGIN' > "$instance/trace_marker"
/tmp/k98-bt-mgmt-probe-window scan 100 > "$dir/bt-scan.txt" &
scan_pid=$!
for sample in $(seq 1 45); do
    kill -0 "$scan_pid"
    cli status > "$dir/coexistence-current.txt"
    state=$(sed -n 's/^wpa_state=//p' "$dir/coexistence-current.txt")
    printf 'sample=%s uptime=%s WPA=%s MPSS=%s taint=%s\n' "$sample" "$(cut -d ' ' -f1 /proc/uptime)" "$state" "$(cat /sys/class/remoteproc/remoteproc0/state)" "$(cat /proc/sys/kernel/tainted)" >> "$dir/coexistence-samples.txt"
    sleep 2
done
wait "$scan_pid"
scan_pid=
connected after-scan
network after-scan
echo 'K98_AFTER_SCAN_NETWORK_RESTORED_OR_RETAINED' > "$instance/trace_marker"
/tmp/k98-bt-mgmt-probe off > "$dir/bt-off-before-removal.txt"
echo 'K98_PAIRWISE_REMOVAL_REQUEST_BT_OFF' > "$instance/trace_marker"
cli disconnect | grep -qx OK
sleep 10
echo 'K98_RECONNECT_REQUEST_BT_OFF' > "$instance/trace_marker"
cli reconnect | grep -qx OK
connected reconnect
network reconnect
echo 'K98_RECONNECT_AUTH_DHCP_GATEWAY_PASS' > "$instance/trace_marker"
cli set_network 0 freq_list 5180 | grep -qx OK
cli select_network 0 | grep -qx OK
cli reassociate | grep -qx OK
connected five-ghz
grep -qx freq=5180 "$dir/five-ghz-status.txt"
network five-ghz
echo 'K98_FIVE_GHZ_AUTH_DHCP_GATEWAY_PASS' > "$instance/trace_marker"
cat /proc/sys/kernel/random/boot_id /proc/uptime /proc/sys/kernel/tainted /sys/class/remoteproc/remoteproc0/state > "$dir/state.txt"
echo TRACE_CONNECTIVITY_CAPTURE_PASS > "$dir/result.txt"
