#!/bin/bash
# The kernel build caches usr/initramfs_inc_data.  When it is stale the link
# step silently ships the OLD initramfs (no regulatory.db).  Remove every
# generated artefact and rebuild the usr/ object chain from the archive.
set -eu
LK=/home/cy122/x2pro-linux/linux
cd "$LK"

rm -f usr/initramfs_data.o \
	usr/initramfs_data.cpio \
	usr/initramfs_data.cpio.gz \
	usr/initramfs_inc_data \
	usr/.initramfs_data.cpio.d \
	usr/built-in.a vmlinux vmlinux.o

# Build the Image from the top level so the usr/ delegation and the final
# link both run; a sub-target build has no standalone rule for inc_data.
make -j"$(nproc)" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image \
	> /home/cy122/x2pro-linux/build-incdata.log 2>&1 || {
	tail -20 /home/cy122/x2pro-linux/build-incdata.log; exit 1; }
ls -l usr/initramfs_inc_data arch/arm64/boot/Image
sha256sum arch/arm64/boot/Image
