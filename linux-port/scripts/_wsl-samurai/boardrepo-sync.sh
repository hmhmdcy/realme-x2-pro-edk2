#!/bin/bash
# Keep the signed board repository identical to the board recipes.
#
# The delivery image once shipped samurai-platform 6-r22 while the recipe was
# already at 6-r25 (and samurai-ssc / samurai-systemd lagged one revision
# each), so `apk upgrade` had nothing newer to install and the recipes were
# effectively dead documentation.  This script rebuilds any recipe whose
# revision is missing from the repository, drops superseded revisions, and
# re-signs the APKv3 index the image requires.
#
# Usage: boardrepo-sync.sh [--check]
#   --check  only report drift, change nothing (exit 1 if drift exists)
set -eu

REPO_SRC=${REPO_SRC:-/root/boardrepo-r17}
BOARD_BUILD=${BOARD_BUILD:-/root/board-out}
BUILDER=/mnt/e/RealmeX2Pro\ edk2/linux-port/scripts/_wsl-samurai/build-board-packages.sh
PKGS=/mnt/e/RealmeX2Pro\ edk2/linux-port/packages
APK=/root/apkstatic/sbin/apk.static
KEYS=/root/installed_keys
SIGN_KEY=${SIGN_KEY:-/mnt/e/edk2-samurai-out/standard-arm64-v731/wifi-fast-ready-20261108/signing-key-private.rsa}
RECIPES=${RECIPES:-"samurai-platform samurai-ssc samurai-systemd"}

CHECK=0
[ "${1:-}" = "--check" ] && CHECK=1

mkdir -p "$BOARD_BUILD"
drift=0
for recipe in $RECIPES; do
	dir=$PKGS/$recipe
	[ -f "$dir/APKBUILD" ] || { echo "FATAL: missing recipe $recipe" >&2; exit 1; }
	ver=$(sed -n 's/^pkgver=//p' "$dir/APKBUILD" | head -1)
	rel=$(sed -n 's/^pkgrel=//p' "$dir/APKBUILD" | head -1)
	want="$recipe-$ver-r$rel.apk"

	if [ -f "$REPO_SRC/$want" ] && cmp -s "$REPO_SRC/$want" "$BOARD_BUILD/$want"; then
		echo "  ok: $want"
		continue
	fi
	drift=$((drift + 1))
	echo "  DRIFT: $want (recipe $ver-r$rel)"
	[ "$CHECK" -eq 1 ] && continue

	echo "  building $want"
	OUT="$BOARD_BUILD" bash "$BUILDER" "$recipe"
	# The builder also emits any subpackage at the same revision.
	for built in "$BOARD_BUILD/$recipe-$ver-r$rel"*.apk; do
		[ -e "$built" ] || continue
		install -Dm644 "$built" "$REPO_SRC/$(basename "$built")"
	done
done

for recipe in $RECIPES; do
	# Every artifact the recipe can produce at its current revision: the
	# main package plus any subpackage (samurai-platform-pulse, ...).  Only
	# artifacts that were actually rebuilt are considered, so a subpackage
	# is never dropped just because the builder did not emit it this run.
	for built in "$BOARD_BUILD/$recipe-$ver-r$rel".apk \
	             "$BOARD_BUILD/$recipe"-*"-r$rel.apk"; do
		[ -e "$built" ] || continue
		base=$(basename "$built")
		target="$REPO_SRC/$base"
		if [ -f "$target" ] && cmp -s "$built" "$target"; then
			echo "  ok: $base"
			continue
		fi
		echo "  refresh: $base"
		[ "$CHECK" -eq 1 ] || install -Dm644 "$built" "$target"
	done

	for old in "$REPO_SRC"/$recipe-*.apk; do
		[ -e "$old" ] || continue
		base=$(basename "$old")
		[ -f "$BOARD_BUILD/$base" ] && continue
		echo "  stale: $base"
		[ "$CHECK" -eq 1 ] || rm -f "$old"
	done
done

if [ "$CHECK" -eq 1 ]; then
	[ "$drift" -eq 0 ] || { echo "drift=$drift" >&2; exit 1; }
	echo 'repository matches the recipes'
	exit 0
fi

echo '=== re-sign APKv3 index ==='
TRUST=/root/boardrepo-trust
rm -rf "$TRUST"; mkdir -p "$TRUST"
cp "$KEYS"/*.rsa.pub "$TRUST"/
[ -d /root/akeys ] && cp /root/akeys/*.rsa.pub "$TRUST"/
rm -f "$REPO_SRC/APKINDEX.tar.gz"
"$APK" --keys-dir "$TRUST" --sign-key "$SIGN_KEY" mkndx \
	--pkgname-spec '${name}-${version}.apk' \
	--description 'Realme X2 Pro board packages (official v26.06 base)' \
	--output "$REPO_SRC/APKINDEX.tar.gz" \
	"$REPO_SRC"/*.apk
"$APK" --keys-dir "$TRUST" verify "$REPO_SRC/APKINDEX.tar.gz"
sha256sum "$REPO_SRC/APKINDEX.tar.gz"
