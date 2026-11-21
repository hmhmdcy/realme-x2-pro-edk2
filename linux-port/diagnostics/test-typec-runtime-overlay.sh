#!/bin/sh
set -u

LOG=/root/typec-runtime-test.log
MODULE=/root/samurai_dtbo_loader.ko
DTBO=/root/typec-sink.dtbo

{
	date -Is
	echo PRE
	cat /proc/sys/kernel/random/boot_id
	cat /proc/sys/kernel/tainted
	cat /sys/class/udc/a600000.usb/state
	cat /sys/class/power_supply/mp2650-input/online
	ls -l /sys/class/typec 2>&1
	sha256sum "${DTBO}" "${MODULE}"

	cp "${DTBO}" /lib/firmware/typec-sink.dtbo
	insmod "${MODULE}"
	echo "INSMOD_RC=$?"
	sleep 8

	echo AFTER
	cat /proc/sys/kernel/tainted
	cat /sys/class/udc/a600000.usb/state
	cat /sys/class/power_supply/mp2650-input/online
	find /sys/class/typec -maxdepth 3 \( -type f -o -type l \) 2>/dev/null
	for node in /sys/class/typec/port0 \
		/sys/class/typec/port0-partner \
		/sys/class/typec/port0-cable; do
		echo "NODE=${node}"
		for file in "${node}"/*; do
			test -f "${file}" || continue
			printf '%s=' "${file}"
			cat "${file}" 2>/dev/null
		done
	done
	ls -l /sys/bus/platform/devices/*typec* \
		/sys/bus/platform/drivers/qcom,pmic-typec 2>&1
	cat /proc/interrupts | grep -E 'pmic_arb|PDC' | tail -n 40
	dmesg | tail -n 120
} >>"${LOG}" 2>&1

tail -n 240 "${LOG}"
