#!/bin/sh
# The device's systemd repo needs a few -systemd subpackages that are not
# cached locally.  Fetch them with a long timeout and verify signatures.
set -u
BASE=https://mirrors.postmarketos.org/postmarketos/v26.06/aarch64
OUT=/root/extra2
mkdir -p "$OUT"
APK=/root/apkstatic/sbin/apk.static

for pk in hkdm-systemd-0.3.2-r0 vvmd-systemd-1.1-r31 \
	ttyescape-systemd-1.0.1-r5 plasma-mobile-sounds-systemd-0.1-r2; do
	f="$OUT/$pk.apk"
	curl -sSL --max-time 90 -o "$f" "$BASE/$pk.apk" ||
		{ echo "DOWNLOAD FAILED $pk"; continue; }
	printf '%-40s %s bytes  ' "$pk" "$(stat -c %s "$f")"
	"$APK" --keys-dir /root/akeys verify "$f" >/dev/null 2>&1 &&
		echo ok || echo 'UNTRUSTED/absent'
done
