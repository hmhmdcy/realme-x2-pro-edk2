#!/bin/sh
#
# Write only the kernel FAT (GPT label "logdump") from the running system.
# The boot carrier and every other partition are left untouched.
#
set -eu

KERNEL_IMAGE=
KERNEL_SHA256=
DRY_RUN=0
REBOOT=0

usage() {
	cat <<'EOF'
usage: flash-kernel-linux.sh --kernel-fat IMAGE --sha256 SHA256 \
  [--dry-run] [--reboot]

The image is verified locally and against the target partition before any
write. The target is resolved by GPT label "logdump", never by enumeration
order. The partition must be unmounted and writable.
EOF
}

die() {
	printf 'ERROR: %s\n' "$*" >&2
	exit 1
}

lower_hex() {
	printf '%s' "$1" | tr 'A-F' 'a-f'
}

partition_by_label() {
	label=$1
	path=$(readlink -f "/dev/disk/by-partlabel/$label" 2>/dev/null || true)
	[ -n "$path" ] || die "no block device for PARTLABEL=$label"
	[ -b "$path" ] || die "PARTLABEL=$label is not a block device: $path"
	printf '%s\n' "$path"
}

is_mounted() {
	device=$1
	awk -v device="$device" '$1 == device { found = 1 } END { exit(found ? 0 : 1) }' /proc/mounts
}

verify_image() {
	image=$1
	expected=$2
	device=$3

	[ -f "$image" ] || die "kernel FAT image not found: $image"
	expected=$(lower_hex "$expected")
	[ "${#expected}" -eq 64 ] || die "SHA-256 is not 64 hex characters"
	[ "$(stat -c %s "$image")" -eq "$(blockdev --getsize64 "$device")" ] ||
		die "size mismatch: image=$(stat -c %s "$image") partition=$(blockdev --getsize64 "$device")"
	actual=$(sha256sum "$image" | cut -d ' ' -f 1)
	[ "$actual" = "$expected" ] ||
		die "image hash mismatch: expected=$expected actual=$actual"
	is_mounted "$device" && die "target is mounted: $device"
	[ "$(blockdev --getro "$device")" -eq 0 ] ||
		die "target is read-only: $device"
}

while [ "$#" -gt 0 ]; do
	case "$1" in
	--kernel-fat)
		[ "$#" -ge 2 ] || die "--kernel-fat needs an argument"
		KERNEL_IMAGE=$2
		shift 2
		;;
	--sha256)
		[ "$#" -ge 2 ] || die "--sha256 needs an argument"
		KERNEL_SHA256=$2
		shift 2
		;;
	--dry-run)
		DRY_RUN=1
		shift
		;;
	--reboot)
		REBOOT=1
		shift
		;;
	-h | --help)
		usage
		exit 0
		;;
	*)
		die "unknown argument: $1"
		;;
	esac
done

[ "$(id -u)" -eq 0 ] || die "run as root"
[ -n "$KERNEL_IMAGE" ] && [ -n "$KERNEL_SHA256" ] ||
	die "--kernel-fat and --sha256 are required"

KERNEL_SHA256=$(lower_hex "$KERNEL_SHA256")
DEVICE=$(partition_by_label logdump)
verify_image "$KERNEL_IMAGE" "$KERNEL_SHA256" "$DEVICE"

printf 'schema=samurai-linux-side-kernel-flash-v1\n'
printf 'kernel_fat_image=%s\n' "$KERNEL_IMAGE"
printf 'kernel_fat_device=%s\n' "$DEVICE"
printf 'kernel_fat_sha256=%s\n' "$KERNEL_SHA256"
printf 'kernel_fat_bytes=%s\n' "$(stat -c %s "$KERNEL_IMAGE")"
printf 'mode=%s\n' "$([ "$DRY_RUN" -eq 1 ] && echo dry-run || echo write)"

if [ "$DRY_RUN" -eq 1 ]; then
	printf 'PASS=preflight-only\n'
	exit 0
fi

exec 9>/run/samurai-flash-kernel.lock
flock -n 9 || die "another Linux-side kernel flash is active"
verify_image "$KERNEL_IMAGE" "$KERNEL_SHA256" "$DEVICE"

printf 'WRITE_BEGIN=kernel_fat image=%s device=%s bytes=%s sha256=%s\n' \
	"$KERNEL_IMAGE" "$DEVICE" "$(stat -c %s "$KERNEL_IMAGE")" "$KERNEL_SHA256"
dd if="$KERNEL_IMAGE" of="$DEVICE" bs=4M conv=fsync
sync
blockdev --flushbufs "$DEVICE"
actual=$(sha256sum "$DEVICE" | cut -d ' ' -f 1)
[ "$actual" = "$KERNEL_SHA256" ] ||
	die "kernel FAT readback mismatch: expected=$KERNEL_SHA256 actual=$actual"
printf 'WRITE_OK=kernel_fat device=%s sha256=%s\n' "$DEVICE" "$actual"
printf 'PASS=kernel-fat-written-and-read-back\n'

if [ "$REBOOT" -eq 1 ]; then
	sync
	printf 'REBOOT=requested\n'
	reboot
fi
