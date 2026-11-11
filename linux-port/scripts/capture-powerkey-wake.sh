#!/bin/sh
#
# Manual gate: run while the panel is DPMS Off, then press the physical
# power key once. This is a read-only trace capture; it does not flash or
# change the production power policy.
#
# Expected:
#   before = Off,<brightness>,bl_power=4
#   POWER_DOWN/POWER_UP
#   drm_panel_backlight phase=0 -> dpu_first_frame_backlight ret=0 -> phase=1
#   after  = On,enabled,<brightness>,bl_power=0
#   no HBM/brightness/DCS errors and no KWin Atomic commit failed
#   the user visually confirms that the physical panel is lit.
#
set -u

T=/sys/kernel/debug/tracing
LOG=/home/cy122/.local/state/tinydm.log
OUT=/tmp/powerkey-wake.log
DMESG=/tmp/powerkey-wake-dmesg.log
DSI=$(ls -d /sys/class/drm/card*-DSI-1 2>/dev/null | head -1)
BL=$(ls -d /sys/class/backlight/* 2>/dev/null | head -1)
BEFORE_LOG=$(wc -l < "$LOG" 2>/dev/null || echo 0)
BEFORE_EBUSY=$(grep -c "Atomic commit failed" "$LOG" 2>/dev/null || true)

{
	echo "start=$(date -Iseconds)"
	echo "dsi=$DSI"
	echo "backlight=$BL"
	echo "before=$(cat "$DSI/dpms"),$(cat "$BL/brightness"),$(cat "$BL/bl_power")"

	printf 0 > "$T/tracing_on"
	: > "$T/trace"
	for e in \
		drm_panel/drm_panel_backlight \
		dpu/dpu_first_frame_backlight \
		dpu/dpu_crtc_enable \
		dpu/dpu_crtc_disable \
		dpu/dpu_enc_enable \
		dpu/dpu_enc_disable
	do
		printf 1 > "$T/events/$e/enable"
	done
	printf 1 > "$T/tracing_on"
	dmesg -C
	echo "ready_for_power_key=$(date -Iseconds)"

	python3 /tmp/wait-powerkey.py 180
	echo "powerkey_rc=$?"
	sleep 5

	echo "after=$(cat "$DSI/dpms"),$(cat "$DSI/enabled"),$(cat "$BL/brightness"),$(cat "$BL/bl_power")"
	printf 0 > "$T/tracing_on"
	cat "$T/trace"
	dmesg > "$DMESG"
	echo "dmesg_filtered:"
	grep -iE "sofef03f|panel|dsi|backlight|brightness|HBM|error|fail|timeout" "$DMESG" || true
	echo "kwin_new_log:"
	sed -n "$((BEFORE_LOG + 1)),\$p" "$LOG"
	echo "kwin_ebusy_before=$BEFORE_EBUSY after=$(grep -c 'Atomic commit failed' "$LOG" 2>/dev/null || true)"
	echo "end=$(date -Iseconds)"

	for e in \
		drm_panel/drm_panel_backlight \
		dpu/dpu_first_frame_backlight \
		dpu/dpu_crtc_enable \
		dpu/dpu_crtc_disable \
		dpu/dpu_enc_enable \
		dpu/dpu_enc_disable
	do
		printf 0 > "$T/events/$e/enable"
	done
} > "$OUT" 2>&1

cat "$OUT"
