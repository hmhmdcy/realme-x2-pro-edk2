#!/bin/sh
# Current live boot, after two logged frame-done timeouts; save state first.
# Reuse audited session78 event/CRC tool, no explicit CRTC disable/panel cycle.
set -eu
[ "$(cat /proc/sys/kernel/random/boot_id)" = 87753933-4992-45d2-aaf5-d9db9c11d1a3 ]
[ "$(sha256sum /tmp/kms-pageflip | cut -d ' ' -f1)" = 7abbfa366bc688b50379f2fee65f54510b7805d0c498f7930e0f4531b96cd42b ]
[ ! -e /tmp/k81-pageflip-after-timeouts.txt ]
! pidof kms-pageflip
cat /sys/kernel/debug/dri/1/encoder-0/status >/tmp/k81-probe-before-encoder.txt
dmesg >/tmp/k81-probe-before-dmesg.txt
{ cat /proc/uptime; /tmp/kms-pageflip /dev/dri/card1 0; echo tool_rc=$?; cat /proc/uptime; } >/tmp/k81-pageflip-after-timeouts.txt 2>&1
cat /sys/kernel/debug/dri/1/encoder-0/status >/tmp/k81-probe-after-encoder.txt
cat /sys/kernel/debug/dri/1/state >/tmp/k81-probe-after-drm-state.txt
cat /sys/kernel/debug/dri/1/kms >/tmp/k81-probe-after-kms.txt
cat /sys/kernel/debug/clk/clk_summary >/tmp/k81-probe-after-clocks.txt
dmesg >/tmp/k81-probe-after-dmesg.txt
cat /sys/class/power_supply/bq28z610-0/uevent >/tmp/k81-probe-after-battery.txt
sha256sum /tmp/k81-timeout-clocks.txt /tmp/k81-timeout-encoder.txt /tmp/k81-timeout-drm-state.txt \
    /tmp/k81-timeout-kms.txt /tmp/k81-timeout-dmesg.txt /tmp/k81-timeout-processes.txt \
    /tmp/k81-probe-before-encoder.txt /tmp/k81-probe-before-dmesg.txt /tmp/k81-pageflip-after-timeouts.txt \
    /tmp/k81-probe-after-encoder.txt /tmp/k81-probe-after-drm-state.txt /tmp/k81-probe-after-kms.txt \
    /tmp/k81-probe-after-clocks.txt /tmp/k81-probe-after-dmesg.txt /tmp/k81-probe-after-battery.txt >/tmp/k81-display-device-hashes.txt
printf 'probe_before\n'; cat /tmp/k81-probe-before-encoder.txt
printf 'probe_after\n'; cat /tmp/k81-probe-after-encoder.txt
tail -n 7 /tmp/k81-pageflip-after-timeouts.txt
