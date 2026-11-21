#!/usr/bin/env bash
set -euo pipefail

VHDX_PATH='/mnt/c/Users/cy122/AppData/Local/wsl/{ee461976-57ad-4560-8244-f266f2040781}/ext4.vhdx'
VHD_ROOT='/mnt/orig-vhd'
EXT4_ROOT='/mnt/orig-ro'

if ! command -v vhdimount >/dev/null 2>&1; then
    echo 'Missing vhdimount. Install it with:' >&2
    echo '  apt-get update && apt-get install -y libvhdi-utils' >&2
    exit 1
fi

mkdir -p "$VHD_ROOT" "$EXT4_ROOT"

if ! mountpoint -q "$VHD_ROOT"; then
    vhdimount "$VHDX_PATH" "$VHD_ROOT"
fi

if [ ! -b "$VHD_ROOT/vhdi1" ] && [ ! -f "$VHD_ROOT/vhdi1" ]; then
    echo 'vhdimount did not expose the virtual disk' >&2
    exit 1
fi

if ! mountpoint -q "$EXT4_ROOT"; then
    mount -t ext4 -o ro,noload,noatime "$VHD_ROOT/vhdi1" "$EXT4_ROOT"
fi

echo "Original Ubuntu is mounted read-only at $EXT4_ROOT."
echo "Preview: ls -la $EXT4_ROOT/home/cy122"
