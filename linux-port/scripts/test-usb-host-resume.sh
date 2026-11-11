#!/bin/sh
#
# Bounded USB host-resume test for a DWC3 gadget kept connected across
# system sleep.  Run on the handset with a physical recovery path available.
#
# The RTC alarm is only a safety net.  A successful USB resume must keep the
# same boot_id and increase suspend_stats/success before the RTC deadline.
#
set -u

seconds=${1:-90}
log=${2:-/tmp/samurai-usb-host-resume.log}
usb_dev=${USB_DEV:-a600000.usb}
pm_debug_old=$(cat /sys/power/pm_debug_messages 2>/dev/null || echo 0)

if [ "${SAMURAI_ALLOW_SUSPEND:-0}" != "1" ]; then
	echo "refusing suspend: set SAMURAI_ALLOW_SUSPEND=1 and keep a physical recovery path" >&2
	exit 2
fi

case "$seconds" in
*[!0-9]*|'')
	echo "usage: $0 [seconds] [log]" >&2
	exit 2
	;;
esac

if [ ! -e "/sys/bus/platform/devices/$usb_dev" ]; then
	echo "USB platform device not found: $usb_dev" >&2
	exit 2
fi

exec >>"$log" 2>&1

echo "BEGIN=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "BOOT_BEFORE=$(cat /proc/sys/kernel/random/boot_id)"
echo "RELEASE=$(uname -r)"
echo "UPTIME_BEFORE=$(cat /proc/uptime)"
uptime_before=$(awk '{print $1}' /proc/uptime)
echo "STATE=$(cat /sys/power/state)"
echo "MEM_SLEEP=$(cat /sys/power/mem_sleep 2>/dev/null || true)"
echo "WAKEUP=$(cat "/sys/bus/platform/devices/$usb_dev/power/wakeup" 2>/dev/null || true)"
echo "LINK_BEFORE=$(cat "/sys/kernel/debug/usb/$usb_dev/link_state" 2>/dev/null || true)"
echo "UDC_BEFORE=$(for u in /sys/class/udc/*; do printf '%s=%s ' "$(basename "$u")" "$(cat "$u/state" 2>/dev/null)"; done)"
echo "SUSPEND_BEFORE=$(cat /sys/kernel/debug/suspend_stats 2>/dev/null | tr '\n' ' ')"
echo "WAKEUP_SOURCES_BEFORE=$(cat /sys/kernel/debug/wakeup_sources 2>/dev/null | tr '\n' ' ')"
echo "IRQ_BEFORE=$(grep -Ei 'pdc|dwc3|phy_irq|rtc|mp2650|charger' /proc/interrupts 2>/dev/null | tr '\n' ' ')"
echo 1 > /sys/power/pm_debug_messages 2>/dev/null || true
sync

rtcwake -m mem -s "$seconds"
rc=$?

echo "RTCWAKE_RC=$rc"
echo "PM_WAKEUP_IRQ=$(cat /sys/power/pm_wakeup_irq 2>/dev/null || true)"
echo "BOOT_AFTER=$(cat /proc/sys/kernel/random/boot_id)"
echo "UPTIME_AFTER=$(cat /proc/uptime)"
echo "LINK_AFTER=$(cat "/sys/kernel/debug/usb/$usb_dev/link_state" 2>/dev/null || true)"
echo "UDC_AFTER=$(for u in /sys/class/udc/*; do printf '%s=%s ' "$(basename "$u")" "$(cat "$u/state" 2>/dev/null)"; done)"
echo "SUSPEND_AFTER=$(cat /sys/kernel/debug/suspend_stats 2>/dev/null | tr '\n' ' ')"
echo "WAKEUP_SOURCES_AFTER=$(cat /sys/kernel/debug/wakeup_sources 2>/dev/null | tr '\n' ' ')"
echo "IRQ_AFTER=$(grep -Ei 'pdc|dwc3|phy_irq|rtc|mp2650|charger' /proc/interrupts 2>/dev/null | tr '\n' ' ')"
echo "$pm_debug_old" > /sys/power/pm_debug_messages 2>/dev/null || true
uptime_after=$(awk '{print $1}' /proc/uptime)
echo "SUSPEND_SECONDS=$(awk -v a="$uptime_before" -v b="$uptime_after" 'BEGIN { printf \"%.2f\", b - a }')"
echo "DONE=$(date -u +%Y-%m-%dT%H:%M:%SZ)"

exit "$rc"
