#!/bin/bash
# Apply the rootfs-side NCM layering fix to an existing F2FS image.
#
# Background: the diagnostic initramfs created the NCM gadget, forced
# `ip link set usb0 up`, and added 169.254.42.1 itself.  The distro rootfs
# replaces that path with usb-signaller (configfs gadget, L4/L6),
# NetworkManager (profile policy, L5), unudhcpd (DHCP, L5) and OpenSSH.
# None of those owns the "bring the netdev up" step, so a fresh rootfs boots
# with a correctly enumerated gadget whose usb0 is DOWN: the host can send,
# the device receives nothing, and no DHCP/ARP/SSH ever completes.
#
# This script installs the missing board glue as one supervised OpenRC
# service and rewrites the existing runlevel link.  It is idempotent.
#
# Usage: apply-rootfs-ncm-layer-fix.sh RAW_IMAGE INITD WATCHDOG [USER]

set -euo pipefail

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

raw=${1:?usage: $0 RAW_IMAGE INITD WATCHDOG [USER]}
initd=${2:?usage: $0 RAW_IMAGE INITD WATCHDOG [USER]}
watchdog=${3:?usage: $0 RAW_IMAGE INITD WATCHDOG [USER]}
user=${4:-user}

mountpoint=$(mktemp -d)
cleanup() {
	sync
	umount "$mountpoint" 2>/dev/null || true
	rmdir "$mountpoint" 2>/dev/null || true
}
trap cleanup EXIT

mount -t f2fs,loop "$raw" "$mountpoint"
root=$mountpoint

install -Dm755 "$initd" "$root/etc/init.d/samurai-usb-network"
install -Dm755 "$watchdog" "$root/usr/sbin/samurai-usb-network-watchdog"

# OpenRC resolves a service by /etc/init.d/<name>; the daemon spawns the
# command named inside it.  A mismatch between the two (an init script that
# still points at a removed helper) makes supervise-daemon respawn a missing
# binary forever, so the link is never configured.  Verify the exact path.
service_command=$(sed -n 's/^command="\(.*\)"$/\1/p' \
	"$root/etc/init.d/samurai-usb-network" | tail -n 1)
[ -n "$service_command" ] || {
	echo "samurai-usb-network has no command=" >&2
	exit 1
}
[ -x "$root$service_command" ] || {
	echo "init script command is missing: $service_command" >&2
	exit 1
}

# The one-shot boot service was enabled before usb0 existed and a duplicate
# default link made OpenRC treat it as already started.  Both links are
# removed; the supervised service below starts at default and waits.
for level in boot default; do
	rm -f "$root/etc/runlevels/$level/samurai-ncm-fallback"
	rm -f "$root/etc/runlevels/$level/samurai-usb-network"
done
rm -f "$root/etc/init.d/samurai-ncm-fallback"
rm -f "$root/usr/sbin/samurai-ncm-watchdog"

mkdir -p "$root/etc/runlevels/default"
ln -s /etc/init.d/samurai-usb-network \
	"$root/etc/runlevels/default/samurai-usb-network"

# unudhcpd.usb0 is a boot service in the postmarketOS baseline.  It must stay
# there to match the distro, but the watchdog restarts it after the real
# netdev exists.  Repair the template symlink if a package transaction left
# only the runlevel link behind.
if [ ! -e "$root/etc/init.d/unudhcpd.usb0" ] &&
	[ ! -L "$root/etc/init.d/unudhcpd.usb0" ]; then
	ln -s /etc/init.d/unudhcpd "$root/etc/init.d/unudhcpd.usb0"
fi

# Keep /etc/unudhcpd.conf and /etc/conf.d/unudhcpd on the same subnet as the
# NetworkManager developer profile.  The distro defaults are .41/.42.
for file in "$root/etc/unudhcpd.conf" "$root/etc/conf.d/unudhcpd"; do
	[ -f "$file" ] || continue
	sed -i \
		-e 's/^UNUDHCPD_SERVER=.*/UNUDHCPD_SERVER="172.16.42.1"/' \
		-e 's/^UNUDHCPD_CLIENT=.*/UNUDHCPD_CLIENT="172.16.42.2"/' \
		"$file"
done

# On this port the developer profile cannot be the sole owner of usb0:
# NetworkManager only activates it when carrier is already 1, while the
# gadget only raises carrier after the netdev is UP.  The glue service
# therefore marks usb0 unmanaged and owns the link + address itself.  The
# profile is still created by the mode script; it is simply not the path
# that establishes the link.

# Descriptor values (VID/PID, MaxPower, qmult) are left exactly as the
# board package ships them: they already enumerate correctly on this host,
# and the defect being fixed is the missing link enablement, not the
# descriptor.  A fixed dev_addr/host_addr pair (as the initramfs used) is
# still a separate open item because usb-signaller has no field for it.

# The user must exist before sshd can authenticate.  Fail loudly instead of
# flashing an image whose SSH path is untestable.
entry=$(awk -F: -v u="$user" '$1 == u { print $3 ":" $4 ":" $6 }' \
	"$root/etc/passwd")
[ -n "$entry" ] || { echo "missing user: $user" >&2; exit 1; }
uid=${entry%%:*}
rest=${entry#*:}
gid=${rest%%:*}
home=${rest#*:}

ak="$root${home}/.ssh/authorized_keys"
if [ -f "$ak" ]; then
	chown -R "$uid:$gid" "$root${home}/.ssh"
	chmod 700 "$root${home}/.ssh"
	chmod 600 "$ak"
fi

# Modules for the running kernel are a hard prerequisite for Wi-Fi/radio and
# for hci_uart.  Their absence was one of the switch_root misses.
moddir="$root/lib/modules"
if ! ls -d "$moddir"/7.3.1-* >/dev/null 2>&1; then
	echo "warning: no /lib/modules/7.3.1-* in image" >&2
fi

# Record what was installed so the flash script and docs can cite it.
cat >"$root/etc/samurai-ncm-layer" <<'EOF'
LAYER=L6 board glue
GADGET=usb-signaller (configfs, L4/L6)
ADDRESS=NetworkManager developer profile (L5)
DHCP=unudhcpd.usb0 (L5)
SSH=sshd (L5)
GLUE=samurai-usb-network (L6, supervised)
EOF

echo "installed samurai-usb-network"
ls -l "$root/etc/runlevels/default/samurai-usb-network"
echo "user: $user uid=$uid gid=$gid home=$home"

# The retired fallback package once appended a record to the apk database by
# hand.  That record is invalid for apk-tools 3 and makes every later
# `apk` command fail with "v2 database format error", so drop it here.
python3 "$script_dir/repair-apkdb.py" "$root" || {
	echo "apk database repair failed" >&2
	exit 1
}
