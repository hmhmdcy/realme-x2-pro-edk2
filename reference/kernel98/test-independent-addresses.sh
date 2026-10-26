#!/bin/sh
# Controlled query fault injection, then real DMS queries; no pairing/power-on.
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#96 SMP PREEMPT'
base=/run/samurai-radio-address
dir=/tmp/k98-independent-addresses
service=/tmp/k98-samurai-radio-address
helper=/usr/sbin/samurai-dms-mac-read
saved=/tmp/k98-original-dms-mac-read
test ! -e "$dir" && test ! -e "$saved"
test ! -e "$base/current-wlan" && test ! -e "$base/current-bt"
test ! -e "$base/request.lock"
[ "$(cat /sys/class/remoteproc/remoteproc0/state)" = running ]
mkdir -m700 "$dir"
cp -a "$base" "$dir/cache-before"
sha256sum "$helper" > "$dir/helper-before.sha"
cat /sys/class/net/wlan0/address > "$dir/wlan-before.txt"
cat /sys/kernel/debug/dri/1/encoder-0/status > "$dir/display-before.txt"
chmod 700 "$service"
restore()
{
    result=$?
    set +e
    if test -e "$saved"; then mv "$saved" "$helper"; fi
    sha256sum -c "$dir/helper-before.sha" > "$dir/helper-restore.txt"
    echo "$result" > "$dir/exit-status.txt"
    cp -a "$base" "$dir/cache-after"
    dmesg > "$dir/dmesg-after.txt"
    cat /sys/kernel/debug/dri/1/encoder-0/status > "$dir/display-after.txt"
    (cd "$dir" && find . -type f ! -path './SHA256SUMS' -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
    tar -C /tmp -cf /tmp/k98-independent-addresses.tar k98-independent-addresses
    sha256sum /tmp/k98-independent-addresses.tar
    exit "$result"
}
trap restore EXIT
mv "$helper" "$saved"
cat > "$helper" <<'WRAPPER'
#!/bin/sh
if [ "$1" = wlan ]; then echo INJECTED_WLAN_QUERY_FAILURE >&2; exit 42; fi
exec /tmp/k98-original-dms-mac-read "$@"
WRAPPER
chmod 700 "$helper"
if "$service" refresh wlan > "$dir/wlan-injected-failure.txt" 2>&1; then exit 1; else code=$?; fi
[ "$code" = 42 ]
echo "$code" > "$dir/wlan-injected-exit.txt"
test ! -e "$base/current-wlan" && test ! -e "$base/current-bt"
"$service" status > "$dir/after-wlan-failure.txt"
"$service" refresh bt > "$dir/bt-fresh-query.txt" 2>&1
test ! -e "$base/current-wlan" && test -f "$base/current-bt"
"$service" bt > "$dir/bt-idempotent.txt" 2>&1
"$service" status > "$dir/after-bt-query.txt"
mv "$saved" "$helper"
sha256sum -c "$dir/helper-before.sha" > "$dir/helper-restored-before-wlan.txt"
"$service" refresh wlan > "$dir/wlan-fresh-query.txt" 2>&1
"$service" wlan > "$dir/wlan-idempotent.txt" 2>&1
"$service" status > "$dir/final-address-status.txt"
cat /sys/class/net/wlan0/address > "$dir/wlan-after.txt"
cmp "$dir/wlan-before.txt" "$dir/wlan-after.txt"
/tmp/k97-bt-mgmt-probe info > "$dir/bt-final.txt"
wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status > "$dir/wpa-final.txt"
grep -qx wpa_state=COMPLETED "$dir/wpa-final.txt"
grep -qx freq=5180 "$dir/wpa-final.txt"
cat /proc/sys/kernel/random/boot_id /proc/uptime /proc/sys/kernel/tainted /sys/class/remoteproc/remoteproc0/state > "$dir/state.txt"
echo INDEPENDENT_QUERY_FAILURE_ISOLATION_PASS > "$dir/result.txt"
