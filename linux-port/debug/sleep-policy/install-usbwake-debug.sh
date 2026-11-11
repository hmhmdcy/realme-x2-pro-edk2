#!/bin/sh
# Install the optional, debug-only USBwake OpenRC service.
set -eu

here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
root=${DESTDIR:-}
root=${root%/}
apply=0
enable=0
mode=${USBWAKE_GUARD_MODE:-either}

usage() {
	cat <<EOF
Usage: $0 [--apply] [--enable] [--mode either|power|ncm]

Without --apply this prints the install plan. --enable implies --apply and
installs the service in the default runlevel. This is a debug-only helper;
it is not part of the production board package.
EOF
}

while [ "$#" -gt 0 ]; do
	case "$1" in
	--apply)
		apply=1
		;;
	--enable)
		apply=1
		enable=1
		;;
	--mode)
		shift
		[ "$#" -gt 0 ] || {
			echo "--mode needs an argument" >&2
			exit 2
		}
		mode=$1
		;;
	-h|--help)
		usage
		exit 0
		;;
	*)
		echo "unknown argument: $1" >&2
		usage >&2
		exit 2
		;;
	esac
	shift
done

case "$mode" in
either|power|ncm)
	;;
*)
	echo "invalid mode: $mode" >&2
	exit 2
	;;
esac

if [ "$apply" -eq 0 ]; then
	cat <<EOF
dry-run:
  /usr/libexec/usbwake-guard
  /usr/libexec/usbwake-run
  /etc/usbwake-sleep-inhibitor.conf
  /etc/init.d/usbwake-debug
  /etc/conf.d/usbwake-debug
  mode=$mode
Use --apply to install; add --enable to start it in the default runlevel.
EOF
	exit 0
fi

[ "$(id -u)" -eq 0 ] || {
	echo "must run as root" >&2
	exit 1
}

if [ "$enable" -eq 1 ] && [ -n "$root" ]; then
	echo "--enable is not supported with DESTDIR" >&2
	exit 2
fi

install -Dm755 "$here/usbwake-guard" "$root/usr/libexec/usbwake-guard"
install -Dm755 "$here/run-usbwake-guard.sh" "$root/usr/libexec/usbwake-run"
install -Dm644 "$here/usbwake-sleep-inhibitor.conf" \
	"$root/etc/usbwake-sleep-inhibitor.conf"
install -Dm755 "$here/usbwake-debug.initd" "$root/etc/init.d/usbwake-debug"
install -Dm644 "$here/usbwake-debug.confd" "$root/etc/conf.d/usbwake-debug"
sed -i "s/^USBWAKE_GUARD_MODE=.*/USBWAKE_GUARD_MODE=\"$mode\"/" \
	"$root/etc/conf.d/usbwake-debug"

if [ "$enable" -eq 1 ]; then
	rc-update add usbwake-debug default
	rc-service usbwake-debug restart
else
	echo "installed; start with: rc-service usbwake-debug start"
fi
