#!/bin/sh
# Verify that each sha512sums line is adjacent to the matching source entry.
#
# abuild's default_fetch() walks $source in order and shifts two words off
# $sha512sums per file:
#
#     set -- ${sha512sums:-$sha256sums}
#     for s in $source; do
#         echo "$1  $file" | sha512sum -c   # $1 is the expected hash
#         shift 2
#     done
#
# so the N-th checksum must belong to the N-th source.  A single misplaced
# line makes every later file report FAILED while the first mismatch is the
# real one.

set -u
apkbuild=${1:?usage: $0 APKBUILD}
srcdir=$(dirname "$apkbuild")

source_list=$(sed -n 's/^source="\(.*\)"$/\1/p' "$apkbuild")
sync_block=$(
	awk '
		/^sha512sums="/ { inside=1; sub(/^sha512sums="/, ""); }
		inside && /"$/ { sub(/"$/, ""); print; exit }
		inside { print }
	' "$apkbuild"
)

idx=0
bad=0
# shellcheck disable=SC2086
set -- $source_list
echo "$sync_block" | while IFS= read -r line; do
	[ -z "$line" ] && continue
	idx=$((idx + 1))
	expected_name=$(echo "$line" | awk '{print $2}')
	actual_name=$(eval "echo \${$idx}")
	if [ "$expected_name" != "$actual_name" ]; then
		echo "OUT OF ORDER at position $idx:"
		echo "  sha512sums names: $expected_name"
		echo "  source names     : $actual_name"
		bad=$((bad + 1))
	fi
done
echo "checked via positional alignment"
