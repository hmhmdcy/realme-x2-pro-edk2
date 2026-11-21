#!/bin/sh
# Find and remove the *private* modifications that make a full-system
# `apk upgrade` unsolvable on the samurai image, then prove the result.
#
# Nothing is written unless --apply is passed, and --apply is refused in
# offline mode.  Offline mode exists so the image's exported database can be
# audited on the host without mounting it or touching the handset.
#
#   device:  sh clean-apk-upgrade.sh [--apply]
#   offline: sh clean-apk-upgrade.sh --db <installed> --world <world>
#
# Exit status is 0 only when every check passed and, on device, a dry-run
# upgrade returned 0.
set -eu

APPLY=0
OFFLINE=0
DB=/lib/apk/db/installed
WORLD=/etc/apk/world
REPO_DIR=

usage()
{
	sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'
}

while [ $# -gt 0 ]; do
	case "$1" in
	--apply) APPLY=1 ;;
	--db) DB=$2; shift; OFFLINE=1 ;;
	--world) WORLD=$2; shift; OFFLINE=1 ;;
	--repo-dir) REPO_DIR=$2; shift ;;
	-h|--help) usage; exit 0 ;;
	*) echo "unknown argument: $1" >&2; exit 2 ;;
	esac
	shift
done

[ "$OFFLINE" -eq 1 ] && APPLY=0

fail=0
ok() { echo "ok: $*"; }
bad() { echo "FAIL: $*" >&2; fail=$((fail + 1)); }
note() { echo "note: $*"; }

echo '=== 1. inputs ==='
[ -f "$DB" ] || { echo "missing database: $DB" >&2; exit 2; }
[ -f "$WORLD" ] || { echo "missing world: $WORLD" >&2; exit 2; }
pkgs=$(grep -c '^P:' "$DB" || true)
echo "  database: $DB"
echo "  world:    $WORLD"
echo "  packages: ${pkgs:-0}"
[ "${pkgs:-0}" -gt 0 ] || bad 'installed database is empty'

# One record per package: name, version, origin, broken-flag.
records=$(awk '
/^P:/ { p = substr($0, 3); v = ""; o = ""; f = "" }
/^V:/ { if (p != "") v = substr($0, 3) }
/^o:/ { if (p != "") o = substr($0, 3) }
/^f:/ { if (p != "") f = substr($0, 3) }
/^$/  { if (p != "") { print p "\t" v "\t" o "\t" f; p = "" } }
END   { if (p != "") print p "\t" v "\t" o "\t" f }
' "$DB")

echo
echo '=== 2. private (non-upstream) packages ==='
# Board packages have no upstream equivalent: they must stay, but they must
# be served by the local signed repository or `apk upgrade` reports them as
# "no longer available".
echo "$records" | awk -F'\t' '
/^(samurai-|device-realme-samurai|usb-signaller|unudhcpd)/ ||
$3 ~ /^samurai-/ || $3 == "device-realme-samurai" {
	printf "  board     %-34s %-18s %s\n", $1, $2, $3
}
' || true

echo
echo '=== 3. locally rebuilt upstream packages ==='
# postmarketOS marks a locally rebuilt package by prefixing the upstream
# version with 9999x, so it always sorts above the official one.  That keeps
# the private build selected forever: apk never considers the upstream
# version an upgrade.  These are what "removing private changes" targets.
echo "$records" | awk -F'\t' '
$2 ~ /^9999[0-9]/ {
	printf "  rebuilt   %-34s %-18s %s\n", $1, $2, $3
}
' || true

echo
echo '=== 4. packages with no upstream counterpart ==='
# A package whose origin is not a real upstream project cannot be upgraded,
# and its file list will collide with the upstream package that eventually
# ships the same paths.  This is the most common hard failure in an upgrade.
echo "$records" | awk -F'\t' '
$3 ~ /dummy/ || $3 == "" {
	printf "  orphan    %-34s %-18s %s\n", $1, $2, ($3 == "" ? "<no origin>" : $3)
}
' || true

echo
echo '=== 5. world pins (these make the solver fail) ==='
checksum=$(grep -c '<Q' "$WORLD" || true)
exact=$(grep -c '=[^<>~]' "$WORLD" || true)
fuzzy=$(grep -c '~' "$WORLD" || true)
echo "  checksum pins <Q..= : ${checksum:-0}"
echo "  exact pins    =      : ${exact:-0}"
echo "  fuzzy pins    ~      : ${fuzzy:-0}"
grep '<Q' "$WORLD" | sed 's/^/    /' || true

if [ "${checksum:-0}" -eq 0 ]; then
	ok 'world carries no APK checksum pins'
else
	if [ "$APPLY" -eq 1 ]; then
		# <Q1...= is a per-file checksum pin produced by a local build; it
		# freezes the package forever.  Strip it, keep the package name.
		cp "$WORLD" "$WORLD.bak-clean-apk"
		sed -i 's/<Q[0-9A-Za-z+/=]*=/ /g' "$WORLD"
		ok "removed $checksum checksum pin(s); backup at $WORLD.bak-clean-apk"
	else
		bad "world has $checksum checksum pin(s); re-run with --apply to strip"
	fi
fi

echo
echo '=== 6. broken script flags ==='
broken=$(echo "$records" | awk -F'\t' '$4 != "" { print "    " $1 " " $2 " (f:" $4 ")" }')
if [ -z "$broken" ]; then
	ok 'no package carries a broken-script flag'
else
	echo "$broken"
	note 'a flagged package adds "1 error" to every later transaction; repair with `apk fix <name>`'
	bad 'broken-script flags present'
fi

echo
echo '=== 7. board repository coverage ==='
if [ -z "$REPO_DIR" ] && [ "$OFFLINE" -eq 0 ]; then
	REPO_DIR=/usr/share/samurai/packages/aarch64
fi
if [ -z "$REPO_DIR" ]; then
	note 'no --repo-dir given; skipping repository coverage check'
elif [ -d "$REPO_DIR" ]; then
	echo "  repository: $REPO_DIR"
	# Coverage is by package *name*, not by installed version: an upgrade
	# only needs some version of that name to exist in the index.  Requiring
	# the exact installed version would flag every outdated board package.
	missing=$(echo "$records" | awk -F'\t' '
	/^(samurai-|device-realme-samurai|usb-signaller|unudhcpd)/ { print $1 }
	' | while read -r name; do
		ls "$REPO_DIR/$name"-*.apk >/dev/null 2>&1 || echo "$name"
	done)
	if [ -z "$missing" ]; then
		ok 'every installed board package is present in the repository'
	else
		echo "$missing" | sed 's/^/    no package with this name: /'
		bad 'the repository does not cover every installed board package'
	fi
else
	bad "board repository not found: $REPO_DIR"
fi

if [ "$OFFLINE" -eq 0 ]; then
	echo
	echo '=== 8. trust chain ==='
	key=pmos@local-6aeaf066.rsa.pub
	if [ -f "/etc/apk/keys/$key" ]; then
		ok "board signing key installed: $key"
	else
		bad "board signing key missing: /etc/apk/keys/$key"
	fi
	if [ -n "$REPO_DIR" ] && [ -f "$REPO_DIR/APKINDEX.tar.gz" ]; then
		ok "board index present: $REPO_DIR/APKINDEX.tar.gz"
	else
		bad "board index missing in $REPO_DIR"
	fi

	echo
	echo '=== 9. prove it ==='
	if [ "$APPLY" -eq 1 ]; then
		printf 'refreshing indexes\n'
		sudo apk update || bad 'apk update failed'
	fi
	sudo apk upgrade --simulate || bad 'apk upgrade --simulate returned non-zero'
fi

echo
if [ "$fail" -ne 0 ]; then
	echo "RESULT: $fail problem(s)" >&2
	exit 1
fi
echo 'RESULT: clean-apk-upgrade check passed'
