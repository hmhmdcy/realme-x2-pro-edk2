#!/bin/sh
# Run *inside TWRP/recovery* (arm64), not on the host and not in WSL.
# sshd binds the port before sshd-auth loads the host key, so a missing
# host key looks like "TCP connects, then 0 bytes and close".  This script
# collects the persisted journal evidence and, if the key really is absent,
# regenerates it with the target's own ssh-keygen (recovery is arm64, so a
# chroot into the aarch64 rootfs runs natively -- no qemu needed).
set -eu

DEV=/dev/block/sda16
MNT=/mnt/pmos

umount /sdcard 2>/dev/null || true
umount /data 2>/dev/null || true
mkdir -p "$MNT"
mount -t f2fs -o rw "$DEV" "$MNT"

echo '=== 1. host keys on disk ==='
ls -l "$MNT"/etc/ssh/ 2>&1 || true

echo '=== 2. sshdgenkeys / sshd journal (persisted) ==='
journalctl -D "$MNT/var/log/journal" --no-pager -u sshdgenkeys -u sshd 2>&1 | tail -40 ||
    echo '  (no persisted journal; nothing to grep)'

echo '=== 3. why did ssh-keygen fail? direct retry inside the rootfs ==='
if [ ! -s "$MNT/etc/ssh/ssh_host_ed25519_key" ]; then
    chroot "$MNT" /usr/bin/ssh-keygen -A 2>&1 || true
else
    echo '  host keys already exist'
fi

echo '=== 4. result ==='
ls -l "$MNT"/etc/ssh/ssh_host_* 2>&1 || echo '  STILL MISSING'

sync
echo '=== done; reboot from recovery to test ==='
