#!/usr/bin/env bash
set -euo pipefail

SRC_OVERLAY=/mnt/e/wsl-recover/wsl-ubuntu-fix.qcow2
WORK_DIR=/mnt/e/wsl-recover/qemu-boot
TEST_IMAGE="$WORK_DIR/boot-test.qcow2"
SENTINEL=/recovery-boot-sentinel

mkdir -p "$WORK_DIR"
rm -f "$TEST_IMAGE" "$TEST_IMAGE-dev" "$WORK_DIR"/serial.log

echo '=== convert repaired overlay to standalone test image ==='
qemu-img convert -p -f qcow2 -O qcow2 "$SRC_OVERLAY" "$TEST_IMAGE"

echo '=== inject sentinel through the test image ==='
truncate -s 0 "$TEST_IMAGE-dev"
qemu-storage-daemon \
    --blockdev "driver=file,filename=$TEST_IMAGE,node-name=img-file" \
    --blockdev driver=qcow2,file=img-file,node-name=img \
    --export type=fuse,id=export0,node-name=img,mountpoint="$TEST_IMAGE-dev",writable=on \
    >"$WORK_DIR"/dev.log 2>&1 &
dpid=$!
for _ in $(seq 1 80); do
    [ "$(stat -c '%s' "$TEST_IMAGE-dev" 2>/dev/null || echo 0)" -gt 0 ] && break
    kill -0 "$dpid" 2>/dev/null || { cat "$WORK_DIR"/dev.log >&2; exit 1; }
    sleep 0.25
done
loop=$(losetup -f --show "$TEST_IMAGE-dev")
echo "loop=$loop size=$(blockdev --getsize64 "$loop")"
mkdir -p /mnt/qemu-boot-write
mount -t ext4 -o rw,noload,noatime "$loop" /mnt/qemu-boot-write
touch "$SENTINEL"
sync
umount /mnt/qemu-boot-write
losetup -d "$loop"
kill "$dpid" 2>/dev/null || true
sleep 1
umount "$TEST_IMAGE-dev" 2>/dev/null || true

echo '=== boot QEMU ==='
set +e
timeout 180 qemu-system-x86_64 \
    -machine q35,accel=tcg \
    -m 3072 \
    -smp 2 \
    -drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd \
    -drive if=pflash,format=raw,file="$WORK_DIR"/ovmf-vars.fd \
    -drive file="$TEST_IMAGE",format=qcow2,if=virtio,readonly=on \
    -serial stdio \
    -display none \
    -no-reboot \
    > "$WORK_DIR"/serial.log 2>&1
qrc=$?
set -e
echo "qemu_rc=$qrc"
echo '=== sentinel / kernel evidence ==='
grep -F "$SENTINEL" "$WORK_DIR"/serial.log || true
grep -iE 'Linux version|Ubuntu|rootfs|initramfs|Kernel panic|No bootable|sentinel' "$WORK_DIR"/serial.log | head -40 || true
echo '=== serial tail ==='
tail -40 "$WORK_DIR"/serial.log || true
exit 0
