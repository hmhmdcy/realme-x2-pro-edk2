#!/bin/sh
# Which key signed each official package we intend to install?  A package
# whose signer is absent from /etc/apk/keys cannot be installed or upgraded.
set -u
dir=/tmp/sig
rm -rf "$dir"
mkdir -p "$dir"
for pk in hkdm-0.3.2-r0 vvmd-1.1-r31 vvmplayer-2.6-r1 \
	plasma-mobile-sounds-0.1-r2 ttyescape-1.0.1-r5; do
	for base in \
		https://mirror.postmarketos.org/postmarketos/v26.06/aarch64 \
		https://mirror.postmarketos.org/postmarketos/extra-repos/systemd/v26.06/aarch64; do
		curl -sSL --max-time 45 "$base/$pk.apk" -o "$dir/$pk.apk" 2>/dev/null
		[ -s "$dir/$pk.apk" ] && { echo "$pk <- $base"; break; }
	done
done
for f in "$dir"/*.apk; do
	[ -s "$f" ] || continue
	printf '%-34s ' "$(basename "$f")"
	sig=$(tar tzf "$f" 2>/dev/null | head -1)
	echo "$sig"
case "$sig" in
.SIGN.RSA.*)
	key=${sig#.SIGN.RSA.}
	if [ -f "/etc/apk/keys/$key" ]; then
		echo '    trusted: yes'
	else
		echo '    trusted: NO'
	fi
	;;
esac
done
