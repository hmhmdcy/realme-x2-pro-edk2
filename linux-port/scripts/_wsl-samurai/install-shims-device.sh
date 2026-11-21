#!/bin/sh
# Install the board-rebuilt systemd shims offline and confirm the device
# reaches the same package count as the delivery image.
set -eu
SUDO() { printf '12345678\n' | sudo -S -p '' "$@"; }
SUDO true

# apk treats the local board repository as a remote repository, so
# --no-network masks even local files; drop it and resolve against the
# board repository alone (the blobs are already on disk).
# The board repository is treated as remote; --no-network masks it, and
# `add` also needs a fresh index, so update it first.
SUDO apk --repositories-file /dev/null \
	--repository /usr/share/samurai/packages update 2>&1 | tail -2
SUDO apk --repositories-file /dev/null \
	--repository /usr/share/samurai/packages \
	add hkdm-systemd vvmd-systemd 2>&1 | tail -6

echo '== totals =='
apk list -I 2>/dev/null | wc -l
echo '== shim owners =='
apk info -W /usr/lib/systemd/system/hkdm.service 2>&1
apk info -W /usr/lib/systemd/user/vvmd.service 2>&1
echo '== units present =='
ls -l /usr/lib/systemd/system/hkdm.service /usr/lib/systemd/user/vvmd.service
