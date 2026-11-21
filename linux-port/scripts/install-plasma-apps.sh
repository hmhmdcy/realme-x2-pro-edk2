#!/bin/sh
# Install the complete Plasma Mobile application set from a local bundle.
#
# The bundle contains aarch64 APKs, SHA256SUMS and this script.  Installing
# files with --no-network and a repository file that exposes only the local
# @samurai index keeps apk from selecting older Alpine openrc subpackages.
set -eu

if [ "$(id -u)" -ne 0 ]; then
	echo "run as root (sudo $0 $*)" >&2
	exit 1
fi

if [ ! -f /etc/samurai-rootfs-release ]; then
	echo "not a Samurai distro rootfs" >&2
	exit 1
fi

bundle=${1:-}
if [ -z "$bundle" ]; then
	bundle=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
fi
bundle=$(CDPATH= cd -- "$bundle" && pwd)
apks=$bundle/apks

[ -d "$apks" ] || {
	echo "missing APK directory: $apks" >&2
	exit 1
}
[ -f "$bundle/SHA256SUMS" ] || {
	echo "missing SHA256SUMS" >&2
	exit 1
}
[ -f /var/lib/samurai/apk/aarch64/APKINDEX.tar.gz ] || {
	echo "missing @samurai package index" >&2
	exit 1
}

echo "verifying bundle"
(cd "$apks" && sha256sum -c "$bundle/SHA256SUMS" >/dev/null)

repositories=$(mktemp)
trap 'rm -f "$repositories"' EXIT
printf '%s\n' '@samurai /var/lib/samurai/apk' >"$repositories"

echo "installing $(find "$apks" -maxdepth 1 -name '*.apk' | wc -l) packages"
apk --repositories-file "$repositories" --no-network --allow-untrusted \
	--interactive=no add --virtual samurai-apps "$apks"/*.apk

# Plasma's KService cache normally updates through inotify, but refreshing it
# here removes the "apps installed but launcher still empty" first-boot edge.
if command -v kbuildsycoca6 >/dev/null 2>&1; then
	su -s /bin/sh -c 'kbuildsycoca6 --noincremental' user \
		>/dev/null 2>&1 || true
fi

exec "$bundle/check-plasma-apps.sh"
