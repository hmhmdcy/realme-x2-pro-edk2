#!/bin/sh
#
# Write the boot/logdump pair from the running Linux system.
# The partitions are resolved by GPT label, never by enumeration order.
#
set -eu

BOOT_IMAGE=
BOOT_SHA256=
LOGDUMP_IMAGE=
LOGDUMP_SHA256=
DRY_RUN=0
REBOOT=0

usage() {
	cat <<'EOF'
usage: flash-pair-linux.sh \
  --boot IMAGE --boot-sha256 SHA256 \
  --logdump IMAGE --logdump-sha256 SHA256 \
  [--dry-run] [--reboot]

Both images are verified locally and against their partition sizes before
either partition is written. logdump is written first and read back before
boot is touched. Mounted targets and partial pairs are rejected.
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
	name=$1
	image=$2
	expected=$3
	device=$4

	[ -f "$image" ] || die "$name image not found: $image"
	expected=$(lower_hex "$expected")
	[ "${#expected}" -eq 64 ] || die "$name SHA-256 is not 64 hex characters"

	image_size=$(stat -c %s "$image")
	device_size=$(blockdev --getsize64 "$device")
	[ "$image_size" -eq "$device_size" ] ||
		die "$name size mismatch: image=$image_size partition=$device_size"

	actual=$(sha256sum "$image" | cut -d ' ' -f 1)
	[ "$actual" = "$expected" ] ||
		die "$name image hash mismatch: expected=$expected actual=$actual"

	is_mounted "$device" && die "$name target is mounted: $device"
	[ "$(blockdev --getro "$device")" -eq 0 ] ||
		die "$name target is read-only: $device"
}

write_and_verify() {
	name=$1
	image=$2
	expected=$3
	device=$4

	printf 'WRITE_BEGIN=%s image=%s device=%s bytes=%s sha256=%s\n' \
		"$name" "$image" "$device" "$(stat -c %s "$image")" "$expected"
	dd if="$image" of="$device" bs=4M conv=fsync
	sync
	blockdev --flushbufs "$device"
	actual=$(sha256sum "$device" | cut -d ' ' -f 1)
	[ "$actual" = "$expected" ] ||
		die "$name readback mismatch: expected=$expected actual=$actual"
	printf 'WRITE_OK=%s device=%s sha256=%s\n' "$name" "$device" "$actual"
}

while [ "$#" -gt 0 ]; do
	case "$1" in
	--boot)
		[ "$#" -ge 2 ] || die "--boot needs an argument"
		BOOT_IMAGE=$2
		shift 2
		;;
	--boot-sha256)
		[ "$#" -ge 2 ] || die "--boot-sha256 needs an argument"
		BOOT_SHA256=$2
		shift 2
		;;
	--logdump)
		[ "$#" -ge 2 ] || die "--logdump needs an argument"
		LOGDUMP_IMAGE=$2
		shift 2
		;;
	--logdump-sha256)
		[ "$#" -ge 2 ] || die "--logdump-sha256 needs an argument"
		LOGDUMP_SHA256=$2
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
[ -n "$BOOT_IMAGE" ] && [ -n "$BOOT_SHA256" ] ||
	die "--boot and --boot-sha256 are required"
[ -n "$LOGDUMP_IMAGE" ] && [ -n "$LOGDUMP_SHA256" ] ||
	die "--logdump and --logdump-sha256 are required"

BOOT_SHA256=$(lower_hex "$BOOT_SHA256")
LOGDUMP_SHA256=$(lower_hex "$LOGDUMP_SHA256")
BOOT_DEVICE=$(partition_by_label boot)
LOGDUMP_DEVICE=$(partition_by_label logdump)
[ "$BOOT_DEVICE" != "$LOGDUMP_DEVICE" ] || die "boot and logdump resolved to the same device"

verify_image boot "$BOOT_IMAGE" "$BOOT_SHA256" "$BOOT_DEVICE"
verify_image logdump "$LOGDUMP_IMAGE" "$LOGDUMP_SHA256" "$LOGDUMP_DEVICE"

printf 'schema=samurai-linux-side-pair-flash-v1\n'
printf 'boot_image=%s\n' "$BOOT_IMAGE"
printf 'boot_device=%s\n' "$BOOT_DEVICE"
printf 'boot_sha256=%s\n' "$BOOT_SHA256"
printf 'boot_bytes=%s\n' "$(stat -c %s "$BOOT_IMAGE")"
printf 'logdump_image=%s\n' "$LOGDUMP_IMAGE"
printf 'logdump_device=%s\n' "$LOGDUMP_DEVICE"
printf 'logdump_sha256=%s\n' "$LOGDUMP_SHA256"
printf 'logdump_bytes=%s\n' "$(stat -c %s "$LOGDUMP_IMAGE")"
printf 'mode=%s\n' "$([ "$DRY_RUN" -eq 1 ] && echo dry-run || echo write)"

if [ "$DRY_RUN" -eq 1 ]; then
	printf 'PASS=preflight-only\n'
	exit 0
fi

exec 9>/run/samurai-flash-pair.lock
flock -n 9 || die "another Linux-side pair flash is active"

# Recheck after acquiring the lock.
verify_image boot "$BOOT_IMAGE" "$BOOT_SHA256" "$BOOT_DEVICE"
verify_image logdump "$LOGDUMP_IMAGE" "$LOGDUMP_SHA256" "$LOGDUMP_DEVICE"

write_and_verify logdump "$LOGDUMP_IMAGE" "$LOGDUMP_SHA256" "$LOGDUMP_DEVICE"
write_and_verify boot "$BOOT_IMAGE" "$BOOT_SHA256" "$BOOT_DEVICE"

printf 'PASS=pair-written-and-read-back\n'
if [ "$REBOOT" -eq 1 ]; then
	sync
	printf 'REBOOT=requested\n'
	reboot
fi
