#!/bin/sh
# Read-only one-boot timeline for Wi-Fi, NCM, DHCP and SSH readiness.
# It does not change routing, services, firmware or the USB gadget.
set -eu

if [ "$#" -gt 1 ]; then
	echo "usage: $0 [output-file]" >&2
	exit 2
fi
if [ "$#" -eq 1 ]; then
	parent=$(dirname "$1")
	mkdir -p "$parent" 2>/dev/null || true
	exec >"$1"
fi

section()
{
	printf '\n===== %s =====\n' "$*"
}

run_sh()
{
	printf '\n$ %s\n' "$1"
	sh -c "$1" 2>&1 || true
}

print_file()
{
	printf '\n--- %s ---\n' "$1"
	if [ -r "$1" ]; then
		sed -n '1,240p' "$1" 2>/dev/null || true
	else
		printf 'not readable or absent\n'
	fi
}

section identity
print_file /proc/sys/kernel/random/boot_id
printf 'uptime_seconds='; cut -d. -f1 /proc/uptime
printf 'tainted='; cat /proc/sys/kernel/tainted
printf 'utc='; date -u
uname -a 2>/dev/null || true

section openrc
run_sh 'rc-status -a'
run_sh 'for s in dbus elogind networkmanager wpa_supplicant sshd samurai-radio samurai-usb sleep-inhibitor iio-sensor-proxy tinydm; do rc-service "$s" status 2>&1 || true; done'

section processes
run_sh "ps -eo pid,ppid,etime,comm,args 2>/dev/null |
	grep -E 'NetworkManager|wpa_supplicant|dnsmasq|sshd|samurai|ModemManager|bluetoothd|tinydm|plasmashell|kwin' |
	grep -v -E 'grep|sed' || true"

section kernel_network_log
run_sh "dmesg 2>/dev/null | grep -Ei 'wlan0|ath10k|cfg80211|mac80211|networkmanager|wpa_supplicant|dnsmasq|usb0|dwc3|gadget|udc|ncm|qrtr|firmware|samurai' | tail -n 500"

section network_manager
run_sh 'nmcli -t -f DEVICE,TYPE,STATE,CONNECTION device status 2>&1 || true'
run_sh 'nmcli -f GENERAL,IP4,IP6,DHCP4,WIFI device show wlan0 2>&1 || true'
run_sh 'nmcli -f GENERAL,IP4,IP6,DHCP4 device show usb0 2>&1 || true'

section wifi
run_sh 'iw dev wlan0 info 2>&1 || true'
run_sh 'iw dev wlan0 link 2>&1 || true'
run_sh 'iw dev wlan0 station dump 2>&1 || true'
run_sh 'ip -4 addr show dev wlan0 2>&1 || true'
run_sh 'ip route show 2>&1 || true'
run_sh 'ip neigh show dev wlan0 2>&1 || true'

section usb_ncm
run_sh 'ip -4 addr show dev usb0 2>&1 || true'
run_sh 'ip -s link show dev usb0 2>&1 || true'
run_sh 'ip neigh show dev usb0 2>&1 || true'
run_sh 'cat /sys/class/udc/*/state 2>&1 || true'
run_sh 'cat /sys/kernel/config/usb_gadget/samurai/UDC 2>&1 || true'
run_sh 'cat /sys/class/net/usb0/carrier 2>&1 || true'
run_sh 'pgrep -a dnsmasq 2>&1 || true'
print_file /etc/samurai/usb-dhcp.conf
print_file /var/lib/misc/dnsmasq-usb.leases

section samurai_wifi_markers
for file in \
	boot-started boot-finished ready firmware-check.txt \
	nv-source-hashes.txt nv-snapshot-sha256.txt qrtr-before.txt \
	tftp.log wpa.log nv-after-start.txt; do
	print_file "/run/samurai-wifi/$file"
done
print_file /run/samurai-wifi-boot.log
print_file /var/log/samurai/wifi-boot-failure.log

section sleep_locks
run_sh 'loginctl list-sessions --no-legend 2>&1 || true'
run_sh 'elogind-inhibit --list 2>&1 || true'

section ssh
run_sh "ss -tnp 2>/dev/null | grep -E '(:22|,22) ' || true"

section network_counters
run_sh "cat /proc/net/dev 2>/dev/null | grep -E 'Inter-|wlan0|usb0' || true"
