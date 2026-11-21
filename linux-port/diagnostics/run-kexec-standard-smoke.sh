#!/bin/sh
# Run a bounded kexec smoke test with the live FDT and the qcom watchdog.
set -eu

D=${KEXEC_DIAG_DIR:-/root/kexec-diag}
IMAGE=${1:-/var/tmp/Image-v731-standard-kexec}
EXPECTED_SHA256=${2:-5069b1b47d453b11f11ce4a831de6821971b064184452303d4373ae7c8fbd2bd}
CMDLINE=${3:-$(cat /proc/cmdline)}
DTB=${4:-/sys/firmware/fdt}

case "$IMAGE" in
/var/tmp/Image-v731-standard-kexec|/var/tmp/Image-v731-clock-rbcpr) ;;
*)
	echo "refusing unregistered kexec image: $IMAGE" >&2
	exit 2
	;;
esac

test -x "$D/kexec"
test -f "$IMAGE"
test -r "$DTB"
test "$(sha256sum "$IMAGE" | cut -d ' ' -f1)" = "$EXPECTED_SHA256"
test -f "$D/arm-watchdog.py"

cp "$DTB" "$D/live-kexec-smoke.dtb"
sync

"$D/kexec" -u 2>/dev/null || true
"$D/kexec" -l "$IMAGE" --dtb="$D/live-kexec-smoke.dtb" \
	--command-line="$CMDLINE"
test "$(cat /sys/kernel/kexec_loaded)" = 1

# The watchdog process keeps the old PID1 alive long enough to be useful if
# the transition hangs. It must be armed before kexec -e is issued.
nohup python3 "$D/arm-watchdog.py" > "$D/arm-watchdog.log" 2>&1 &
sleep 1
grep -q 'watchdog timeout=30' "$D/arm-watchdog.log"

echo "kexec_loaded=1"
echo "image=$IMAGE"
echo "image_sha256=$EXPECTED_SHA256"
echo "dtb=$DTB"
echo "cmdline=$CMDLINE"
echo "watchdog=armed"

"$D/kexec" -e
