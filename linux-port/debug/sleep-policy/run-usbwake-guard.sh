#!/bin/sh
# Run a debug-only sleep-inhibitor instance with the USBwake guard.
set -eu

here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
mode=${USBWAKE_GUARD_MODE:-either}
if [ -n "${USBWAKE_CONFIG:-}" ]; then
	config=$USBWAKE_CONFIG
	temp_config=0
	[ -r "$config" ] || {
		echo "cannot read USBWAKE_CONFIG=$config" >&2
		exit 1
	}
else
	config=$(mktemp)
	temp_config=1

	cat >"$config" <<EOF
plugins:
  - path: $here/usbwake-guard
    name: USBwake power/NCM guard (debug only)
    period: .1
    what: sleep
EOF
fi

export USBWAKE_GUARD_MODE="$mode"
if command -v setsid >/dev/null 2>&1; then
	setsid sleep-inhibitor --config "$config" &
else
	sleep-inhibitor --config "$config" &
fi
pid=$!

cleanup() {
	# sleep-inhibitor forks elogind-inhibit. setsid gives the whole helper
	# a private process group so a failed debug run cannot leave a sleep
	# lock behind.
	kill -TERM -"$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null || true
	for _ in 1 2 3 4 5; do
		kill -0 "$pid" 2>/dev/null || break
		sleep 1
	done
	kill -KILL -"$pid" 2>/dev/null || kill -KILL "$pid" 2>/dev/null || true
	wait "$pid" 2>/dev/null || true
	if [ "$temp_config" -eq 1 ]; then
		rm -f "$config"
	fi
}
trap cleanup 0 1 2 15

wait "$pid"
