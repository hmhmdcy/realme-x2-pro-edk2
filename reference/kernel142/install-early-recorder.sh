#!/bin/sh
set -eu
umask 077
test "$(uname -v | cut -d ' ' -f 1)" = '#140'
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k142-preflash/boot-id-private.txt)"
test ! -e /etc/init.d/k142-startup-trace
test ! -e /etc/runlevels/boot/k142-startup-trace
test ! -e /var/lib/samurai/k142-reboot140-startup
test -f /tmp/k142-startup-trace
python3 -m py_compile /var/lib/samurai/k142-pre-reboot/capture-next-startup.py /var/lib/samurai/k142-pre-reboot/check-new-boot.py
for event in irq_handler_entry irq_handler_exit softirq_entry softirq_exit cpu_idle cpu_frequency cpu_frequency_limits suspend_resume device_pm_callback_start device_pm_callback_end timer_expire_entry timer_expire_exit; do
    test "$(find /sys/kernel/tracing/events -name "$event" | wc -l)" = 1
done
sha256sum -c /var/lib/samurai/k135-preflash/gui-config.sha256 > /var/lib/samurai/k142-pre-reboot/gui-config-before-service-check.txt
cp /tmp/k142-startup-trace /etc/init.d/k142-startup-trace
chmod 755 /etc/init.d/k142-startup-trace
sh -n /etc/init.d/k142-startup-trace
rc-update add k142-startup-trace boot > /var/lib/samurai/k142-pre-reboot/service-install-private.txt
test "$(readlink /etc/runlevels/boot/k142-startup-trace)" = /etc/init.d/k142-startup-trace
test ! -e /run/k142-startup-trace.pid
sha256sum /etc/init.d/k142-startup-trace /var/lib/samurai/k142-pre-reboot/capture-next-startup.py /var/lib/samurai/k142-pre-reboot/check-new-boot.py > /var/lib/samurai/k142-pre-reboot/temporary-recorder.sha256
sync
echo K142_EARLY_RECORDER_INSTALLED_DORMANT_CURRENT_BOOT
