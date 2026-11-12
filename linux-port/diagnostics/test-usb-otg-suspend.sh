#!/bin/sh
# SPDX-License-Identifier: BSD-3-Clause
#
# Run a bounded RTC suspend on the OTG candidate.  Start this with nohup so
# the USB-NCM SSH connection may disappear without killing the test.

set -u

seconds=${1:-15}
case $seconds in
''|*[!0-9]*) echo "usage: $0 [seconds]" >&2; exit 2 ;;
esac
[ "$seconds" -ge 2 ] || { echo "usage: $0 [seconds]" >&2; exit 2; }

log=/var/log/samurai/usb-otg-suspend.log

log_event()
{
	mkdir -p "${log%/*}"
	printf '%s %s\n' "$(date -Is)" "$*" >>"$log"
}

snapshot()
{
	state=$(cat /sys/class/udc/a600000.usb/state 2>/dev/null || echo missing)
	carrier=$(cat /sys/class/net/usb0/carrier 2>/dev/null || echo missing)
	success=$(cat /sys/power/suspend_stats/success 2>/dev/null || echo missing)
	fail=$(cat /sys/power/suspend_stats/fail 2>/dev/null || echo missing)
	pm_wakeup_irq=$(cat /sys/power/pm_wakeup_irq 2>/dev/null || echo missing)
	log_event "STATE udc=$state carrier=$carrier success=$success fail=$fail pm_wakeup_irq=$pm_wakeup_irq"
}

mkdir -p "${log%/*}"
log_event "BEGIN seconds=$seconds boot_id=$(cat /proc/sys/kernel/random/boot_id)"
snapshot

start_epoch=$(date +%s)
rtcwake -m mem -s "$seconds"
rc=$?
end_epoch=$(date +%s)
elapsed=$((end_epoch - start_epoch))

log_event "RTCWAKE_RC=$rc elapsed_seconds=$elapsed requested_seconds=$seconds"
if [ "$elapsed" -lt $((seconds - 2)) ]; then
	log_event "FAIL early_wake elapsed_seconds=$elapsed requested_seconds=$seconds"
	rc=1
fi
snapshot
dmesg | grep -Ei 'PM: suspend|suspend exit|dwc3|typec|tcpm|xhci' |
	tail -n 80 >>"$log"
log_event "END boot_id=$(cat /proc/sys/kernel/random/boot_id)"

if [ "$rc" -eq 0 ]; then
	log_event "RESULT=PASS"
else
	log_event "RESULT=FAIL rc=$rc"
fi
[ "$rc" -eq 0 ]
