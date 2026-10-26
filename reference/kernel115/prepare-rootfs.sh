#!/bin/bash
set -euo pipefail
umask 077
stage=/home/cy122/pmos-samurai-rootfs115
test ! -e "$stage"
mkdir "$stage"
cp -a --reflink=auto /home/cy122/pmos-samurai-rootfs114/rootfs "$stage/rootfs"
cp -a /home/cy122/pmos-samurai-kernel115/runtime-package/lib/. "$stage/rootfs/usr/lib/"
depmod -b "$stage/rootfs" 7.3.0-rc6-rmx1931-samurai+
printf 'rootfs115-ipa-zram-kernel115\n' > "$stage/rootfs/etc/samurai-rootfs-stage"
echo ROOTFS115_STAGE_COMPLETE_USERSPACE_MODULES_OWN_IPA_FIRMWARE_READY
