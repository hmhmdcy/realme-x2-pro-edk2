#!/bin/sh
# Acceptance for the official recommend install.
set -u
SUDO() { printf '12345678\n' | sudo -S -p '' "$@"; }
fail=0
bad() { echo "FAIL: $*"; fail=1; }
ok() { echo "ok: $*"; }

echo '== official _pmb_recommends present? =='
for p in hkdm ttyescape plasma-mobile-sounds vvmd vvmplayer gst-libav \
	gst-plugins-ugly; do
	if apk info -e "$p" >/dev/null 2>&1; then
		ok "$p installed"
	else
		bad "$p missing"
	fi
done

echo '== files owned by the right packages =='
for pair in /usr/bin/togglevt.sh:ttyescape \
	/usr/sbin/hkdm:hkdm \
	/usr/share/sounds/plasma-mobile/index.theme:plasma-mobile-sounds; do
	f=${pair%:*}; p=${pair#*:}
	owner=$(apk info -W "$f" 2>/dev/null)
	case "$owner" in
	*"$p"*) ok "$f -> $p" ;;
	*) bad "$f owner: ${owner:-none} (want $p)" ;;
	esac
done

echo '== system still healthy =='
n=$(systemctl --failed --no-legend 2>/dev/null | wc -l)
[ "$n" -eq 0 ] && ok 'systemctl --failed = 0' || bad "$n failed units"

echo '== upgrade must remain solvable =='
SUDO apk --no-network upgrade --simulate 2>&1 | tail -2

[ "$fail" -eq 0 ] && echo 'RESULT: recommend install passed' ||
	{ echo 'RESULT: recommend install failed'; exit 1; }
