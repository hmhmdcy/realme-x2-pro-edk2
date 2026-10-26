#!/bin/bash
set -euo pipefail
stage=/home/cy122/pmos-samurai-kernel109
out=/mnt/e/edk2-samurai-out/kernel109
root="$stage/rootfs"
rootfs_uuid=$(cat "$out/rootfs-uuid-private.txt")
[[ "$rootfs_uuid" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]]
image="$stage/samurai-rootfs-f2fs-final.raw.img"
test ! -e "$image"
if findmnt -rn -o TARGET | grep -F "$root/"; then
    echo 'Build mounts still present' >&2
    exit 1
fi
chroot "$root" /bin/sh -ec '
    export PATH=/usr/sbin:/usr/bin:/sbin:/bin
    /usr/sbin/sshd.pam -t
    /usr/sbin/sshd.pam -T | grep -iE "^permitrootlogin|^passwordauthentication|^pubkeyauthentication|^kbdinteractiveauthentication|^usepam"
    id cy122
    sh -n /usr/local/sbin/samurai-usb /etc/init.d/samurai-usb /etc/init.d/samurai-radio /usr/sbin/samurai-wifi
    /usr/sbin/wpa_supplicant -v
    /usr/sbin/iw --version
    test -x /sbin/init
    test -L /etc/runlevels/default/samurai-radio
    echo NATIVE_USERSPACE_VALIDATION_PASS
' > "$out/userspace-validation.log" 2>&1
truncate -s 119033245696 "$image"
mkfs.f2fs -f -t 0 -w 4096 -l pmos_root -U "$rootfs_uuid" "$image" > "$out/mkfs.log" 2>&1
sload.f2fs -P -f "$root" "$image" > "$out/sload.log" 2>&1
fsck.f2fs --dry-run "$image" > "$out/fsck-raw.log" 2>&1
img2simg -s "$image" "$out/samurai-rootfs-f2fs.simg" 4096
python3 "$out/verify-sparse.py" > "$out/sparse-verify.log"
fsck.f2fs --dry-run "$stage/samurai-rootfs-f2fs-restored.raw.img" > "$out/fsck-restored.log" 2>&1
sha256sum "$out/samurai-rootfs-f2fs.simg" > "$out/rootfs.sha256"
echo ROOTFS109_PACK_AND_SPARSE_RESTORE_FSCK_PASS
