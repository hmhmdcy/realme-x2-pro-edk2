#!/bin/sh
#
# One-shot PM8150B USBIN wake test for RMX1931.
#
# Run over Wi-Fi or a serial console, with the USB cable initially unplugged.
# The script arms an RTC safety alarm, suspends the phone, and expects the
# operator to plug the USB cable after the phone is asleep.  A pass requires
# a new usbin-plugin/usbin-src-change IRQ, online=0 -> online=1, and a resume
# before the RTC deadline.  An RTC-only resume is a failure.

set -u

if [ "${SAMURAI_ALLOW_SUSPEND:-0}" != "1" ]; then
	echo "ERROR: set SAMURAI_ALLOW_SUSPEND=1 to allow system suspend" >&2
	exit 2
fi

[ "$(id -u)" -eq 0 ] || {
	echo "ERROR: run as root" >&2
	exit 2
}

wait_unplug=0
if [ "${1:-}" = "--wait-unplug" ]; then
	wait_unplug=1
	shift
fi

seconds=${1:-120}
case "$seconds" in
	''|*[!0-9]*)
		echo "ERROR: sleep seconds must be an integer" >&2
		exit 2
		;;
esac
[ "$seconds" -ge 30 ] || {
	echo "ERROR: use at least 30 seconds so the cable can be plugged" >&2
	exit 2
}

irq_count()
{
	name=$1
	line=$(grep -E "[[:space:]]$name([[:space:]]|$)" /proc/interrupts 2>/dev/null | head -n 1)
	if [ -z "$line" ]; then
		echo 0
		return
	fi
	printf '%s\n' "$line" | awk '
		{
			sum = 0
			for (i = 2; i <= NF; i++)
				if ($i ~ /^[0-9]+$/)
					sum += $i
			print sum
		}
	'
}

wakeup_field()
{
	name=$1
	field=$2
	line=$(grep -E "^$name([[:space:]]|$)" /sys/kernel/debug/wakeup_sources 2>/dev/null | head -n 1)
	if [ -z "$line" ]; then
		echo 0
		return
	fi
	printf '%s\n' "$line" | awk -v f="$field" '{ print $f }'
}

read_int()
{
	if [ -r "$1" ]; then
		cat "$1"
	else
		echo 0
	fi
}

baseline=/tmp/check-usb-pmic-wake-baseline.sh
[ -r "$baseline" ] || {
	echo "ERROR: missing $baseline" >&2
	exit 2
}

if ! sh "$baseline"; then
	echo "ERROR: PMIC wake baseline failed; refusing to suspend" >&2
	exit 1
fi

psy=/sys/class/power_supply/samurai-usb-input
online=$(read_int "$psy/online")
if [ "$online" != "0" ]; then
	if [ "$wait_unplug" -ne 1 ]; then
		echo "ERROR: USB cable is attached (online=$online); unplug it first" >&2
		exit 1
	fi
	echo "UNPLUG_USB_NOW=1"
	echo "Waiting for samurai-usb-input online=0..."
	deadline=$(( $(date +%s) + 300 ))
	while [ "$online" != "0" ]; do
		if [ "$(date +%s)" -ge "$deadline" ]; then
			echo "ERROR: USB cable did not detach within 300 seconds" >&2
			exit 1
		fi
		sleep 1
		online=$(read_int "$psy/online")
	done
fi

udc=/sys/class/udc/a600000.usb
udc_disconnected=0
restore_udc()
{
	[ "$udc_disconnected" -eq 1 ] || return 0
	if [ -w "$udc/soft_connect" ]; then
		printf 'connect\n' >"$udc/soft_connect" 2>/dev/null || true
	fi

	# A plain connect is not always enough after the controller has seen host
	# resets while soft-disconnected.  Rebind DWC3 and recreate the gadget so
	# Windows does not retain a Code 43 "device descriptor failed" port state.
	dwc_driver=/sys/bus/platform/drivers/dwc3-qcom
	if [ -d "$dwc_driver" ]; then
		echo a600000.usb >"$dwc_driver/unbind" 2>/dev/null || true
		sleep 1
		echo a600000.usb >"$dwc_driver/bind" 2>/dev/null || true
		sleep 2
	fi
	if command -v rc-service >/dev/null 2>&1; then
		rc-service samurai-usb restart >/dev/null 2>&1 || true
	fi
}
trap restore_udc EXIT HUP INT TERM

# An unplugged controller can reject system suspend with -EAGAIN while the
# gadget is still logically attached.  Disconnect it for the test and restore
# the UDC on exit.
if [ -w "$udc/soft_connect" ]; then
	printf 'disconnect\n' >"$udc/soft_connect" 2>/dev/null &&
		udc_disconnected=1
fi

log=/tmp/usb-pmic-wake-$(date +%Y%m%d-%H%M%S).log
echo "LOG=$log"
exec 3>&1
exec >>"$log" 2>&1

before_boot=$(cat /proc/sys/kernel/random/boot_id)
before_success=$(read_int /sys/power/suspend_stats/success)
before_irq_plugin=$(irq_count usbin-plugin)
before_irq_src=$(irq_count usbin-src-change)
before_events=$(wakeup_field samurai-usb-input 3)
before_wakeups=$(wakeup_field samurai-usb-input 4)
before_rtc=$(read_int /sys/class/rtc/rtc0/since_epoch)

echo "schema=samurai-usb-pmic-wake-test-v1"
echo "log=$log"
echo "seconds=$seconds"
echo "before.boot_id=$before_boot"
echo "before.suspend_success=$before_success"
echo "before.usbin_plugin_irq=$before_irq_plugin"
echo "before.usbin_src_irq=$before_irq_src"
echo "before.wakeup_events=$before_events"
echo "before.wakeup_count=$before_wakeups"
echo "before.online=$online"
echo "before.udc_state=$(cat "$udc/state" 2>/dev/null)"
echo "before.rtc_epoch=$before_rtc"
echo "IMPORTANT: wait until the phone is asleep (screen off), then plug the USB cable."
echo "SUSPEND_BEGIN=$(date -Is)"
start_epoch=$(date +%s)

rtcwake -m mem -s "$seconds"
rtc_rc=$?
end_epoch=$(date +%s)
elapsed=$((end_epoch - start_epoch))

after_boot=$(cat /proc/sys/kernel/random/boot_id)
after_success=$(read_int /sys/power/suspend_stats/success)
after_irq_plugin=$(irq_count usbin-plugin)
after_irq_src=$(irq_count usbin-src-change)
after_events=$(wakeup_field samurai-usb-input 3)
after_wakeups=$(wakeup_field samurai-usb-input 4)
after_rtc=$(read_int /sys/class/rtc/rtc0/since_epoch)
after_wakealarm=$(read_int /sys/class/rtc/rtc0/wakealarm)
after_online=$(read_int "$psy/online")
pm_wakeup_irq=$(read_int /sys/power/pm_wakeup_irq)

delta_plugin=$((after_irq_plugin - before_irq_plugin))
delta_src=$((after_irq_src - before_irq_src))
delta_events=$((after_events - before_events))
delta_wakeups=$((after_wakeups - before_wakeups))
delta_rtc=$((after_rtc - before_rtc))
delta_usb_irq=$((delta_plugin + delta_src))

echo "SUSPEND_END=$(date -Is)"
echo "elapsed_seconds=$elapsed"
echo "rtcwake_rc=$rtc_rc"
echo "after.boot_id=$after_boot"
echo "after.suspend_success=$after_success"
echo "after.usbin_plugin_irq=$after_irq_plugin"
echo "after.usbin_src_irq=$after_irq_src"
echo "after.wakeup_events=$after_events"
echo "after.wakeup_count=$after_wakeups"
echo "delta.usbin_plugin_irq=$delta_plugin"
echo "delta.usbin_src_irq=$delta_src"
echo "delta.wakeup_events=$delta_events"
echo "delta.wakeup_count=$delta_wakeups"
echo "delta.rtc_seconds=$delta_rtc"
echo "delta.usb_irq=$delta_usb_irq"
echo "pm_wakeup_irq=$pm_wakeup_irq"
echo "after.online=$after_online"
echo "after.udc_state=$(cat "$udc/state" 2>/dev/null)"
echo "after.wakealarm=$after_wakealarm"
echo "--- wakeup_sources ---"
grep -E "^samurai-usb-input([[:space:]]|$)" /sys/kernel/debug/wakeup_sources 2>/dev/null || true
echo "--- relevant dmesg ---"
dmesg | grep -Ei 'usbin|spmi|pdc|samurai-usb|suspend|wake' | tail -n 80 || true

deadline=0
# rtcwake may wait for its alarm in userspace after an early external wake.
# Only the RTC seconds prove that the SoC resumed before the safety alarm.
[ "$delta_rtc" -lt "$((seconds - 5))" ] && deadline=1
same_boot=0
[ "$before_boot" = "$after_boot" ] && same_boot=1
new_suspend=0
[ "$after_success" -gt "$before_success" ] && new_suspend=1
usb_event=0
[ "$delta_usb_irq" -gt 0 ] && usb_event=1

echo "pass.rtcwake=$([ "$rtc_rc" -eq 0 ] && echo 1 || echo 0)"
echo "pass.same_boot=$same_boot"
echo "pass.new_suspend=$new_suspend"
echo "pass.before_deadline=$deadline"
echo "pass.usb_irq=$usb_event"
echo "pass.online=$after_online"

if [ "$rtc_rc" -eq 0 ] && [ "$same_boot" -eq 1 ] &&
   [ "$new_suspend" -eq 1 ] && [ "$deadline" -eq 1 ] &&
   [ "$after_online" -eq 1 ] && [ "$usb_event" -eq 1 ]; then
	echo "RESULT: PASS"
	echo "RESULT: PASS" >&3
	exit 0
fi

echo "RESULT: FAIL"
echo "RESULT: FAIL" >&3
exit 1
