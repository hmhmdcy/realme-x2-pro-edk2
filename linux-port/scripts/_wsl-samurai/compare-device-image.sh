#!/bin/sh
# Final consistency: the delivery image and the device should present the
# same package set, the same board repository, and a healthy systemd.
set -u
SUDO() { printf '12345678\n' | sudo -S -p '' "$@"; }

echo '== device package count =='
apk list -I 2>/dev/null | wc -l

echo '== device: recommends + shims =='
for p in hkdm hkdm-systemd ttyescape plasma-mobile-sounds vvmd vvmd-systemd \
	vvmplayer gst-libav gst-plugins-ugly; do
	apk info -e "$p" >/dev/null 2>&1 &&
		printf '  ok      %s\n' "$p" || printf '  MISSING %s\n' "$p"
done

echo '== device: systemd health =='
echo "failed=$(systemctl --failed --no-legend | wc -l)"
for u in hkdm vvmd; do
	printf '  %-8s %s\n' "$u" "$(SUDO systemctl is-enabled $u 2>&1)-$(SUDO systemctl is-active $u 2>&1)"
done

echo '== device: ownership of everything this round added =='
for f in /etc/xdg/powerdevilrc /usr/bin/togglevt.sh /usr/sbin/hkdm \
	/usr/lib/systemd/system/hkdm.service \
	/usr/lib/systemd/user/vvmd.service; do
	printf '  %-44s ' "$f"
	apk info -W "$f" 2>&1 | sed 's/^.* is owned by /owned by /'
done

echo '== device: upgrade must stay clean =='
SUDO apk --no-network upgrade --simulate 2>&1 | tail -2
