#!/bin/bash
# Verify that APKBUILD dependency strings are syntactically valid.
#
# Mirrors abuild's check_depver(): split name/operator/version, validate the
# version with apk, and accept only the operators apk implements.  Run it
# against a real apk binary (apk-tools 2.14 matches pmOS targets).
#
# Usage:
#   APK=/path/to/apk.static ./check-pkg-constraints.sh DEP...

set -u

: "${APK:?set APK to an apk.static binary}"

fail=0

check_depver() {
	local name="${1%%[<>=~]*}"
	if [ "$name" = "$1" ]; then
		echo "OK   $1 (no constraint)"
		return 0
	fi

	local ver="${1##*[<>=~]}"
	if ! "$APK" version --check --quiet "$ver"; then
		echo "FAIL $1 (invalid version: $ver)"
		return 1
	fi

	local sep="${1#"$name"}"
	sep="${sep%"$ver"}"

	local i
	for i in "<" ">" "=" "~" ">=" "<=" ">~" "<~"; do
		if [ "$sep" = "$i" ]; then
		echo "OK   $1"
		return 0
		fi
	done

	echo "FAIL $1 (unknown operator: $sep)"
	return 1
}

for dep in "$@"; do
	check_depver "$dep" || fail=1
done

exit "$fail"
