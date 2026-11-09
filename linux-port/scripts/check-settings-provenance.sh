#!/bin/sh
# Read-only provenance check for the production settings baseline.
set -eu

failures=0
notes=0
ok()
{
	echo "ok: $*"
}
bad()
{
	echo "FAIL: $*" >&2
	failures=$((failures + 1))
}
note()
{
	echo "note: $*"
	notes=$((notes + 1))
}

official=/etc/sleep-inhibitor.conf
if [ -f "$official" ]; then
	grep -q '^[[:space:]]*-[[:space:]]*path:[[:space:]]*ssh-session-open$' "$official" &&
		ok 'official ssh-session-open plugin present' ||
		bad 'official ssh-session-open plugin missing'
	grep -q '^[[:space:]]*-[[:space:]]*path:[[:space:]]*apk-running$' "$official" &&
		ok 'official apk-running plugin present' ||
		bad 'official apk-running plugin missing'
	if grep -q 'samurai-usb-sleep-guard' "$official"; then
		bad 'debug carrier guard is enabled in the production config'
	else
		ok 'debug carrier guard is not enabled'
	fi
else
	bad "$official missing"
fi

if command -v rc-service >/dev/null 2>&1; then
	rc-service sleep-inhibitor status >/dev/null 2>&1 &&
		ok 'official sleep-inhibitor service running' ||
		bad 'official sleep-inhibitor service not running'
	rc-service samurai-sleep-inhibitor status >/dev/null 2>&1 &&
		bad 'board samurai-sleep-inhibitor service still exists' ||
		ok 'board samurai-sleep-inhibitor service retired'
fi

[ -e /etc/samurai/sleep-inhibitor.conf ] &&
	bad 'board /etc/samurai/sleep-inhibitor.conf still installed' ||
	ok 'board sleep-inhibitor config absent'
[ -e /usr/libexec/samurai-usb-sleep-guard ] &&
	bad 'debug carrier guard still installed in /usr/libexec' ||
	ok 'debug carrier guard not installed'

tinydm=/etc/conf.d/tinydm
if [ -f "$tinydm" ]; then
	if grep -Eq '^rc_(need|use|after)=.*(samurai-sleep-inhibitor|iio-sensor-proxy)' "$tinydm"; then
		bad 'tinydm still has board debug dependencies'
	else
		ok 'tinydm has no board debug dependencies'
	fi
	if grep -qx 'rc_need="dbus elogind"' "$tinydm"; then
		bad 'tinydm still has the board rc_need override'
	else
		ok 'tinydm has no board rc_need override'
	fi
	grep -q '^rc_cgroup_cleanup="yes"$' "$tinydm" &&
		ok 'tinydm uses the official rc_cgroup_cleanup value' ||
		note 'tinydm rc_cgroup_cleanup is not the official lowercase value'
	grep -q '^AUTOLOGIN_UID=10000$' "$tinydm" &&
		ok 'tinydm uses the official AUTOLOGIN_UID' ||
		note 'tinydm AUTOLOGIN_UID differs from the pmOS default'
else
	bad "$tinydm missing"
fi

powerdevil_found=0
for file in /etc/xdg/powerdevilrc /home/*/.config/powerdevilrc; do
	[ -f "$file" ] || continue
	powerdevil_found=1
	if grep -Eq '^AutoSuspendAction=0$' "$file"; then
		bad "PowerDevil debug override AutoSuspendAction=0 in $file"
	else
		ok "no AutoSuspendAction=0 override in $file"
	fi
done
[ "$powerdevil_found" -eq 1 ] ||
	ok 'no local powerdevilrc; KDE upstream defaults apply'

if [ -e /etc/runlevels/boot/sshd ]; then
	note 'sshd is in boot runlevel (debug-era early-SSH ordering); official default is default runlevel'
fi

if [ "$failures" -ne 0 ]; then
	echo "RESULT: $failures provenance problem(s), $notes note(s)" >&2
	exit 1
fi
echo "RESULT: settings provenance check passed ($notes note(s))"
