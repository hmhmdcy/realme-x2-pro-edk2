#!/bin/sh
# Device-side launcher for the debugfs clock-sweep image.
set -eu

D=${KEXEC_DIAG_DIR:-/root/kexec-diag}

test -x "$D/kexec"
test -f "$D/Image-diag"
test -f "$D/arm-watchdog.py"

cp /sys/firmware/fdt "$D/live.dtb"
sync

"$D/kexec" -u 2>/dev/null || true
"$D/kexec" -l "$D/Image-diag" --dtb="$D/live.dtb" \
    --command-line="console=tty0 loglevel=4 panic=15 clk_ignore_unused"
test "$(cat /sys/kernel/kexec_loaded)" = 1

nohup python3 "$D/arm-watchdog.py" >"$D/arm-watchdog.log" 2>&1 &
sleep 1
cat "$D/arm-watchdog.log"

"$D/kexec" -e
