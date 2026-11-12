#!/bin/sh
#
# Write only the logdump (kernel FAT) partition from the running Linux system.
# The boot partition is never opened for writing.
#
set -eu

IMAGE=
IMAGE_SHA256=
EXPECTED_CURRENT_SHA256=
DRY_RUN=0
REBOOT=0

usage() {
	cat <<'EOF'
usage: flash-logdump-linux.sh \
  --logdump IMAGE --logdump-sha256 SHA256 \
  --expected-current-sha256 SHA256 \
  [--dry-run] [--reboot]

The target is resolved by GPT label logdump.  The current partition must
match --expected-current-sha256 before anything is written.  The image is
written, synced, flushed and read back.  The boot partition is untouched.
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

while [ "$#" -gt 0 ]; do
	case "$1" in
	--logdump)
		[ "$#" -ge 2 ] || die "--logdump needs an argument"
		IMAGE=$2
		shift 2
		;;
	--logdump-sha256)
		[ "$#" -ge 2 ] || die "--logdump-sha256 needs an argument"
		IMAGE_SHA256=$2
		shift 2
		;;
	--expected-current-sha256)
		[ "$#" -ge 2 ] || die "--expected-current-sha256 needs an argument"
		EXPECTED_CURRENT_SHA256=$2
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
[ -n "$IMAGE" ] && [ -n "$IMAGE_SHA256" ] && [ -n "$EXPECTED_CURRENT_SHA256" ] ||
	die "--logdump, --logdump-sha256 and --expected-current-sha256 are required"

IMAGE_SHA256=$(lower_hex "$IMAGE_SHA256")
EXPECTED_CURRENT_SHA256=$(lower_hex "$EXPECTED_CURRENT_SHA256")
[ "${#IMAGE_SHA256}" -eq 64 ] || die "image SHA-256 is not 64 hex characters"
[ "${#EXPECTED_CURRENT_SHA256}" -eq 64 ] ||
	die "current SHA-256 is not 64 hex characters"

device=$(partition_by_label logdump)
[ -f "$IMAGE" ] || die "image not found: $IMAGE"
[ "$(stat -c %s "$IMAGE")" -eq "$(blockdev --getsize64 "$device")" ] ||
	die "image/partition size mismatch"
[ "$(sha256sum "$IMAGE" | cut -d ' ' -f 1)" = "$IMAGE_SHA256" ] ||
	die "image hash mismatch"
is_mounted "$device" && die "target is mounted: $device"
[ "$(blockdev --getro "$device")" -eq 0 ] || die "target is read-only: $device"

current=$(sha256sum "$device" | cut -d ' ' -f 1)
[ "$current" = "$EXPECTED_CURRENT_SHA256" ] ||
	die "current logdump hash mismatch: expected=$EXPECTED_CURRENT_SHA256 actual=$current"

printf 'schema=samurai-logdump-only-flash-v1\n'
printf 'device=%s\n' "$device"
printf 'image=%s\n' "$IMAGE"
printf 'image_sha256=%s\n' "$IMAGE_SHA256"
printf 'image_bytes=%s\n' "$(stat -c %s "$IMAGE")"
printf 'current_sha256=%s\n' "$current"
printf 'mode=%s\n' "$([ "$DRY_RUN" -eq 1 ] && echo dry-run || echo write)"

if [ "$DRY_RUN" -eq 1 ]; then
	printf 'PASS=preflight-only\n'
	exit 0
fi

exec 9>/run/samurai-flash-logdump.lock
flock -n 9 || die "another logdump flash is active"

current=$(sha256sum "$device" | cut -d ' ' -f 1)
[ "$current" = "$EXPECTED_CURRENT_SHA256" ] ||
	die "current logdump changed before write: $current"
[ "$(sha256sum "$IMAGE" | cut -d ' ' -f 1)" = "$IMAGE_SHA256" ] ||
	die "image changed before write"

printf 'WRITE_BEGIN=logdump device=%s bytes=%s sha256=%s\n' \
	"$device" "$(stat -c %s "$IMAGE")" "$IMAGE_SHA256"
dd if="$IMAGE" of="$device" bs=4M conv=fsync
sync
blockdev --flushbufs "$device"

actual=$(sha256sum "$device" | cut -d ' ' -f 1)
[ "$actual" = "$IMAGE_SHA256" ] ||
	die "readback mismatch: expected=$IMAGE_SHA256 actual=$actual"

printf 'WRITE_OK=logdump device=%s sha256=%s\n' "$device" "$actual"
printf 'PASS=logdump-written-and-read-back\n'

if [ "$REBOOT" -eq 1 ]; then
	sync
	printf 'REBOOT=requested\n'
	reboot
fi
