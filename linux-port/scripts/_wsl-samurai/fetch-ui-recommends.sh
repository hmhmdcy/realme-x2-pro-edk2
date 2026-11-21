#!/bin/sh
# Fetch the official postmarketos-ui-plasma-mobile recipe so its
# _pmb_recommends list can be compared with what the image actually has.
set -u
for base in https://gitlab.nura.eco/postmarketOS/pmaports/-/raw \
	https://gitlab.postmarketos.org/postmarketOS/pmaports/-/raw; do
	for ref in v26.06 master main; do
		out=/tmp/ui-$ref.txt
		curl -sSL --max-time 45 -o "$out" \
			"$base/$ref/main/postmarketos-ui-plasma-mobile/APKBUILD"
		if grep -q 'pkgname=postmarketos-ui-plasma-mobile' "$out" 2>/dev/null; then
			echo "got $ref from $base"
			grep -n -A12 '_pmb_recommends' "$out" | head -20
			echo '== every recommend literal in the recipe =='
			awk '/_pmb_recommends="/{f=1;next} f&&/"/{f=0}
				f{gsub(/[\t ]/,""); if (length) print}' "$out"
			exit 0
		fi
	done
done
echo 'could not fetch the recipe'
