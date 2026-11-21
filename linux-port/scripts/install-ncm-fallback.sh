#!/bin/bash
# RETIRED - do not use.
#
# This installer appended a hand-written record to lib/apk/db/installed.
# apk-tools 3 cannot parse such records and then refuses to read the whole
# database ("v2 database format error"), which disables the package manager
# on the device.  The service it installed was also a one-shot boot-runlevel
# script that ran before usb0 existed, so it never configured the interface.
#
# Use instead: apply-rootfs-ncm-layer-fix.sh RAW_IMG INITD WATCHDOG [USER]

cat >&2 <<'EOF'
install-ncm-fallback.sh is retired: it corrupted lib/apk/db/installed.
Use apply-rootfs-ncm-layer-fix.sh instead.
EOF
exit 1
