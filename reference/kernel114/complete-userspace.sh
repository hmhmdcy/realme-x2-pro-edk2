#!/bin/bash
set -euo pipefail
umask 077
stage=/home/cy122/pmos-samurai-rootfs114
out=/mnt/e/edk2-samurai-out/kernel114
root="$stage/rootfs"
test -d "$root/usr"
test ! -e "$out/userspace-complete.json"
cp -a "$root/etc/resolv.conf" "$stage/resolv-before"
cp /etc/resolv.conf "$root/etc/resolv.conf"
cleanup() { cp -a "$stage/resolv-before" "$root/etc/resolv.conf"; }
trap cleanup EXIT
chroot "$root" /bin/sh -ec 'export PATH=/usr/sbin:/usr/bin:/sbin:/bin; apk update; apk add --simulate qmi-utils libcamera-tools calls chatty firefox mobile-config-firefox megapixels rsync strace' > "$out/apk-plan-private.log" 2>&1
echo ROOTFS114_SIGNED_PACKAGE_PLAN_READY
chroot "$root" /bin/sh -ec 'export PATH=/usr/sbin:/usr/bin:/sbin:/bin; apk add qmi-utils libcamera-tools calls chatty firefox mobile-config-firefox megapixels rsync strace; glib-compile-schemas --strict /usr/share/glib-2.0/schemas; /usr/sbin/sshd.pam -t; qmicli --version; cam --version; strace --version; apk info' > "$out/apk-install-private.log" 2>&1
echo ROOTFS114_USERSPACE_PACKAGES_INSTALLED
