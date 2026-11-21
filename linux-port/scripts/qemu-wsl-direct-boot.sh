#!/usr/bin/env bash
set -euo pipefail

IMAGE=/mnt/e/wsl-recover/wsl-ubuntu-fix.qcow2
KERNEL=/mnt/c/Program\ Files/WSL/tools/kernel
INITRD=/mnt/c/Program\ Files/WSL/tools/initrd.img
LOG=/mnt/e/wsl-recover/qemu-boot/direct-serial.log

"$KERNEL" --help >/dev/null 2>&1 || true

mkdir -p /mnt/e/wsl-recover/qemu-boot
echo '=== boot repaired overlay with WSL kernel ==='
set +e
timeout 180 qemu-system-x86_64 \
    -machine q35,accel=tcg \
    -m 3072 \
    -smp 2 \
    -kernel "$KERNEL" \
    -initrd "$INITRD" \
    -append 'console=ttyS0 root=/dev/vda rw earlyprintk' \
    -drive "file=$IMAGE,format=qcow2,if=virtio,readonly=on" \
    -serial stdio \
    -display none \
    -no-reboot \
    > "$LOG" 2>&1
rc=$?
set -e
echo "qemu_rc=$rc"
echo '=== kernel / rootfs evidence ==='
grep -iE 'Linux version|Ubuntu|Attempting to mount|VFS: Cannot|Kernel panic|initramfs|recovery-boot-sentinel|rootfs' "$LOG" | head -40 || true
echo '=== tail ==='
tail -80 "$LOG" || true
exit 0
