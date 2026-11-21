#!/bin/sh
# Read-only probe: which official recommends does the image still miss,
# and can they be installed from the repositories the image already has?
set -u
for p in gst-plugins-ugly gst-plugins-good gst-libav vvmd hkdm \
	plasma-mobile-sounds ttyescape buffyboard terminus-font kbd; do
	printf '%-22s ' "$p"
	if apk info -e "$p" >/dev/null 2>&1; then
		echo installed
	else
		echo MISSING
		fi
done
echo '== vvmplayer dependency tree (resolved offline) =='
apk --no-network info -R vvmplayer 2>&1 | head -12
echo '== disk space for the recommends =='
apk --no-network info -s gst-plugins-ugly vvmd vvmplayer hkdm \
	plasma-mobile-sounds 2>/dev/null |
	sed 's/^/  /' | head -8
