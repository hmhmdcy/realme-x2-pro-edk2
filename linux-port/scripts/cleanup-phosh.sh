#!/bin/sh
# Remove the Phosh/Phoc desktop stack and keep Plasma Mobile working.
#
# Default is a dry run. Use --apply to make changes.
set -eu

apply=0
if [ "${1:-}" = "--apply" ]; then
	apply=1
elif [ -n "${1:-}" ]; then
	echo "usage: $0 [--apply]" >&2
	exit 2
fi

if ! pgrep -x kwin_wayland >/dev/null || ! pgrep -x plasmashell >/dev/null; then
	echo "Plasma Mobile is not running; refusing to remove Phosh." >&2
	exit 1
fi

# These are shared runtime/config packages that happen to be pulled in by
# postmarketos-ui-phosh. Keep them explicit so apk does not treat them as
# orphaned when the Phosh meta package is removed.
keep="
	bash
	desktop-file-utils
	postmarketos-base-ui-qt-wayland
	postmarketos-base-ui-qt-tweaks
	postmarketos-artwork-wallpapers-plasma
	postmarketos-artwork-wallpapers
	colord
	libseat
	libaccountsservice
	apk-polkit-rs
	cellbroadcastd
	fwupd
	postmarketos-base-fwupd
	power-profiles-daemon
	adwaita-icon-theme
	setxkbmap
	gst-thumbnailers
	dconf
	xdg-user-dirs
	xdg-user-dirs-gtk
	hunspell-en-us
"

remove="
	postmarketos-ui-phosh
	postmarketos-ui-phosh-openrc
	postmarketos-ui-phosh-default-osk
	phosh
	phoc
	phosh-schemas
	phosh-portalsconf
	phosh-wallpapers
	sound-theme-phosh
	libphosh
	stevia
	greetd
	greetd-openrc
	greetd-phrog
	greetd-phrog-schemas
	xdg-desktop-portal-phosh
	xdg-desktop-portal-wlr
	xdg-desktop-portal-wlr-openrc
	samurai-refresh
	wlr-randr
	grim
"

installed=""
for p in $remove; do
	if apk info -e "$p" >/dev/null 2>&1; then
		installed="$installed $p"
	fi
done

if [ -z "$installed" ]; then
	echo "no Phosh packages installed; nothing to remove"
	exit 0
fi

if [ "$apply" -eq 1 ]; then
	ts=$(date +%Y%m%d-%H%M%S)
	backup=/root/pre-phosh-cleanup-$ts
	mkdir -p "$backup"
	cp /etc/apk/world "$backup/world"
	apk info -v > "$backup/packages.txt"
	rc-status --all > "$backup/rc-status.txt" 2>&1 || true
	echo "backup: $backup"
fi

# Mark shared packages as explicit world entries before simulating/deleting.
for p in $keep; do
	if apk info -e "$p" >/dev/null 2>&1; then
		apk add --no-progress "$p"
	fi
done

echo "keep:"
for p in $keep; do
	apk info -e "$p" >/dev/null 2>&1 && echo "  $p"
done
echo "remove:$installed"
echo "--- apk del simulation ---"
apk del --simulate --no-progress $installed

if [ "$apply" -ne 1 ]; then
	echo
	echo "dry run only; re-run with --apply to execute"
	exit 0
fi

apk del --no-progress $installed

tinydm-set-session -s /usr/share/wayland-sessions/plasma-mobile.desktop
rc-update add tinydm default
rc-update del greetd default 2>/dev/null || true

rm -rf /etc/phosh /etc/phoc /etc/greetd /etc/conf.d/greetd \
	/home/cy122/.config/phosh \
	/home/cy122/.local/share/phosh \
	/home/cy122/.cache/phosh \
	/home/cy122/.local/state/phoc \
	/var/lib/greetd
rm -f /home/cy122/.local/state/samurai-phosh-*

apk cache clean >/dev/null 2>&1 || true
find /var/cache/apk -maxdepth 1 -type f -name '*.apk' -delete

echo "cleanup complete"
echo "verify:"
echo "  apk info -e phosh phoc greetd"
echo "  rc-update show | grep -E 'tinydm|greetd'"
echo "  kscreen-doctor -o"
