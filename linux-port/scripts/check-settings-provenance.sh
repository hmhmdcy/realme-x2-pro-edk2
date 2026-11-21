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

# The v26.06 stable image is systemd-based: tinydm runs as a unit with a
# /run/systemd/generator drop-in, and /etc/conf.d/tinydm does not exist.
# Only judge the OpenRC file when this image actually uses OpenRC, otherwise
# the check would fail every systemd build for a file that is not meant to
# be there.
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
elif [ -d /run/systemd/system ]; then
	if [ -f /usr/lib/systemd/system/tinydm.service ]; then
		ok 'systemd image: tinydm is unit-based, no /etc/conf.d/tinydm expected'
	else
		bad 'systemd image but tinydm.service is missing'
	fi
else
	bad "$tinydm missing"
fi

powerdevil_found=0
for file in /etc/xdg/powerdevilrc /home/*/.config/powerdevilrc; do
	[ -f "$file" ] || continue
	powerdevil_found=1
done
[ "$powerdevil_found" -eq 1 ] ||
	ok 'no local powerdevilrc; KDE upstream defaults apply'

# The board ships /etc/xdg/powerdevilrc with both keys at 0.  KDE's desktop
# KCM writes AutoSuspendAction=0 for "Never", the Plasma Mobile KCM writes
# AutoSuspendIdleTimeoutSec=0; pinning both keeps the setting unambiguous
# whichever UI is opened.  They are ordinary user-facing keys, not a
# private debug override; ~/.config/powerdevilrc still wins.
system_powerdevil=/etc/xdg/powerdevilrc
if [ -f "$system_powerdevil" ]; then
	sections=0
	for section in '[AC][SuspendAndShutdown]' \
				   '[Battery][SuspendAndShutdown]' \
				   '[LowBattery][SuspendAndShutdown]'; do
		if awk -v want="$section" '
			$0 == want { inside = 1; next }
			/^\[/ { inside = 0 }
			inside && /^AutoSuspendAction=0$/ { action = 1 }
			inside && /^AutoSuspendIdleTimeoutSec=0$/ { found = 1 }
			END { exit (found && action) ? 0 : 1 }' "$system_powerdevil"; then
			sections=$((sections + 1))
		else
			bad "auto-suspend not fully disabled under $section in $system_powerdevil"
		fi
	done
	[ "$sections" -eq 3 ] &&
		ok 'board default sets NoAction + never on AC, battery and low battery' ||
		true
	# A non-zero action would re-enable suspend even with a 0 timeout.
	if awk '
		/^\[/ { inside = ($0 ~ /^\[(AC|Battery|LowBattery)\]\[SuspendAndShutdown\]$/) }
		inside && /^AutoSuspendAction=/ && $0 != "AutoSuspendAction=0" { bad = 1 }
		END { exit bad ? 0 : 1 }' "$system_powerdevil"; then
		bad "non-NoAction AutoSuspendAction in $system_powerdevil"
	else
		ok 'every AutoSuspendAction is NoAction'
	fi
	# A prebuilt image can be assembled outside apk, leaving the file on disk
	# but absent from lib/apk/db/installed.  That happened to 4-r16: the value
	# was live, yet no package owned the file, so no upgrade could replace it.
	# The installed DB stores nested files as "F:<dir>" plus "R:<name>" pairs,
	# so a literal ^R:powerdevilrc$ grep can never match /etc/xdg/powerdevilrc.
	owner=$(apk info -W /etc/xdg/powerdevilrc 2>/dev/null |
		sed -n 's|^/etc/xdg/powerdevilrc is owned by ||p' | head -n 1)
	if [ -n "$owner" ]; then
		ok "/etc/xdg/powerdevilrc is owned by $owner"
	else
		bad '/etc/xdg/powerdevilrc is not owned by any package; apk cannot replace it'
	fi
else
	bad "$system_powerdevil missing; board default would auto-suspend"
fi

for user_file in /home/*/.config/powerdevilrc; do
	[ -f "$user_file" ] || continue
	if awk '
		/^\[/ { inside = ($0 ~ /^\[(AC|Battery|LowBattery)\]\[SuspendAndShutdown\]$/) }
		inside && /^AutoSuspendAction=/ && $0 != "AutoSuspendAction=0" { bad = 1 }
		inside && /^AutoSuspendIdleTimeoutSec=/ && $0 != "AutoSuspendIdleTimeoutSec=0" { bad = 1 }
		END { exit bad ? 0 : 1 }' "$user_file"; then
		bad "user override re-enables auto-suspend in $user_file"
	else
		ok "$user_file keeps auto-suspend off"
	fi
done

if [ -e /etc/runlevels/boot/sshd ]; then
	note 'sshd is in boot runlevel (debug-era early-SSH ordering); official default is default runlevel'
fi

if [ "$failures" -ne 0 ]; then
	echo "RESULT: $failures provenance problem(s), $notes note(s)" >&2
	exit 1
fi
echo "RESULT: settings provenance check passed ($notes note(s))"
