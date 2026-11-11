#!/bin/sh
set -eu

source_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
destdir=${DESTDIR:-}
target="$destdir/etc/wireplumber/wireplumber.conf.d/60-samurai-camera-names.conf"

install -Dm644 \
	"$source_dir/60-samurai-camera-names.conf" \
	"$target"

printf 'Installed %s\n' "$target"
printf 'Restart the desktop WirePlumber process, then reopen the camera app.\n'
