#!/bin/sh
# The v26.06 index lists hkdm-systemd / vvmd-systemd, but the main mirror
# answers 404.  Check whether another official mirror has the file before
# concluding it is an upstream publishing gap.
set -u
APK=/root/apkstatic/sbin/apk.static
for host in \
	https://mirror.postmarketos.org/postmarketos \
	https://mirrors.postmarketos.org/postmarketos \
	https://osmirror.postmarketos.org/postmarketos \
	https://mirror.postmarketos.org/postmarketos/extra-repos/systemd; do
	for pkg in hkdm-systemd-0.3.2-r0 vvmd-systemd-1.1-r31; do
		url="$host/v26.06/aarch64/$pkg.apk"
		code=$(curl -sSIL --max-time 25 "$url" 2>/dev/null |
			grep -F 'HTTP/' | tail -1 | tr -d '\r')
		printf '%-58s %s\n' "$(echo "$url" | sed 's|https://||')" "${code:-no-answer}"
	done
done
