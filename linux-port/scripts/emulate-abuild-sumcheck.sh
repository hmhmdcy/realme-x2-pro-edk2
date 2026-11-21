#!/bin/sh
# Reproduce the sumcheck loop pmbootstrap appends to every APKBUILD.
#
# pmbootstrap's abuild_overrides.sh does:
#   set -- $sums ; numsums=$(( $# / 2 )) ; set -- $source
#   if [ $# -ne $numsums ]; then die ... fi
#   for src in $sums ; do echo "$src" | sha512sum -c ; done
#
# Run this from the build directory (where source files were copied) to see
# exactly which entry abuild rejects and what it actually computed.
#
# Usage: emulate-abuild-sumcheck.sh APKBUILD

set -u

apkbuild=${1:?usage: $0 APKBUILD}

SUM_BLOCK=$(awk '/^sha512sums="/{f=1; sub(/^sha512sums="/,""); if ($0 ~ /"$/) {sub(/"$/,""); print; exit} print; next} f && /"$/{sub(/"$/,""); print; exit} f{print}' "$apkbuild")
SRC_LINE=$(sed -n 's/^source="\(.*\)"$/\1/p' "$apkbuild")

# shellcheck disable=SC2086
set -- $SUM_BLOCK
numsums=$(($# / 2))

# shellcheck disable=SC2086
set -- $SRC_LINE
numsrc=$#

echo "abuild view: numsums=$numsums sources=$numsrc"
if [ "$numsrc" -ne "$numsums" ]; then
	echo "MISMATCH: abuild would die before checking any file"
	exit 1
fi

IFS='
'
fail=0
for entry in $SUM_BLOCK; do
	[ -z "$entry" ] && continue
	if ! echo "$entry" | sha512sum -c >/dev/null 2>&1; then
		name=$(echo "$entry" | awk '{print $2}')
		expected=$(echo "$entry" | awk '{print $1}')
		actual=$(sha512sum "$name" 2>/dev/null | awk '{print $1}')
		echo "FAILED: $name"
		echo "  expected $expected"
		echo "  actual   ${actual:-<missing file>}"
		fail=$((fail + 1))
	fi
done
unset IFS

if [ "$fail" -eq 0 ]; then
	echo "OK: every checksum verified from the local sources"
	exit 0
fi
echo "TOTAL FAILED: $fail"
exit 1
