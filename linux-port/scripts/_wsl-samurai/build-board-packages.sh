#!/bin/bash
# Rebuild board packages straight from their APKBUILD so the shipped
# repository can never drift from the recipes.
#
# Why this exists: the delivery image carried samurai-platform 6-r22 while
# the recipe was already at 6-r25, and samurai-ssc / samurai-systemd lagged
# one revision each.  `apk upgrade` therefore had nothing newer to offer and
# the source -> artifact link was broken.
#
# Each package's file list is derived from the `install -D<m> <src> <dst>`
# statements in its package() function.  Upgrading one of these recipes
# without re-running this script now fails the repack gate instead of
# silently shipping stale files.
#
# Usage: build-board-packages.sh [--dry-run] pkg [pkg ...]
set -eu

REPO=/mnt/e/RealmeX2Pro\ edk2
PKGS=$REPO/linux-port/packages
APK=/root/apkstatic/sbin/apk.static
KEYS=/root/installed_keys
SIGN_KEY=/mnt/e/edk2-samurai-out/standard-arm64-v731/wifi-fast-ready-20261108/signing-key-private.rsa
OUT=${OUT:-/root/board-out}
DRY=0

if [ "${1:-}" = "--dry-run" ]; then
	DRY=1
	shift
fi
[ $# -gt 0 ] || { echo 'usage: build-board-packages.sh [--dry-run] pkg...' >&2; exit 2; }

mkdir -p "$OUT"

for name in "$@"; do
	dir=$PKGS/$name
	b=$dir/APKBUILD
	[ -f "$b" ] || { echo "missing recipe: $name" >&2; exit 1; }

	ver=$(sed -n 's/^pkgver=//p' "$b" | head -1)
	rel=$(sed -n 's/^pkgrel=//p' "$b" | head -1)
	ver=${ver//\$\{pkgname\}/$name}
	version=$ver-r$rel
	arch=$(sed -n 's/^arch=//p' "$b" | head -1 | tr -d '"')
# abuild's `arch=noarch` means "no arch-specific build requirement"; the
# resulting package still belongs to the device architecture and must be
# recorded as such.  A real noarch APK in an aarch64/ repository cannot be
# resolved: apk looks for it under the noarch path and reports
# "package mentioned in index not found".
	case "$arch" in
	noarch|all|"") arch=aarch64 ;;
	esac
	desc=$(sed -n 's/^pkgdesc=//p' "$b" | head -1 | tr -d '"')
	license=$(sed -n 's/^license=//p' "$b" | head -1 | tr -d '"')

	# depends may span several lines.  Join them, drop comments, then
	# normalise whitespace into the single string apk mkpkg expects.
	depends=$(python3 - "$b" <<'PY'
import re, sys

lines = open(sys.argv[1], encoding='utf-8').read().replace('\r', '').splitlines()
value, inside = '', False
for line in lines:
    if not inside:
        m = re.match(r'^depends="?([^"]*)"?$', line)
        if m:
            value, inside = m.group(1), line.count('"') % 2 == 1
            continue
    else:
        stripped = line.strip().rstrip('"')
        if stripped.startswith('#'):
            continue
        value += ' ' + stripped
        if line.rstrip().endswith('"'):
            inside = False
print(' '.join(value.split()))
PY
)
	[ -n "$depends" ] || { echo "  recipe declares no runtime depends" >&2; exit 1; }
	echo "  depends: $depends"

	echo "=== $name $version ($arch) ==="

	# Pull "src dst" pairs out of package().  A trailing backslash joins the
	# next line first, so multi-line install lines are handled.
	pairs=$(python3 - "$b" <<'PY'
import re, sys

text = open(sys.argv[1], encoding='utf-8').read().replace('\r', '')
# Only the package() body; stop at the next top-level function (pulse() etc).
body = ''
inside = False
for line in text.splitlines():
    if re.match(r'^package\s*\(\s*\)', line):
        inside = True
        continue
    if inside and re.match(r'^[A-Za-z_][\w-]*\s*\(\s*\)', line):
        break
    if inside:
        body += line.rstrip('\\') + ' '

# install -Dm<mode> "$srcdir"/<src> "$pkgdir"/<dst>
for m in re.finditer(
        r'install\s+-Dm(\d+)\s+"\$srcdir"/("[^"]*"|\S+)\s+"\$pkgdir"/("[^"]*"|\S+)',
        body):
    mode, src, dst = m.group(1), m.group(2), m.group(3).rstrip('"')
    src = src.strip('"')
    dst = dst.strip('"')
    print(f'{mode}\t{src}\t{dst}')
PY
)

	if [ -z "$pairs" ]; then
		echo "  no install lines found in package()" >&2
		exit 1
	fi

	stage=$(mktemp -d "/root/board-stage-$name.XXXXXX")
	trap 'rm -rf "$stage"' EXIT
	expected=0
	while IFS=$'\t' read -r mode src dst; do
		[ -n "$src" ] || continue
		from=$dir/$src
		[ -f "$from" ] || { echo "  missing source file: $src" >&2; exit 1; }
		install -Dm$mode "$from" "$stage/$dst"
		expected=$((expected + 1))
	done <<EOF
$pairs
EOF

	# Directories that the package wants to exist but carries no file in.
	rules="$dir/$name.rules"
	if [ -f "$rules" ]; then
		# Format: "dir <mode> <path>"
		while read -r kind dmode dpath; do
			[ "$kind" = dir ] || continue
			install -d -m "$dmode" "$stage/$dpath"
		done < "$rules"
	fi

	files=$(find "$stage" -type f | wc -l)
	echo "  files staged: $files (install lines: $expected)"
	if [ "$files" -ne "$expected" ]; then
		echo "  staged count does not match the install lines" >&2
		exit 1
	fi
	find "$stage" -type f | sed "s|$stage/||" | sort | sed 's/^/    /'

	if [ "$DRY" -eq 1 ]; then
		echo "  dry-run: not packing"
		continue
	fi

	find "$stage" -exec touch -d @1793836800 {} +
	artifact=$OUT/$name-$version.apk
	rm -f "$artifact"
	# `install=` names the lifecycle scripts (post-install, pre-deinstall,
	# ...) that abuild would embed.  mkpkg takes them from the staged tree
	# via --script, so they stay inside the APK and keep running on upgrade.
	script_args=()
	hook_line=$(sed -n 's/^install="\{0,1\}\([^"]*\)"\{0,1\}$/\1/p' "$b" | head -1)
	hook_line=${hook_line//\$\{pkgname\}/$name}
	hook_line=${hook_line//\$pkgname/$name}
	for hook in $hook_line; do
		[ -f "$dir/$hook" ] || { echo "  missing lifecycle script: $hook" >&2; exit 1; }
		case "$hook" in
		*.post-install) script_args+=(--script "post-install:$dir/$hook") ;;
		*.pre-deinstall) script_args+=(--script "pre-deinstall:$dir/$hook") ;;
		*.post-upgrade) script_args+=(--script "post-upgrade:$dir/$hook") ;;
		*.pre-upgrade) script_args+=(--script "pre-upgrade:$dir/$hook") ;;
		*) echo "  unknown lifecycle script name: $hook" >&2; exit 1 ;;
		esac
	done

	"$APK" mkpkg --compat 3.0.0 --sign-key "$SIGN_KEY" \
		--output "$artifact" --files "$stage" \
		--info "name:$name" --info "version:$version" --info "arch:$arch" \
		--info "description:$desc" --info "license:$license" \
		--info "origin:$name" \
		--info "depends:$depends" \
		"${script_args[@]}" \
		--info url:https://github.com/hmhmdcy/realme-x2-pro-pmaports \
		--info build-time:1793836800
	"$APK" --keys-dir "$KEYS" verify "$artifact"
	sha256sum "$artifact"
	stat -c '%s bytes' "$artifact"

	# Subpackages install their own files under $subpkgdir and carry their
	# own depends.  Build the ones this recipe declares so a version bump of
	# the main package cannot leave a stale subpackage behind.
	sublist=$(sed -n 's/^subpackages="\{0,1\}\([^"]*\)"\{0,1\}$/\1/p' "$b" | head -1)
	for sub in $sublist; do
		case "$sub" in
		\$pkgname-*) subname=$name-${sub#\$pkgname-} ;;
		*) subname=$sub ;;
		esac
		# abuild names the subpackage function after the part following the
		# main package name: samurai-platform-pulse -> pulse().
		case "$subname" in
		$name-*) subfn=${subname#$name-} ;;
		*) subfn=$subname ;;
		esac
		subdir=$dir
		[ -d "$subdir" ] || { echo "  missing subpackage dir for $subname" >&2; exit 1; }

		python3 - "$b" "$subfn" > "$stage/.subpairs" <<'PY'
import re, sys

text = open(sys.argv[1], encoding='utf-8').read().replace('\r', '')
sub = sys.argv[2]
body, inside = '', False
for line in text.splitlines():
    if re.match(r'^' + re.escape(sub) + r'\s*\(\s*\)', line):
        inside = True
        continue
    if inside and re.match(r'^[A-Za-z_][\w-]*\s*\(\s*\)', line):
        break
    if inside:
        body += line.rstrip('\\') + ' '
for m in re.finditer(
        r'install\s+-Dm(\d+)\s+"\$srcdir"/("[^"]*"|\S+)\s+"\$subpkgdir"/("[^"]*"|\S+)',
        body):
    print(f'{m.group(1)}\t{m.group(2).strip(chr(34))}\t{m.group(3).strip(chr(34))}')
PY
		substage=$(mktemp -d "/root/board-stage-$subname.XXXXXX")
		subcount=0
		while IFS=$'\t' read -r mode src dst; do
			[ -n "$src" ] || continue
			from=$subdir/$src
			[ -f "$from" ] || { echo "  missing subpackage source: $src" >&2; exit 1; }
			install -Dm$mode "$from" "$substage/$dst"
			subcount=$((subcount + 1))
		done < "$stage/.subpairs"
		rm -f "$stage/.subpairs"
		if [ "$subcount" -eq 0 ]; then
			rm -rf "$substage"
			echo "  subpackage $subname: no files, skipped"
			continue
		fi
		subdepends=()
		for tok in $(sed -n "/^$subfn[ ()]*()/,/^}/p" "$b" | sed -n 's/^[[:space:]]*depends="\{0,1\}\([^"]*\)"\{0,1\}$/\1/p'); do
			subdepends+=("$tok")
		done
		find "$substage" -exec touch -d @1793836800 {} +
		subartifact=$OUT/$subname-$version.apk
		rm -f "$subartifact"
		"$APK" mkpkg --compat 3.0.0 --sign-key "$SIGN_KEY" \
			--output "$subartifact" --files "$substage" \
			--info "name:$subname" --info "version:$version" --info "arch:$arch" \
			--info "description:$(sed -n "/^$subfn[ ()]*()/,/^}/p" "$b" |
				sed -n 's/^[[:space:]]*pkgdesc="\{0,1\}\([^"]*\)"\{0,1\}$/\1/p' | head -1)" \
			--info "license:$license" --info "origin:$name" \
			--info "depends:${subdepends[*]}" \
			--info url:https://github.com/hmhmdcy/realme-x2-pro-pmaports \
			--info build-time:1793836800
		"$APK" --keys-dir "$KEYS" verify "$subartifact"
		sha256sum "$subartifact"
		echo "  subpackage files: $subcount"
		rm -rf "$substage"
	done
done
