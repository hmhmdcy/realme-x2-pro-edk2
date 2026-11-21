#!/usr/bin/env bash
set -euo pipefail

rootfs=/mnt/fixed-ro
tmp_etc=/tmp/wsl-recovery-machine-id
mkdir -p "$tmp_etc"
printf 'd5209904af8f4e83aecc31cf88150ab5\n' > "$tmp_etc/machine-id"

echo '=== systemd-nspawn verification ==='
set +e
timeout 45 systemd-nspawn --boot --capability=CAP_SYS_ADMIN \
    --directory="$rootfs" \
    --bind-ro="$tmp_etc/machine-id:/etc/machine-id" \
    --network-namespace-path=/proc/1/ns/net \
    --private-users=no \
    --quiet \
    > /tmp/systemd-root-boot.log 2>&1
rc=$?
set -e
echo "nspawn_rc=$rc"
grep -iE 'Reached target|Failed|systemd|login|Getting host|Kernel panic|ERROR' /tmp/systemd-root-boot.log | head -40 || true
echo '=== log tail ==='
tail -50 /tmp/systemd-root-boot.log || true
exit 0
