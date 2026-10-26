#!/bin/sh
set -eu
umask 077
dest=/var/lib/samurai/k128-keytrace-postflash
instance=/sys/kernel/tracing/instances/k128-keytrace-postflash
test ! -e "$dest" && test ! -e "$instance"
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k128-postflash-wifi-baseline/boot-id-private.txt)"
test "$(cat /sys/module/ath10k_core/parameters/debug_mask)" = 0
mkdir -m700 "$dest"
mkdir "$instance"
finish() {
    rc=$?
    trap - EXIT HUP INT TERM
    set +e
    echo 0 > "$instance/tracing_on"
    cat "$instance/trace" > "$dest/trace-private.txt"
    for file in "$instance"/per_cpu/cpu*/stats; do cat "$file"; done > "$dest/trace-stats.txt"
    echo "$rc" > "$dest/exit.txt"
    cat /sys/module/ath10k_core/parameters/debug_mask > "$dest/debug-mask.txt"
    echo 0 > "$instance/events/enable"
    rmdir "$instance"
    (cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
    tar -C "$dest" -czf /tmp/k128-keytrace-postflash-private.tar.gz .
    echo K128_CURRENT_KEY_DELETE_BASELINE_TRACE_CLOSED_PRIVATE_SAVED
    exit "$rc"
}
trap finish EXIT HUP INT TERM
echo 0 > "$instance/tracing_on"
echo 1024 > "$instance/buffer_size_kb"
echo mono > "$instance/trace_clock"
echo 'msg ~ "sec ind*" || msg ~ "wmi tlv vdev install key*"' > "$instance/events/ath10k/ath10k_log_dbg/filter"
for event in ath10k/ath10k_log_dbg mac80211/drv_set_key mac80211/drv_return_int; do
    cp "$instance/events/$event/format" "$dest/$(echo "$event" | tr / _)-format.txt"
    echo 1 > "$instance/events/$event/enable"
done
echo 1 > "$instance/tracing_on"
sh /tmp/k128-test-postflash-5ghz.sh > "$dest/inner-result.txt" 2>&1
