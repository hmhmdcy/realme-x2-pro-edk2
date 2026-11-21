#!/bin/sh
# Measure per-band Wi-Fi round-trip latency on the Realme X2 Pro.
#
# This is a read-only measurement.  It does not write any NetworkManager
# profile: it re-reads the current association, so run it once while the phone
# is on 2.4 GHz and once while it is on 5 GHz.
#
# Thresholds come from the 2026-11-20 measurement on SM8150/WCN3990:
#   2.4 GHz, -46 dBm, 40 MHz HT :  avg 11-26 ms, 0 % loss
#   5 GHz,   -62 dBm, 80 MHz VHT:  avg 560-720 ms, 0-40 % loss
# The 5 GHz side is a known open defect (see
# linux-port/docs/WIFI-BAND-LATENCY-20261120.md), so this script reports a
# RESULT line instead of failing the build: it is a probe, not a gate for the
# whole image.
set -u

dev=${1:-wlan0}
count=${2:-25}
target=${3:-192.168.0.1}
max_avg_ms=${SAMURAI_WIFI_MAX_AVG_MS:-120}

fail=0
bad() { echo "FAIL: $*"; fail=1; }
ok() { echo "ok: $*"; }

[ -e "/sys/class/net/$dev" ] || { echo "RESULT: no $dev; skipped"; exit 2; }

link=$(iw dev "$dev" link 2>/dev/null)
case "$link" in
*Connected*) ;;
*) echo "RESULT: $dev not associated; skipped"; exit 2 ;;
esac

freq=$(printf '%s\n' "$link" | sed -n 's/^\s*freq: \([0-9.]*\).*/\1/p')
band=unknown
if [ -n "$freq" ]; then
	# take the integer part; busybox test does not compare 2462.0 numerically
	freq_int=$(printf '%s\n' "$freq" | cut -d. -f1)
	if [ "$freq_int" -lt 3000 ] 2>/dev/null; then
		band=2.4GHz
	else
		band=5GHz
	fi
fi

echo "== association =="
printf '%s\n' "$link" | sed -n 's/^/  /p' | grep -E \
	'^\s+(Connected to|SSID|freq|signal|rx bitrate)' || true

echo "== latency to $target ($count probes) =="
ping -c "$count" -i 0.2 -W 3 "$target" >/tmp/samurai-wifi-latency.$$ 2>&1
rc=$?
tail -n 2 /tmp/samurai-wifi-latency.$$ | sed 's/^/  /'

# ping prints "min/avg/max", so the middle field is the average.
loss=$(grep -o '[0-9]\+% packet loss' /tmp/samurai-wifi-latency.$$ |
	sed 's/% packet loss//' | tail -n 1)
avg=$(sed -n 's/.*= [0-9.]*\/\([0-9.]*\)\/[0-9.]* ms.*/\1/p' /tmp/samurai-wifi-latency.$$ | tail -n 1)
[ -n "$avg" ] || avg=99999
[ -n "$loss" ] || loss=100
rm -f /tmp/samurai-wifi-latency.$$

echo "  band=$band freq=${freq:-?} loss=${loss}% avg=${avg}ms"

case "$band" in
2.4GHz)
	awk -v a="$avg" -v m="$max_avg_ms" 'BEGIN{exit (a<=m)?0:1}' &&
		ok "2.4 GHz latency ${avg}ms <= ${max_avg_ms}ms" ||
		bad "2.4 GHz latency ${avg}ms > ${max_avg_ms}ms"
	[ "$loss" -le 5 ] &&
		ok "2.4 GHz loss ${loss}% <= 5%" ||
		bad "2.4 GHz loss ${loss}% > 5%"
	;;
5GHz)
	echo "note: 5 GHz is the open defect; ${avg}ms is expected to be ~500-700ms"
	[ "$rc" -eq 0 ] || echo "note: ping exited $rc"
	;;
*)
	bad "unknown band for freq ${freq:-?}"
	;;
esac

echo "RESULT: band=$band loss=${loss}% avg=${avg}ms failures=$fail"
