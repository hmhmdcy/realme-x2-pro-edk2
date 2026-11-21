#!/bin/bash
# The running kernel's CONFIG_INITRAMFS_SOURCE points at a cpio.gz that no
# longer exists in WSL.  Locate any surviving copy so regulatory.db can be
# staged into it (that is the only place cfg80211 can find it before the
# f2fs root is mounted).
set -u
for cand in \
	/mnt/e/edk2-samurai-out/*/baseline-initramfs*.gz \
	/mnt/e/edk2-samurai-out/*/*/baseline-initramfs*.gz \
	/mnt/e/edk2-samurai-out/kernel*/candidate-embedded-initramfs*.gz \
	/mnt/e/*/baseline-initramfs*.gz ; do
	for f in $cand; do
		[ -f "$f" ] || continue
		printf '%-88s %s bytes\n' "$f" "$(stat -c %s "$f")"
	done
done
