#!/bin/sh
# The two -systemd shims are listed in the v26.06 index but 404 on the main
# mirror; the 301 redirect target still serves them.  Fetch them on the
# device so the installed set matches the rebuilt image exactly.
set -eu
SUDO() { printf '12345678\n' | sudo -S -p '' "$@"; }
SUDO true
SUM=/tmp/shims
mkdir -p "$SUM"

for pk in hkdm-systemd-0.3.2-r0 vvmd-systemd-1.1-r31; do
	url="https://mirror.nura.eco:443/postmarketos/v26.06/aarch64/$pk.apk"
	curl -sSL --max-time 60 -o "$SUM/$pk.apk" "$url"
	sz=$(stat -c %s "$SUM/$pk.apk" 2>/dev/null || echo 0)
	printf '%-24s %s bytes  ' "$pk" "$sz"
	apk verify "$SUM/$pk.apk" >/dev/null 2>&1 && echo ok || echo UNTRUSTED
done

for f in "$SUM"/*.apk; do
	SUDO apk --no-network --keys-dir /etc/apk/keys add "$f" 2>&1 | tail -1
done
echo '== total packages =='
apk list -I 2>/dev/null | wc -l
