#!/bin/sh
# Mirror the rebuilt, signed board repository onto the device so
# `apk upgrade`/`apk add` can resolve every board and recommend package
# offline.  Only the board directory is replaced; Alpine/pmOS repos stay.
set -eu
SUDO() { printf '12345678\n' | sudo -S -p '' "$@"; }
SUDO true

DST=/usr/share/samurai/packages/aarch64
SRC=/tmp/boardrepo-final
stamp=$(date +%Y%m%d-%H%M%S)

echo "== backup old board repo to /usr/share/samurai/packages/.bak-$stamp =="
SUDO mkdir -p "/usr/share/samurai/packages/.bak-$stamp"
SUDO cp -a "$DST"/* "/usr/share/samurai/packages/.bak-$stamp/" 2>/dev/null || true

echo '== install new index and packages =='
SUDO install -d -m0755 "$DST"
SUDO install -m0644 "$SRC/APKINDEX.tar.gz" "$DST/APKINDEX.tar.gz"
for f in "$SRC"/*.apk; do
	SUDO install -m0644 "$f" "$DST/$(basename "$f")"
done

echo '== verify index signature with the device key set =='
SUDO apk --keys-dir /etc/apk/keys verify "$DST/APKINDEX.tar.gz"
echo '== tag the board repository so it always wins over an identical copy =='
# The recommends also exist in the official repositories.  Without a tag,
# apk may resolve the official index entry first and then fail to fetch it
# offline ("package mentioned in index not found").  A world-side tag pin
# makes the local copy the only candidate.
SUDO sh -c 'grep -q "@samurai" /etc/apk/repositories || \
	printf "%s\n" "@samurai /usr/share/samurai/packages" >>/etc/apk/repositories'
echo '== entries now visible =='
printf '12345678\n' | sudo -S -p '' apk --no-network update 2>&1 | tail -3
apk list -a 2>/dev/null | grep -E '^(ttyescape|plasma-mobile-sounds|hkdm)' || true
