#!/bin/sh
# Pull the device's installed regulatory.db (from the wireless-regdb
# package) instead of trusting a third-party download.  This is the exact
# pair the running rootfs already ships.
set -eu
OUT=/root/regdb-device
mkdir -p "$OUT"
for f in regulatory.db regulatory.db.p7s; do
	scp -q -i /root/k72key -o UserKnownHostsFile=/dev/null \
		-o StrictHostKeyChecking=no \
		"user@172.16.42.1:/lib/firmware/$f" "$OUT/$f" 2>/dev/null ||
		sudo -n cp "/lib/firmware/$f" "$OUT/$f" 2>/dev/null ||
		true
done
ls -l "$OUT"
sha256sum "$OUT"/* 2>/dev/null
