#!/bin/sh
# Compare the official _pmb_recommends list of postmarketos-ui-plasma-mobile
# (and its -extras subpackage, which pmbootstrap installs together with it)
# against what is actually installed on the device.
set -u
recipe=/tmp/ui-v26.06.txt
[ -s "$recipe" ] || { echo "missing $recipe"; exit 1; }

sed -n '/_pmb_recommends="/,/^"/p' "$recipe" |
	grep -E '^\t[a-z]' | tr -d '\t " \\' > /tmp/want.txt

echo "== official recommends: $(wc -l < /tmp/want.txt) =="
while read -r p; do
	[ -n "$p" ] || continue
	if apk info -e "$p" >/dev/null 2>&1; then
		printf '  ok       %s\n' "$p"
	else
		printf '  MISSING  %s\n' "$p"
	fi
done < /tmp/want.txt
