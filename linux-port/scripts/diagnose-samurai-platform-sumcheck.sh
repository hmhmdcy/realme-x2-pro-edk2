#!/bin/bash
# Diagnose why abuild's sumcheck rejects exactly one samurai-platform file.
#
# The buildroot copies source entries into /home/pmos/build/src as symlinks
# and then runs sha512sum -c from there.  When src/ is stale (it only
# refreshes names it already knows), the newest sources have no link and the
# "1 of 1 computed checksums did NOT match" message names an unrelated file.

set -u
root=/home/cy122/samurai-build/work/chroot_native
build=$root/home/pmos/build

echo "== source= tokens =="
# shellcheck disable=SC1091
count=$(cd "$build" && . ./APKBUILD >/dev/null 2>&1 && echo "$source" | wc -w)
echo "source entries: $count"

echo "== src/ entries =="
ls "$build/src" 2>/dev/null | wc -l

echo "== source entries missing from src/ =="
(cd "$build" && . ./APKBUILD >/dev/null 2>&1
 for name in $source; do
	[ -e "src/$name" ] || echo "  missing link: $name"
 done)

echo "== entries in src/ not in source =="
(cd "$build" && . ./APKBUILD >/dev/null 2>&1
 for path in src/*; do
	name=${path#src/}
	case " $source " in
	*" $name "*) ;;
	*) echo "  stale link: $name" ;;
	esac
 done)
