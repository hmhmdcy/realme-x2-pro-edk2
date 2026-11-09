#!/bin/sh
# Read-only provenance check for the retired USB carrier sleep guard.
# The guard is debug-only; production must use the official
# /etc/sleep-inhibitor.conf and the upstream sleep-inhibitor service.
set -eu

failures=0
ok()
{
	echo "ok: $*"
}
bad()
{
	echo "FAIL: $*" >&2
	failures=$((failures + 1))
}

[ -e /usr/libexec/samurai-usb-sleep-guard ] &&
	bad "debug guard is installed in production" ||
	ok "debug guard is absent"
[ -e /etc/samurai/sleep-inhibitor.conf ] &&
	bad "board sleep config is installed in production" ||
	ok "board sleep config is absent"

if [ -f /etc/sleep-inhibitor.conf ]; then
	grep -q '^[[:space:]]*-[[:space:]]*path:[[:space:]]*ssh-session-open$' \
		/etc/sleep-inhibitor.conf &&
		ok "official ssh-session-open plugin present" ||
		bad "official ssh-session-open plugin missing"
	grep -q '^[[:space:]]*-[[:space:]]*path:[[:space:]]*apk-running$' \
		/etc/sleep-inhibitor.conf &&
		ok "official apk-running plugin present" ||
		bad "official apk-running plugin missing"
	grep -q 'samurai-usb-sleep-guard' /etc/sleep-inhibitor.conf &&
		bad "debug guard is enabled in production" ||
		ok "debug guard is not enabled"
else
	bad "official /etc/sleep-inhibitor.conf missing"
fi

if command -v rc-service >/dev/null 2>&1; then
	rc-service sleep-inhibitor status >/dev/null 2>&1 &&
		ok "official sleep-inhibitor running" ||
		bad "official sleep-inhibitor not running"
	rc-service samurai-sleep-inhibitor status >/dev/null 2>&1 &&
		bad "board samurai-sleep-inhibitor still exists" ||
		ok "board samurai-sleep-inhibitor retired"
fi

[ "$failures" -eq 0 ] || exit 1
echo "RESULT: USB sleep policy provenance check passed"
