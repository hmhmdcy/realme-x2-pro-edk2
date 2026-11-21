#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: wsl-recover-overlay.sh <check|fix> <source-image> <overlay.qcow2> [raw|vhdx]

Create a sparse QCOW2 copy-on-write overlay backed by the source VHDX,
expose it as a FUSE block device, and run e2fsck.

check: e2fsck -fn (no filesystem writes)
fix:   e2fsck -fy (writes only to the overlay, never the source VHDX)
EOF
}

mode=${1:-}
source_vhdx=${2:-}
overlay=${3:-}
source_fmt=${4:-vhdx}

if [ "$mode" != check ] && [ "$mode" != fix ]; then
    usage >&2
    exit 2
fi
if [ -z "$source_vhdx" ] || [ -z "$overlay" ]; then
    usage >&2
    exit 2
fi
if [ "$source_fmt" != raw ] && [ "$source_fmt" != vhdx ]; then
    echo "Unsupported source format: $source_fmt" >&2
    exit 2
fi

for cmd in qemu-img qemu-storage-daemon losetup e2fsck; do
    command -v "$cmd" >/dev/null 2>&1 || {
        echo "Missing dependency: $cmd" >&2
        exit 1
    }
done

if [ ! -r "$source_vhdx" ]; then
    echo "Source VHDX is not readable: $source_vhdx" >&2
    exit 1
fi
if [ -e "$overlay" ]; then
    echo "Refusing to overwrite an existing overlay: $overlay" >&2
    exit 1
fi

workdir=$(mktemp -d /tmp/wsl-recover-overlay.XXXXXX)
devfile="$workdir/device"
fuse_pid=
loop_dev=

cleanup() {
    if [ -n "${loop_dev:-}" ]; then
        losetup -d "$loop_dev" 2>/dev/null || true
    fi
    if [ -n "${fuse_pid:-}" ]; then
        kill "$fuse_pid" 2>/dev/null || true
        wait "$fuse_pid" 2>/dev/null || true
    fi
    umount "$devfile" 2>/dev/null || true
    rm -rf "$workdir"
}
trap cleanup EXIT INT TERM

echo "mode=$mode"
echo "source=$source_vhdx"
echo "source_format=$source_fmt"
echo "overlay=$overlay"

qemu-img create -q -f qcow2 -b "$source_vhdx" -F "$source_fmt" "$overlay"
echo "overlay_info:"
qemu-img info --backing-chain "$overlay"

truncate -s 0 "$devfile"
qemu-storage-daemon \
    --blockdev "driver=file,filename=$overlay,node-name=overlay-file,cache.direct=off" \
    --blockdev driver=qcow2,file=overlay-file,node-name=overlay-disk \
    --export type=fuse,id=export0,node-name=overlay-disk,mountpoint="$devfile",writable=on \
    >"$workdir/fuse.log" 2>&1 &
fuse_pid=$!

expected_size=0
for _ in $(seq 1 240); do
    if ! kill -0 "$fuse_pid" 2>/dev/null; then
        cat "$workdir/fuse.log" >&2
        echo "FUSE export exited early" >&2
        exit 1
    fi
    actual_size=$(stat -c '%s' "$devfile" 2>/dev/null || echo 0)
    if [ "$actual_size" -gt 0 ]; then
        expected_size=$actual_size
        break
    fi
    sleep 0.25
done

if [ "$expected_size" -eq 0 ]; then
    cat "$workdir/fuse.log" >&2 || true
    echo "FUSE export did not report a virtual disk size" >&2
    exit 1
fi

loop_dev=$(losetup -f --show "$devfile")
actual_size=$(blockdev --getsize64 "$loop_dev")
if [ "$actual_size" -ne "$expected_size" ]; then
    echo "Loopback size mismatch: expected=$expected_size actual=$actual_size" >&2
    exit 1
fi

echo "loop=$loop_dev"
blockdev --getsize64 "$loop_dev"

set +e
if [ "$mode" = check ]; then
    e2fsck -fn "$loop_dev" 2>&1 | tee "$overlay.check.log"
elif [ "$mode" = fix ]; then
    e2fsck -E no_optimize_extents -fy -z "$overlay.e2fsck-undo" "$loop_dev" 2>&1 | tee "$overlay.fix.log"
else
    echo "Unsupported mode" >&2
    exit 2
fi
fsck_rc=${PIPESTATUS[0]}
set -e
echo "fsck_rc=$fsck_rc"

sync
du -h "$overlay"
echo "Second read-only verification:"
set +e
e2fsck -fn "$loop_dev" 2>&1 | tee "$overlay.verify.log"
verify_rc=${PIPESTATUS[0]}
set -e
echo "verify_rc=$verify_rc"

if [ "$mode" = fix ]; then
    if [ "$fsck_rc" -eq 0 ] || { [ "$fsck_rc" -eq 1 ] && [ "$verify_rc" -eq 0 ]; }; then
        echo "fix_status=ready (overlay is independently readable)"
        exit 0
    fi
    echo "fix_status=incomplete" >&2
    exit 1
fi
exit 0
