#!/bin/sh
# Read-only check for the complete Plasma Mobile application set.
set -u

failures=0
installed_db=/lib/apk/db/installed

check_package()
{
	if grep -qx "P:$1" "$installed_db"; then
		printf 'OK   package %s\n' "$1"
	else
		printf 'FAIL package %s\n' "$1"
		failures=$((failures + 1))
	fi
}

check_file()
{
	if [ -f "$1" ]; then
		printf 'OK   file %s\n' "$1"
	else
		printf 'FAIL file %s\n' "$1"
		failures=$((failures + 1))
	fi
}

for package in \
	firefox-esr mobile-config-firefox discover discover-backend-fwupd \
	dolphin kclock krecorder kweather plasma-dialer plasma-phonebook \
	qmlkonsole spacebar ttyescape vvmplayer alligator audiotube elisa \
	itinerary kalgebra kalk kasts kdeconnect keysmith konsole kate ark \
	gwenview kcalc spectacle
do
	check_package "$package"
done

for desktop in \
	/usr/share/applications/org.mozilla.firefox-esr.desktop \
	/usr/share/applications/org.kde.discover.desktop \
	/usr/share/applications/org.kde.dolphin.desktop \
	/usr/share/applications/org.kde.konsole.desktop \
	/usr/share/applications/org.kde.kate.desktop
do
	check_file "$desktop"
done

for command in firefox-esr plasma-discover dolphin konsole kate
do
	if command -v "$command" >/dev/null 2>&1; then
		printf 'OK   command %s\n' "$command"
	else
		printf 'FAIL command %s\n' "$command"
		failures=$((failures + 1))
	fi
done

installed=$(grep -c '^P:' "$installed_db")
printf 'INFO installed packages: %s\n' "$installed"

year=$(date +%Y)
if [ "$year" -lt 2025 ]; then
	printf 'WARN system clock is %s; HTTPS repositories need a correct clock\n' \
		"$(date)"
fi

if [ "$failures" -ne 0 ]; then
	printf 'RESULT: FAIL (%s check(s))\n' "$failures"
	exit 1
fi
printf 'RESULT: PASS\n'
