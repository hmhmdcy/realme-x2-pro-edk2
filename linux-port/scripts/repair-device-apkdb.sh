#!/bin/sh
# Remove the hand-written samurai-ncm-fallback record from the device's apk
# database.
#
# apk-tools 3 rejects the whole installed database when it meets the fields
# that install-ncm-fallback.sh appended, so every `apk` command fails with
# "v2 database format error".  The files that record described are already
# gone (the fallback service was retired), so the record is pure residue.
#
# Run on the device as root.  Prints a before/after summary and validates
# the result with the same field-state rules apk uses.

set -eu

db=/lib/apk/db/installed
[ -f "$db" ] || { echo "$db missing" >&2; exit 1; }

before=$(grep -c '^P:' "$db" || true)
tmp=/tmp/installed.repaired
mkdir -p /tmp

awk '
	BEGIN { RS = ""; ORS = "\n\n" }
	{ if ($0 ~ /(^|\n)P:samurai-ncm-fallback\n/) next; print }
' "$db" > "$tmp"

after=$(grep -c '^P:' "$tmp" || true)
echo "records: $before -> $after"

if [ "$before" -eq "$after" ]; then
	echo "no fallback record present; database left untouched"
	rm -f "$tmp"
	exit 0
fi

# Validate the rewritten database before replacing the live one.
awk '
	BEGIN { pkg=""; diri=0; file=0; bad=0 }
	/^P:/ { pkg=substr($0,3); diri=0; file=0; next }
	/^F:/ { diri=1; file=0; next }
	/^R:/ { if (!diri) { print "line " NR ": R without F"; bad=1 } file=1; next }
	/^Z:/ { if (!file) { print "line " NR ": Z without R"; bad=1 } next }
	/^a:/ { if (!diri && !file) { print "line " NR ": acl without F/R"; bad=1 } next }
	END { exit bad }
' "$tmp" || { echo "rewritten database failed validation; aborting" >&2; exit 1; }

# Preserve ownership/mode and swap in atomically.
chown root:root "$tmp"
chmod 644 "$tmp"
cp -p "$db" "/tmp/installed.backup.$(date +%s)"
mv "$tmp" "$db"

echo "database replaced"
apk --version
apk info samurai-platform >/dev/null 2>&1 &&
	echo "OK: apk can read the database again" ||
	echo "FAIL: apk still cannot read the database" >&2
