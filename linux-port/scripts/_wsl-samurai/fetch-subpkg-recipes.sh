#!/bin/sh
# Fetch the official recipes for the tiny -systemd subpackages whose .apk
# files are missing from the mirror (the index lists them, the blob 404s).
set -u
BASE=https://gitlab.nura.eco/postmarketOS/pmaports/-/raw/v26.06/main
for p in hkdm vvmd; do
	out=/root/subpkg-$p-APKBUILD
	curl -sSL --max-time 45 -o "$out" "$BASE/$p/APKBUILD"
	echo "== $p =="
	grep -n -e subpackages -e 'systemd()' -A8 "$out" 2>/dev/null | head -20
done
